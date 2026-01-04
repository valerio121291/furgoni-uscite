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

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

def invia_email_veloce(dati, pdf_content):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER 
        msg['Subject'] = f"Rapporto {dati['autista']}"
        msg.attach(MIMEText("Invio automatico rapporto.", 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=Rapporto.pdf")
        msg.attach(part)

        # Connessione Outlook standard
        with smtplib.SMTP("smtp.office365.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        print("✅ EMAIL SPEDITA!")
    except Exception as e:
        print(f"❌ ERRORE: {e}")

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
            except: print("❌ Errore Excel")

            # 2. PDF in memoria
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            doc.build([Paragraph(f"Rapporto {c['autista']}", getSampleStyleSheet()['Heading1'])])
            pdf_content = buffer.getvalue()

            # 3. Invio immediato (senza thread per testare l'errore)
            invia_email_veloce(c, pdf_content)
                
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
