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
GOOGLE_API_KEY = "vzmxtuvtwruvoohd"
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

# Database Redis (per salvare lo stato su Vercel)
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
        if not stato: return STATO_INIZIALE
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

        # --- INIZIO MISSIONE ---
        if azione == "start" and targa in furgoni:
            autisti_lista = request.form.getlist("autista")
            equipaggio = ", ".join(autisti_lista) if autisti_lista else "Non specificato"
            km_p = int(request.form.get("km_partenza", 0))
            
            if targa == "GG862HC" and km_p < 44627:
                return "Errore: KM minimi 44.627", 400

            furgoni[targa].update({
                "stato": "In Viaggio", "posizione": "TIBURTINA",
                "km_p": km_p, "autista": equipaggio,
                "step": 1, "data_p": get_now_it()
            })
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        # --- ARRIVO DESTINAZIONE ---
        elif azione == "arrivo_dest" and targa:
            furgoni[targa].update({
                "dest_intermedia": request.form.get("destinazione"),
                "km_d": request.form.get("km_destinazione"),
                "step": 2, "data_d": get_now_it()
            })
            salva_stato(furgoni)
            return redirect(url_for('index'))

        # --- FINE MISSIONE (INVIO EMAIL E PDF) ---
        elif azione == "stop" and targa:
            c = furgoni.get(targa)
            km_r = request.form.get("km_rientro")
            gasolio = request.form.get("carburante")
            data_r = get_now_it()
            
            # Google Sheets
            try:
                service = get_google_service()
                if service:
                    riga = [c['data_p'], c.get('data_d','-'), data_r, c['autista'], targa, "TIBURTINA", c.get('dest_intermedia','-'), c['km_p'], c.get('km_d','-'), km_r, f"Gasolio: {gasolio}"]
                    service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:K", valueInputOption="USER_ENTERED", body={"values": [riga]}).execute()
            except: pass

            # PDF
            pdf_path = "/tmp/Report_Viaggio.pdf"
            try:
                p = canvas.Canvas(pdf_path, pagesize=A4)
                p.setFont("Helvetica-Bold", 18)
                p.drawCentredString(300, 800, "LOGISTICA CSA - REPORT MISSIONE")
                p.setFont("Helvetica", 11)
                p.drawCentredString(300, 780, f"Equipaggio: {c['autista']}")
                
                def draw_block(titolo, info, km, data, y_pos, color_bg):
                    p.setFillColor(color_bg); p.rect(50, y_pos-60, 500, 60, fill=1)
                    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 11); p.drawString(60, y_pos-20, titolo)
                    p.setFont("Helvetica", 10); p.drawString(60, y_pos-35, f"LUOGO: {info} | ORA: {data}"); p.drawString(60, y_pos-50, f"KM: {km}")
                    return y_pos - 80
                
                y = 700
                y = draw_block("1. PARTENZA", "TIBURTINA", c['km_p'], c['data_p'], y, colors.lightgrey)
                y = draw_block("2. ARRIVO INTERMEDIO", c.get('dest_intermedia','-'), c.get('km_d','-'), c.get('data_d','-'), y, colors.whitesmoke)
                y = draw_block("3. RIENTRO IN SEDE", "TIBURTINA", km_r, data_r, y, colors.lightgrey)
                p.showPage(); p.save()
            except: pass

            # Email
            try:
                msg = EmailMessage()
                msg['Subject'] = f"Report: {targa} - {c['autista']}"
                msg['From'] = EMAIL_MITTENTE
                msg['To'] = EMAIL_DESTINATARIO
                msg.set_content(f"Missione chiusa.\nMezzo: {targa}\nEquipaggio: {c['autista']}\nKM Rientro: {km_r}")
                with open(pdf_path, 'rb') as f:
                    msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=f"Report_{targa}.pdf")
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(EMAIL_MITTENTE, EMAIL_PASSWORD)
                    smtp.send_message(msg)
            except: pass

            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": km_r, "autista": "-", "step": 0, "carburante": gasolio}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return send_file(pdf_path, as_attachment=True, download_name=f"Report_{targa}.pdf")

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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        payload = {"contents": [{"parts": [{"text": f"Rispondi brevemente come assistente logistico CSA: {testo}"}]}]}
        r = requests.post(url, json=payload, timeout=8)
        risposta_ia = r.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"risposta": risposta_ia})
    except:
        return jsonify({"risposta": "Errore connessione IA."}), 500

if __name__ == "__main__":
    app.run(debug=True)
