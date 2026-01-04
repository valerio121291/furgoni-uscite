import os, json, io, smtplib
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = "chiave_segreta_valerio_2026"

# Variabili Ambiente (Caricate da Render)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            print(f"--- [START] Corsa iniziata: {session['corsa']['autista']} ---")
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            c.update({
                "destinazione": request.form.get("destinazione"),
                "km_a": request.form.get("km_arrivo"),
                "data_a": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

            # 1. AGGIORNAMENTO EXCEL
            print("--- [1] Scrittura su Google Sheets... ---")
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], c['data_a'], c['autista'], c['targa'], c['partenza'], c['destinazione'], c['km_p'], c['km_a']]]
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                    valueInputOption="RAW", body={'values': values}
                ).execute()
                print("✅ Excel aggiornato")
            except Exception as e:
                print(f"❌ Errore Excel: {e}")

            # 2. CREAZIONE PDF IN MEMORIA
            print("--- [2] Generazione PDF... ---")
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elementi = [
                Paragraph(f"RIEPILOGO CORSA - {c['autista']}", styles['Heading1']),
                Spacer(1, 12),
                Paragraph(f"Targa: {c['targa']}", styles['Normal']),
                Paragraph(f"Percorso: da {c['partenza']} a {c['destinazione']}", styles['Normal']),
                Paragraph(f"Orari: {c['data_p']} - {c['data_a']}", styles['Normal']),
                Paragraph(f"Chilometri: Inizio {c['km_p']} - Fine {c['km_a']}", styles['Normal'])
            ]
            doc.build(elementi)
            pdf_content = buffer.getvalue()

            # 3. INVIO EMAIL (SINCRONO - BLOCCHIAMO IL REBOOT)
            print(f"--- [3] Invio Email via GMX (Porta 465 SSL)... ---")
            try:
                msg = MIMEMultipart()
                msg['From'] = GMAIL_USER
                msg['To'] = GMAIL_USER
                msg['Subject'] = f"Rapporto Furgone: {c['autista']} ({c['targa']})"
                msg.attach(MIMEText(f"Ciao Valerio, ecco il rapporto per la corsa di {c['autista']}.", 'plain'))

                part = MIMEBase('application', 'octet-stream')
                part.set_payload(pdf_content)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename=Rapporto.pdf')
                msg.attach(part)

                # Utilizziamo SMTP_SSL per una connessione immediata e sicura
                with smtplib.SMTP_SSL("mail.g
