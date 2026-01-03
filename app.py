from flask import Flask, render_template, request, redirect, session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "furgoni-valerio-2026-v8")

# CONFIGURAZIONI
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1Hk-GOKdMts3Qm1qgkt9V58YUoP6Hrshl")
DESTINATARIO_EMAIL = "valerio121291@hotmail.it"
GMAIL_USER = os.getenv("GMAIL_USER") # pvalerio910@gmail.com
GMAIL_PASS = os.getenv("GMAIL_PASS") # cjareqgaidlqwtnd
TEMP_FOLDER = "/tmp/furgoni"

def invia_email_standard(pdf_path, filename):
    """Invia email usando SMTP tradizionale (Porta 587)"""
    if not GMAIL_USER or not GMAIL_PASS:
        print("⚠️ DEBUG: Credenziali Gmail mancanti su Render!")
        return
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = DESTINATARIO_EMAIL
    msg['Subject'] = f"🚚 Rapporto: {filename}"
    msg.attach(MIMEText("In allegato il rapporto PDF.", 'plain'))

    try:
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)

        print(f"DEBUG: Tentativo invio email a {DESTINATARIO_EMAIL}...")
        # Usiamo un timeout molto lungo per Render
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        print("✅ Email inviata con successo!")
    except Exception as e:
        print(f"❌ Errore Email: {e}")

def carica_pdf_su_drive_semplice(pdf_path, filename):
    """Carica il PDF usando direttamente l'account di servizio"""
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive.file'])
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
        media = MediaFileUpload(pdf_path, mimetype='application/pdf')
        
        # supportsAllDrives=True aiuta se la cartella è condivisa
        file = service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        print(f"✅ Caricato su Drive! ID: {file.get('id')}")
    except Exception as e:
        print(f"❌ Errore Drive: {e}")

def genera_pdf(corsa_data):
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"Rapporto_{corsa_data['autista']}_{timestamp}.pdf".replace(" ", "_")
    pdf_path = os.path.join(TEMP_FOLDER, pdf_filename)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"RAPPORTO USCITA: {corsa_data['autista']}", styles['Heading1']))
    elements.append(Spacer(1, 12))
    
    try:
        km_tot = int(corsa_data["km_arrivo"]) - int(corsa_data["km_partenza"])
    except: km_tot = "N/D"

    table_data = [
        ["VOCE", "DETTAGLIO"],
        ["Autista", corsa_data["autista"]],
        ["KM Totali", str(km_tot)],
        ["Data/Ora", corsa_data["data_ora_arrivo"]]
    ]
    
    t = Table(table_data, colWidths=[1.5*inch, 4*inch])
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.blue)]))
    elements.append(t)
    doc.build(elements)
    
    # ESECUZIONE
    invia_email_standard(pdf_path, pdf_filename)
    carica_pdf_su_drive_semplice(pdf_path, pdf_filename)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "km_partenza": request.form.get("km_partenza"),
                "data_ora_partenza": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
        elif azione == "stop" and "corsa" in session:
            corsa = session.pop("corsa")
            corsa.update({
                "km_arrivo": request.form.get("km_arrivo"),
                "data_ora_arrivo": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            genera_pdf(corsa)
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
