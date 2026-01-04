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
app.secret_key = "chiave_segreta_valerio"

# Variabili Ambiente
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
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            c.update({
                "destinazione": request.form.get("destinazione"),
                "km_a": request.form.get("km_arrivo"),
                "data_a": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

            # 1. SCRITTURA EXCEL (Immediata)
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], c['data_a'], c['autista'], c['targa'], c['partenza'], c['destinazione'], c['km_p'], c['km_a']]]
                service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H", valueInputOption="RAW", body={'values': values}).execute()
                print("✅ Excel OK")
            except Exception as e:
                print(f"❌ Errore Excel: {e}")

            # 2. GENERAZIONE PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            doc.build([Paragraph(f"Rapporto {c['autista']}", styles['Heading1']), Spacer(1,12), Paragraph(f"Targa: {c['targa']}", styles['Normal'])])
            pdf_content = buffer.getvalue()

            # 3. INVIO EMAIL (Bloccante - Obbliga Render ad aspettare l'invio)
            print(f"--- [INVIO IN CORSO...] ---")
            try:
                msg = MIMEMultipart()
                msg['From'] = GMAIL_USER
                msg['To'] = GMAIL_USER
                msg['Subject'] = f"Rapporto {c['autista']}"
                msg.attach(MIMEText("In allegato il PDF.", 'plain'))
                
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(pdf_content)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename=Rapporto.pdf')
                msg.attach(part)

                with smtplib.SMTP("mail.gmx.com", 587, timeout=20) as server:
                    server.starttls()
                    server.login(GMAIL_USER, GMAIL_PASS)
                    server.send_message(msg)
                print("✅ ✅ ✅ EMAIL INVIATA!")
            except Exception as e:
                print(f"❌ ERRORE EMAIL: {e}")
                
        return redirect("/")
    
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
