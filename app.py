import os, json, io, smtplib
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

# CONFIGURAZIONI RENDER
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
GMAIL_USER = os.getenv("GMAIL_USER") # Qui metterai la tua email Outlook
GMAIL_PASS = os.getenv("GMAIL_PASS") # Qui metterai la password snuozokkvcrutrsp

def invia_email_con_pdf(dati, pdf_buffer):
    """Versione ottimizzata per Outlook/Hotmail"""
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER 
        msg['Subject'] = f"Rapporto Corsa: {dati['autista']} - {dati['data_a']}"

        corpo = f"Ciao Valerio,\n\nIn allegato trovi il rapporto della corsa terminata il {dati['data_a']}."
        msg.attach(MIMEText(corpo, 'plain'))

        nome_file = f"Rapporto_{dati['autista']}.pdf"
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {nome_file}")
        msg.attach(part)

        # Configurazione per Outlook (Office 365)
        server = smtplib.SMTP('smtp.office365.com', 587, timeout=30)
        server.starttls() 
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ EMAIL INVIATA CON SUCCESSO VIA OUTLOOK!")
    except Exception as e:
        print(f"❌ ERRORE INVIO OUTLOOK: {e}")

def genera_pdf_buffer(dati):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    try:
        tot_km = int(dati['km_a']) - int(dati['km_p'])
    except:
        tot_km = "N/D"

    elementi = [
        Paragraph(f"RIEPILOGO CORSA - {dati['autista']}", styles['Heading1']),
        Spacer(1, 12),
        Table([
            ["Autista", dati['autista']], ["Targa", dati['targa']],
            ["Da", dati['partenza']], ["A", dati['destinazione']],
            ["Inizio", dati['data_p']], ["Fine", dati['data_a']],
            ["KM Inizio", dati['km_p']], ["KM Fine", dati['km_a']],
            ["KM TOTALI", str(tot_km)]
        ], style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
            ('PADDING', (0,0), (-1,-1), 8)
        ])),
    ]
    doc.build(elementi)
    buffer.seek(0)
    return buffer

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
            
            # 1. Excel (Sempre tramite il robot Google)
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], c['data_a'], c['autista'], c['targa'], c['partenza'], c['destinazione'], c['km_p'], c['km_a']]]
                service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H", valueInputOption="RAW", body={'values': values}).execute()
                print("✅ Excel aggiornato")
            except Exception as e:
                print(f"❌ Errore Excel: {e}")

            # 2. Email tramite Outlook
            pdf_buffer = genera_pdf_buffer(c)
            invia_email_con_pdf(c, pdf_buffer)
                
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
