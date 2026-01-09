import os, json, io, requests, re, smtplib
from flask import Flask, render_template, request, session, send_file, redirect, url_for, jsonify
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from upstash_redis import Redis
from email.message import EmailMessage
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pytz 

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "logistica_csa_valerio_2026")

# --- CONFIGURAZIONE ---
# Inserisci la chiave qui o impostala su Vercel come GOOGLE_API_KEY
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyCxfGEZAcmMc00D6CCwsaAwAC0GY6EAaUc")
PPLX_API_KEY = os.getenv("PPLX_API_KEY")
EMAIL_MITTENTE = "pvalerio910@gmail.com"
EMAIL_PASSWORD = "ogteueppdqmtpcvg"
EMAIL_DESTINATARIO = "pvalerio910@gmail.com"
SPREADSHEET_ID = '13vzhKIN6GkFaGhoPkTX0vnUNGZy6wcMT0JWZCpIsx68'

def get_now_it():
    try:
        tz_roma = pytz.timezone('Europe/Rome')
        return datetime.now(tz_roma).strftime("%d/%m/%Y %H:%M")
    except:
        return datetime.now().strftime("%d/%m/%Y %H:%M")

try:
    url = os.getenv("KV_REST_API_URL")
    token = os.getenv("KV_REST_API_TOKEN")
    kv = Redis(url=url, token=token) if url and token else None
except:
    kv = None

STATO_INIZIALE = {
    "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0, "carburante": "Pieno"},
    "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0, "carburante": "Pieno"},
    "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 44627, "autista": "-", "step": 0, "carburante": "Pieno"}
}

def get_google_service():
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_json: return None
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        return build('sheets', 'v4', credentials=creds)
    except: return None

def carica_stato():
    if kv is None: return STATO_INIZIALE
    try:
        stato = kv.get("stato_furgoni")
        return stato if isinstance(stato, dict) else json.loads(stato)
    except: return STATO_INIZIALE

def salva_stato(stato):
    try:
        if kv: kv.set("stato_furgoni", json.dumps(stato))
    except: pass

@app.route("/", methods=["GET", "POST"])
def index():
    furgoni = carica_stato()
    targa_attiva = session.get("targa_in_uso")
    corsa_attiva = furgoni.get(targa_attiva) if targa_attiva else None

    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")

        if azione == "start" and targa in furgoni:
            autisti_lista = request.form.getlist("autista")
            equipaggio = ", ".join(autisti_lista) if autisti_lista else "Non specificato"
            km_p = int(request.form.get("km_partenza", 0))
            if targa == "GG862HC" and km_p < 44627:
                return "Errore: KM minimi 44.627", 400
            furgoni[targa].update({"stato": "In Viaggio", "km_p": km_p, "autista": equipaggio, "step": 1, "data_p": get_now_it()})
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        elif azione == "arrivo_dest" and targa:
            furgoni[targa].update({"dest_intermedia": request.form.get("destinazione"), "km_d": request.form.get("km_destinazione"), "step": 2, "data_d": get_now_it()})
            salva_stato(furgoni)
            return redirect(url_for('index'))

        elif azione == "stop" and targa:
            c = furgoni.get(targa)
            km_r = request.form.get("km_rientro")
            gasolio = request.form.get("carburante")
            try:
                service = get_google_service()
                if service:
                    riga = [c['data_p'], c.get('data_d','-'), get_now_it(), c['autista'], targa, "Sede", c.get('dest_intermedia','-'), c['km_p'], c.get('km_d','-'), km_r, gasolio]
                    service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:K", valueInputOption="USER_ENTERED", body={"values": [riga]}).execute()
            except: pass
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": km_r, "autista": "-", "step": 0, "carburante": gasolio}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

        elif azione == "annulla":
            if targa: furgoni[targa].update({"stato": "Libero", "step": 0})
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        testo = request.json.get("testo", "").lower()
        # Chiamata a Google Gemini 1.5 Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{"text": f"Sei l'assistente vocale della logistica CSA. Rispondi in modo brevissimo (massimo 15 parole) alla domanda: {testo}"}]
            }]
        }
        r = requests.post(url, headers=headers, json=payload, timeout=8)
        res = r.json()
        risposta_ia = res['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"risposta": risposta_ia})
    except Exception as e:
        return jsonify({"risposta": "Cervello CSA momentaneamente offline."}), 500

if __name__ == "__main__":
    app.run()
