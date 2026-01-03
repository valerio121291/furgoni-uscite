from flask import Flask, render_template, request, redirect, session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
# Chiave segreta per gestire le sessioni degli utenti
app.secret_key = os.getenv("SECRET_KEY", "furgoni-secret-2024")

# Configurazione IDs (Sostituisci o usa variabili d'ambiente su Render)
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1Hk-GOKdMts3Qm1qgkt9V58YUoP6Hrshl")
DESTINATARIO_EMAIL = "valerio121291@hotmail.it" 

# Render richiede l'uso di /tmp per scrivere file temporaneamente
TEMP_FOLDER = "/tmp/furgoni"

def invia_email_outlook(pdf_path, filename):
    """Invia il PDF tramite SMTP di Outlook/Hotmail"""
    mittente = os.getenv("OUTLOOK_USER")  # valerio121291@hotmail.it
    password = os.getenv("OUTLOOK_PASS")  # La tua Password per le App
    
    if not mittente or not password:
        print("⚠️ Errore: Credenziali email non trovate nelle variabili d'ambiente.")
        return

    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = DESTINATARIO_EMAIL
    msg['Subject'] = f"🚚 Rapporto Corsa: {filename}"

    corpo = f"Ciao Valerio,\n\nIn allegato trovi il PDF della corsa completata in data {datetime.now().strftime('%d/%m/%Y')}."
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)

        # Connessione al server Microsoft Office 365 / Hotmail
        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()  # Avvia crittografia sicura
            server.login(mittente, password)
            server.send_message(msg)
        
        print(f"✅ Email inviata con successo a {DESTINATARIO_EMAIL}")
    except Exception as e:
        print(f"❌ Errore critico invio email: {e}")

def carica_pdf_su_drive(pdf_path, filename):
    """Carica il file PDF nella cartella specifica di Google Drive"""
    try:
        creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=['https://www.googleapis.com/auth/drive'])
        else:
            # Fallback locale per test
            creds = Credentials.from_service_account_file("credentials.json", scopes=['https://www.googleapis.com/auth/drive'])
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
        media = MediaFileUpload(pdf_path, mimetype='application/pdf')
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        print(f"✅ PDF caricato su Google Drive. ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        print(f"❌ Errore caricamento Drive: {e}")
        return None

def genera_pdf(corsa_data):
    """Crea il documento PDF con i dati della corsa"""
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"Corsa_{corsa_data['autista']}_{timestamp}.pdf"
    pdf_path = os.path.join(TEMP_FOLDER, pdf_filename)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Intestazione
    title = Paragraph("RAPPORTO USCITA FURGONE", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Tabella Dati
    km_percorsi = int(corsa_data["km_arrivo"]) - int(corsa_data["km_partenza"])
    table_data = [
        ["DESCRIZIONE", "DETTAGLIO"],
        ["Autista", corsa_data["autista"]],
        ["Furgone (Targa)", corsa_data["targa"]],
        ["Luogo Partenza", corsa_data["partenza"]],
        ["Destinazione", corsa_data["destinazione"]],
        ["KM alla Partenza", corsa_data["km_partenza"]],
        ["KM all'Arrivo", corsa_data["km_arrivo"]],
        ["Totale KM Percorsi", str(km_percorsi)],
        ["Orario Inizio", corsa_data["data_ora_partenza"]],
        ["Orario Fine", corsa_data["data_ora_arrivo"]]
    ]
    
    t = Table(table_data, colWidths=[2*inch, 3.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    
    # Generazione file
    doc.build(elements)
    
    # Esecuzione azioni esterne
    carica_pdf_su_drive(pdf_path, pdf_filename)
    invia_email_outlook(pdf_path, pdf_filename)
    
    return pdf_path

@app.route("/", methods=["GET", "POST"])
def registra_uscita():
    if request.method == "POST":
        azione = request.form.get("azione")

        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"),
                "km_partenza": request.form.get("km_partenza"),
                "data_ora_partenza": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            return redirect("/")

        elif azione == "stop" and "corsa" in session:
            corsa = session.pop("corsa")
            corsa.update({
                "destinazione": request.form.get("destinazione"),
                "km_arrivo": request.form.get("km_arrivo"),
                "data_ora_arrivo": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            genera_pdf(corsa)
            return redirect("/")

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    # La porta è dinamica per Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
