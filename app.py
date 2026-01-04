import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Google & IA
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "logistica_csa_2026_final"

# IA Gemini Key
genai.configure(api_key="AIzaSyCxfGEZAcmMc00D6CCwsaAwAC0GY6EAaUc")

DB_FILE = "stato_furgoni.json"

def carica_stato():
    if not os.path.exists(DB_FILE):
        iniziale = {
            "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
            "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
            "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
        }
        salva_stato(iniziale)
        return iniziale
    with open(DB_FILE, "r") as f: return json.load(f)

def salva_stato(stato):
    with open(DB_FILE, "w") as f: json.dump(stato, f)

def analisi_ia_viaggio(p, d, km, targa):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Analizza: viaggio da {p} a {d}, totale {km} km, furgone {targa}. Dimmi se i km sono ok e stima costo gasolio (max 10 parole)."
        return model.generate_content(prompt).text
    except: return "Analisi non disponibile"

@app.route("/", methods=["GET", "POST"])
def index():
    furgoni = carica_stato()
    targa_attiva = session.get("targa_in_uso")
    corsa_attiva = furgoni.get(targa_attiva) if targa_attiva else None

    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")

        if azione == "start":
            furgoni[targa] = {
                "targa": targa, "stato": "In Viaggio", "posizione": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"), "autista": request.form.get("autista"),
                "step": 1, "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        elif azione == "arrivo_dest":
            furgoni[targa].update({
                "dest_intermedia": request.form.get("destinazione"),
                "km_d": request.form.get("km_destinazione"),
                "step": 2, "data_d": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salva_stato(furgoni)
            return redirect(url_for('index'))

        elif azione == "stop":
            c = furgoni.get(targa)
            km_r = request.form.get("km_rientro")
            tot_km = int(km_r) - int(c['km_p'])
            nota_ia = analisi_ia_viaggio(c['posizione'], c.get('dest_intermedia','-'), tot_km, targa)

            try:
                creds_json = os.getenv("GOOGLE_CREDENTIALS")
                spreadsheet_id = os.getenv("SPREADSHEET_ID")
                if creds_json and spreadsheet_id:
                    info = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                    service = build('sheets', 'v4', credentials=creds)
                    nuova_riga = [[c['data_p'], c.get('data_d', '-'), datetime.now().strftime("%d/%m/%Y %H:%M"), c['autista'], targa, c['posizione'], c.get('dest_intermedia', '-'), c['km_p'], c.get('km_d', '-'), km_r, nota_ia]]
                    service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range="Foglio1!A:K", valueInputOption="RAW", body={'values': nuova_riga}).execute()
            except Exception as e: print(f"Errore: {e}")

            buffer = io.BytesIO()
            p_pdf = canvas.Canvas(buffer, pagesize=A4)
            p_pdf.drawString(50, 800, f"LOGISTICA CSA - REPORT {targa}")
            p_pdf.drawString(50, 780, f"Autista: {c['autista']} | KM Totali: {tot_km}")
            p_pdf.drawString(50, 760, f"Analisi IA: {nota_ia}")
            p_pdf.showPage()
            p_pdf.save()
            buffer.seek(0)

            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": km_r, "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return send_file(buffer, as_attachment=True, download_name=f"CSA_{targa}.pdf", mimetype='application/pdf')

        elif azione == "annulla":
            if targa:
                furgoni[targa]["stato"] = "Libero"
                furgoni[targa]["step"] = 0
                salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/chat_ia", methods=["POST"])
def chat_ia():
    dati = request.json
    msg = dati.get("messaggio", "").lower()
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Estrai dati da: '{msg}'. Rispondi SOLO JSON: {{"autista": "nome", "partenza": "città", "km": "numero", "destinazione": "città", "risposta": "conferma breve"}}. Nomi ammessi: Valerio, Daniele, Costantino, Stefano."""
        response = model.generate_content(prompt)
        pulita = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(pulita)
    except: return {"risposta": "Errore connessione."}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
