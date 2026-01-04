
import os, json, io, smtplib, threading
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "furgoni_2026_valerio")

# Caricamento variabili da Render
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

def invia_email_gmx(dati, pdf_content):
    print(f"--- [GMX] Tentativo invio a {GMAIL_USER} ---")
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER 
        msg['Subject'] = f"Rapporto Corsa: {dati['autista']}"
        msg.attach(MIMEText("In allegato il rapporto PDF della corsa.", 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=Rapporto.pdf")
        msg.attach(part)

        # Server GMX porta 587
        with smtplib.SMTP("mail.gmx.com", 587, timeout=30) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        print("✅ ✅ ✅ EMAIL GMX INVIATA CON SUCCESSO!")
    except Exception as e:
        print(f"❌ [GMX] ERRORE: {e}")

def genera_pdf_buffer(dati):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elementi = [
        Paragraph(f"RIEPILOGO CORSA - {dati['autista']}", styles['Heading1']),
        Spacer(1, 12),
        Paragraph(f"Targa: {dati['targa']}", styles['Normal']),
        Paragraph(f"Partenza: {dati['data_p']} ({dati['km_p']} KM)", styles['Normal']),
        Paragraph(f"Arrivo: {dati['data_a']} ({dati['km_a']} KM)", styles['Normal'])
    ]
    doc.build(elementi)
    return buffer.getvalue()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"), "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"), "km_p": request.form.get("km_partenza"),
                "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            c.update({
                "destinazione": request.form.get("destinazione"), "km_a": request.form.get("km_arrivo"),
                "data_a": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            
            # 1. Excel
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], c['data_a'], c['autista'], c['targa'], c['partenza'], c['destinazione'], c['km_p'], c['km_a']]]
                service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H", valueInputOption="RAW", body={'values': values}).execute()
                print("✅ Excel aggiornato")
            except Exception as e:
                print(f"❌ Errore Excel: {e}")

            # 2. PDF ed Email in Background
            pdf_content = genera_pdf_buffer(c)
            threading.Thread(target=invia_email_gmx, args=(c, pdf_content)).start()
                
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
