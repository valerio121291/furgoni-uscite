from flask import Flask, render_template, request, redirect, session
import os, smtplib, json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "furgoni_2026"

# Credenziali da Render
GMAIL_USER = os.getenv("GMAIL_USER") # pvalerio910@gmail.com
GMAIL_PASS = os.getenv("GMAIL_PASS") # cjareqgaidlqwtnd
DESTINATARIO = "valerio121291@hotmail.it"

def invia_mail(percorso_pdf, nome_file):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = DESTINATARIO
    msg['Subject'] = f"🚚 Rapporto: {nome_file}"
    msg.attach(MIMEText("In allegato il rapporto corsa.", 'plain'))

    try:
        with open(percorso_pdf, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={nome_file}")
            msg.attach(part)

        # Usiamo la porta 587 con un timeout di 30 secondi per Render
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print("✅ EMAIL INVIATA!")
    except Exception as e:
        print(f"❌ ERRORE EMAIL: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        if azione == "start":
            session["corsa"] = {"autista": request.form.get("autista"), "km": request.form.get("km_partenza")}
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            nome_f = f"Rapporto_{datetime.now().strftime('%H%M%S')}.pdf"
            path = f"/tmp/{nome_f}"
            
            # Crea PDF veloce
            doc = SimpleDocTemplate(path, pagesize=letter)
            elements = [Paragraph(f"Rapporto {c['autista']}", getSampleStyleSheet()['Heading1'])]
            doc.build(elements)
            
            # Invia subito
            invia_mail(path, nome_f)
            
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
