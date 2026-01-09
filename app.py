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
PPLX_API_KEY = os.getenv("PPLX_API_KEY")
EMAIL_MITTENTE = "pvalerio910@gmail.com"
EMAIL_PASSWORD = "ogteueppdqmtpcvg"
EMAIL_DESTINATARIO = "pvalerio910@gmail.com"
SPREADSHEET_ID = '13vzhKIN6GkFaGhoPkTX0vnUNGZy6wcMT0JWZCpIsx68'
CAPACITA_SERBATOIO = 70 

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

# KM INIZIALI AGGIORNATI (Furgone Grande: 44627)
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

        if azione == "start" and targa in furgoni:
            km_p = int(request.form.get("km_partenza", 0))
            # PROTEZIONE KM: non permette di scalare i KM
            if km_p < int(furgoni[targa]['km']):
                return "Errore: I KM non possono essere inferiori all'ultima registrazione!", 400

            furgoni[targa].update({
                "stato": "In Viaggio", "posizione": "TIBURTINA",
                "km_p": km_p,
                "autista": request.form.get("autista"),
                "step": 1, "data_p": get_now_it()
            })
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        elif azione == "arrivo_dest" and targa:
            furgoni[targa].update({
                "dest_intermedia": request.form.get("destinazione"),
                "km_d": request.form.get("km_destinazione"),
                "step": 2, "data_d": get_now_it()
            })
            salva_stato(furgoni)
            return redirect(url_for('index'))

        elif azione == "stop" and targa:
            c = furgoni.get(targa)
            km_r = request.form.get("km_rientro")
            gasolio = request.form.get("carburante")
            data_r = get_now_it()
            
            # 1. Google Sheets
            try:
                service = get_google_service()
                if service:
                    riga = [c['data_p'], c.get('data_d','-'), data_r, c['autista'], targa, "TIBURTINA", c.get('dest_intermedia','-'), c['km_p'], c.get('km_d','-'), km_r, f"Gasolio: {gasolio}"]
                    service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:K", valueInputOption="USER_ENTERED", body={"values": [riga]}).execute()
            except: pass

            # 2. PDF Report
            pdf_path = "/tmp/Report_Viaggio.pdf"
            try:
                p = canvas.Canvas(pdf_path, pagesize=A4)
                p.setFont("Helvetica-Bold", 18)
                p.drawCentredString(300, 800, "LOGISTICA CSA - REPORT VIAGGIO")
                def draw_block(titolo, info, km, data, y_pos, color_bg):
                    p.setFillColor(color_bg); p.rect(50, y_pos-60, 500, 60, fill=1)
                    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 11); p.drawString(60, y_pos-20, titolo)
                    p.setFont("Helvetica", 10); p.drawString(60, y_pos-35, f"LUOGO: {info} | ORA: {data}"); p.drawString(60, y_pos-50, f"KM: {km}")
                    return y_pos - 80
                y = 720
                y = draw_block("1. PARTENZA", "TIBURTINA", c['km_p'], c['data_p'], y, colors.lightgrey)
                y = draw_block("2. ARRIVO INTERMEDIO", c.get('dest_intermedia','-'), c.get('km_d','-'), c.get('data_d','-'), y, colors.whitesmoke)
                y = draw_block("3. RIENTRO", "TIBURTINA (Sede)", km_r, data_r, y, colors.lightgrey)
                p.showPage(); p.save()
            except: pass

            # 3. Email
            try:
                msg = EmailMessage()
                msg['Subject'] = f"Fine Viaggio: {c['autista']} - {targa}"
                msg['From'] = EMAIL_MITTENTE; msg['To'] = EMAIL_DESTINATARIO
                msg.set_content(f"Missione terminata.\nFurgone: {targa}\nGasolio: {gasolio}")
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
            if targa and targa in furgoni: furgoni[targa].update({"stato": "Libero", "step": 0})
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/rifornimento", methods=["POST"])
def rifornimento():
    try:
        data = request.json
        targa = data.get('targa')
        litri_messi = float(data.get('litri', 0))
        furgoni = carica_stato()
        mappa_litri = {"Vuoto": 5, "Semivuoto": 20, "Metà": 35, "Pieno": 70}
        litri_attuali = mappa_litri.get(furgoni[targa].get('carburante', 'Vuoto'), 5)
        nuovi_litri = litri_attuali + litri_messi
        if nuovi_litri >= CAPACITA_SERBATOIO * 0.85: nuovo = "Pieno"
        elif nuovi_litri >= CAPACITA_SERBATOIO * 0.45: nuovo = "Metà"
        elif nuovi_litri >= CAPACITA_SERBATOIO * 0.20: nuovo = "Semivuoto"
        else: nuovo = "Vuoto"
        furgoni[targa]['carburante'] = nuovo
        salva_stato(furgoni)
        return jsonify({"success": True})
    except: return jsonify({"success": False}), 500

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        testo = request.json.get("testo", "").lower()
        headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}
        # ISTRUZIONI IA POTENZIATE PER AUTISTA E FURGONE
        payload = {
            "model": "llama-3.1-sonar-small-128k-online", 
            "messages": [
                {"role": "system", "content": """Estrai dati logistica in JSON. 
                Mappa i furgoni: 'piccolo'->GA087CH, 'medio'->GX942TS, 'grande'->GG862HC. 
                Mappa gli autisti: Valerio, Daniele, Costantino, Simone, Stefano. 
                Esempio: {"targa": "GG862HC", "autista": "Valerio", "km": 44627}"""}, 
                {"role": "user", "content": testo}
            ], 
            "temperature": 0
        }
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        match = re.search(r'\{.*\}', r.json()['choices'][0]['message']['content'], re.DOTALL)
        return jsonify(json.loads(match.group())) if match else jsonify({"error": "No JSON"}), 500
    except: return jsonify({"error": "IA offline"}), 500

if __name__ == "__main__":
    app.run()
