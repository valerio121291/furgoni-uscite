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
app.secret_key = os.getenv("SECRET_KEY", "furgoni-2026-secure-v2")

# Configurazione dalle variabili d'ambiente di Render
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1Hk-GOKdMts3Qm1qgkt9V58YUoP6Hrshl")
DESTINATARIO_EMAIL = "valerio121291@hotmail.it" 
TEMP_FOLDER = "/tmp/furgoni"

def invia_email_gmail(pdf_path, filename):
    """Invia il PDF tramite Gmail usando Password per le App"""
    mittente = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS")

    if not mittente or not password:
        print("⚠️ Errore: Credenziali GMAIL_USER o GMAIL_PASS mancanti.")
        return

    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = DESTINATARIO_EMAIL
    msg['Subject'] = f"🚚 Rapporto Furgoni: {filename}"

    corpo = f"Ciao Valerio,\n\nIn allegato il rapporto della corsa terminata il {datetime.now().strftime('%d/%m/%Y %H:%M')}."
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(mittente, password)
            server.send_message(msg)
        print(f"✅ Email inviata con successo a {DESTINATARIO_EMAIL}")
    except Exception as e:
        print(f"❌ Errore invio email: {e}")

def carica_pdf_su_drive(pdf_path, filename):
    """Carica il PDF su Drive forzando i permessi per evitare errore quota 403"""
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if not creds_json:
            print("⚠️ Errore: Variabile GOOGLE_CREDENTIALS non trovata.")
            return None

        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive'])
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': filename, 
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(pdf_path, mimetype='application/pdf')
        
        # supportsAllDrives=True è necessario per account di servizio
        file = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        print(f"✅ PDF caricato su Google Drive. ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        print(f"❌ Errore caricamento Drive (Quota/Permessi): {e}")
        return None

def genera_pdf(corsa_data):
    """Crea il file PDF e avvia i processi di invio"""
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
    except:
        km_tot = "N/D"

    table_data = [
        ["VOCE", "DETTAGLIO"],
        ["Autista", corsa_data["autista"]],
        ["Targa", corsa_data["targa"]],
        ["Partenza", corsa_data["partenza"]],
        ["Destinazione", corsa_data["destinazione"]],
        ["KM Inizio", corsa_data["km_partenza"]],
        ["KM Fine", corsa_data["km_arrivo"]],
        ["Totale KM", str(km_tot)],
        ["Data Ora", corsa_data["data_ora_arrivo"]]
    ]
    
    t = Table(table_data, colWidths=[1.5*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    doc.build(elements)
    
    # Esegui caricamento e invio
    # Se uno fallisce, l'altro proverà comunque
    carica_pdf_su_drive(pdf_path, pdf_filename)
    invia_email_gmail(pdf_path, pdf_filename)
    
    return pdf_path

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")

        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"),
                "km_partenza": request.form.get("km_partenza"),
                "data_ora_partenza": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
        elif azione == "stop" and "corsa" in session:
            corsa = session.pop("corsa")
            corsa.update({
                "destinazione": request.form.get("destinazione"),
                "km_arrivo": request.form.get("km_arrivo"),
                "data_ora_arrivo": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
         #genera_pdf(corsa)
        
        return redirect("/")

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
