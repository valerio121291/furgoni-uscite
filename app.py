import os, json, io, requests, re, smtplib
from flask import Flask, render_template, request, session, send_file, redirect, url_for, jsonify
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from upstash_redis import Redis
from email.message import EmailMessage
# Librerie Google
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "logistica_csa_valerio_2026")

# --- CONFIGURAZIONE ---
PPLX_API_KEY = os.getenv("PPLX_API_KEY")
EMAIL_MITTENTE = "pvalerio910@gmail.com"
EMAIL_PASSWORD = "ogteueppdqmtpcvg"
EMAIL_DESTINATARIO = "pvalerio910@gmail.com"

# Inserisci qui l'ID del tuo foglio (si trova nell'URL del foglio Google)
SPREADSHEET_ID = 'IL_TUO_ID_FOGLIO_GOOGLE'

# Connessione Redis
try:
    kv = Redis(url=os.getenv("KV_REST_API_URL"), token=os.getenv("KV_REST_API_TOKEN"))
except:
    kv = None

STATO_INIZIALE = {
    "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
    "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
    "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
}

# --- FUNZIONI GOOGLE SHEETS ---
def get_google_service():
    # Legge il JSON dalla variabile d'ambiente GOOGLE_CREDENTIALS su Vercel
    info = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return build('sheets', 'v4', credentials=creds)

def scrivi_su_sheets(riga):
    try:
        service = get_google_service()
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Foglio1!A:G",
            valueInputOption="USER_ENTERED",
            body={"values": [riga]}
        ).execute()
    except Exception as e:
        print(f"Errore Google Sheets: {e}")

# --- GESTIONE STATO ---
def carica_stato():
    if kv is None: return STATO_INIZIALE
    try:
        stato = kv.get("stato_furgoni")
        return stato if isinstance(stato, dict) else json.loads(stato)
    except: return STATO_INIZIALE

def salva_stato(stato):
    if kv: kv.set("stato_furgoni", json.dumps(stato))

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
                "targa": targa, "stato": "In Viaggio",
                "posizione": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "autista": request.form.get("autista"),
                "step": 1, "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        elif azione == "arrivo_dest":
            if targa in furgoni:
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
            data_r = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # 1. SCRITTURA SU GOOGLE SHEETS
            riga_dati = [c['data_p'], data_r, c['autista'], targa, c['km_p'], c.get('km_d', '-'), km_r]
            scrivi_su_sheets(riga_dati)

            # 2. GENERAZIONE PDF
            pdf_path = "/tmp/Report_Viaggio.pdf"
            p = canvas.Canvas(pdf_path, pagesize=A4)
            p.setFont("Helvetica-Bold", 16)
            p.drawString(100, 800, "LOGISTICA CSA - REPORT VIAGGIO")
            p.setFont("Helvetica", 12)
            p.drawString(100, 770, f"Autista: {c['autista']}")
            p.drawString(100, 750, f"Mezzo: {targa}")
            p.drawString(100, 730, f"KM Partenza: {c['km_p']} | KM Rientro: {km_r}")
            p.showPage()
            p.save()

            # 3. INVIO EMAIL
            try:
                msg = EmailMessage()
                msg['Subject'] = f"Fine Missione: {c['autista']} - {targa}"
                msg['From'] = EMAIL_MITTENTE
                msg['To'] = EMAIL_DESTINATARIO
                msg.set_content(f"Report completato per {targa}.\nChilometri totali registrati.")
                with open(pdf_path, 'rb') as f:
                    msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=f"Report_{targa}.pdf")
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                    smtp.login(EMAIL_MITTENTE, EMAIL_PASSWORD)
                    smtp.send_message(msg)
            except: pass

            # Reset furgone
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": km_r, "autista": "-", "step": 0}
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
        testo = request.json.get("testo", "")
        headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "Estrai targa, autista, km in JSON. Mappe: piccolo->GA087CH, medio->GX942TS, grande->GG862HC."},
                {"role": "user", "content": testo}
            ],
            "temperature": 0
        }
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        match = re.search(r'\{.*\}', r.json()['choices'][0]['message']['content'], re.DOTALL)
        return jsonify(json.loads(match.group())) if match else jsonify({"error": "No JSON"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
