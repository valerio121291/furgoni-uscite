from flask import Flask, render_template, request, redirect, session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

app = Flask(__name__)
# Chiave segreta per gestire la sessione (inizio/fine corsa)
app.secret_key = os.getenv("SECRET_KEY", "furgoni-2026-valerio-v4")

DESTINATARIO_EMAIL = "valerio121291@hotmail.it" 
TEMP_FOLDER = "/tmp/furgoni"

def invia_email_gmail(pdf_path, filename):
    """Invia il PDF tramite Gmail usando la porta 587 (TLS)"""
    mittente = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_PASS")

    if not mittente or not password:
        print("⚠️ DEBUG: Credenziali Gmail (USER o PASS) mancanti su Render!")
        return

    msg = MIMEMultipart()
    msg['From'] = mittente
    msg['To'] = DESTINATARIO_EMAIL
    msg['Subject'] = f"🚚 Rapporto Furgoni: {filename}"

    corpo = f"Ciao Valerio,\n\nIn allegato trovi il rapporto PDF della corsa terminata il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}."
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)

        print("DEBUG: Tentativo connessione SMTP (Porta 587)...")
        # Connessione SMTP standard con TLS
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=20)
        server.set_debuglevel(1) # Questo mostrerà più dettagli nei log di Render
        server.starttls() 
        server.login(mittente, password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email inviata con successo a {DESTINATARIO_EMAIL}")
    except Exception as e:
        print(f"❌ Errore SMTP: {e}")

def genera_pdf(corsa_data):
    """Genera il file PDF nella cartella temporanea"""
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
        km_tot = "Dato non valido"

    table_data = [
        ["VOCE", "DETTAGLIO"],
        ["Autista", corsa_data["autista"]],
        ["Targa", corsa_data["targa"]],
        ["Partenza", corsa_data["partenza"]],
        ["Destinazione", corsa_data["destinazione"]],
        ["KM Inizio", corsa_data["km_partenza"]],
        ["KM Fine", corsa_data["km_arrivo"]],
        ["Totale KM", str(km_tot)],
        ["Ora Fine", corsa_data["data_ora_arrivo"]]
    ]
    
    t = Table(table_data, colWidths=[1.5*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    doc.build(elements)
    
    # Avvia l'invio dell'email
    invia_email_gmail(pdf_path, pdf_filename)
    return pdf_path

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        print(f"DEBUG: Ricevuta azione {azione}")
        
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
            print(f"DEBUG: Avvio generazione PDF e Invio Email...")
            genera_pdf(corsa)
        
        return redirect("/")
    
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
