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

# Caricamento Variabili Ambiente da Render
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
GMAIL_USER = os.getenv("GMAIL_USER")  # La tua email Outlook
GMAIL_PASS = os.getenv("GMAIL_PASS")  # La tua password app snuozokkvcrutrsp

def invia_email_veloce(dati, pdf_content):
    """Invio tramite SSL (Porta 465) - Più stabile su server Cloud"""
    print(f"--- [EMAIL] Tentativo invio a {GMAIL_USER} via SSL ---")
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER 
        msg['Subject'] = f"Rapporto Corsa: {dati['autista']} - {dati['data_a']}"
        
        corpo = f"Rapporto automatico generato per {dati['autista']}.\nData: {dati['data_a']}"
        msg.attach(MIMEText(corpo, 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_content)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=Rapporto_{dati['autista']}.pdf")
        msg.attach(part)

        # Connessione SSL diretta su porta 465
        with smtplib.SMTP_SSL("smtp.office365.com", 465, timeout=30) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        
        print("✅ ✅ ✅ EMAIL SPEDITA CON SUCCESSO!")
    except Exception as e:
        print(f"❌ [EMAIL] ERRORE CRITICO: {e}")

def genera_pdf_buffer(dati):
    """Crea il file PDF in memoria"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    try:
        tot_km = int(dati['km_a']) - int(dati['km_p'])
    except: tot_km = "N/D"

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
    return buffer.getvalue()

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
            print(f"--- [LOG] Corsa iniziata da {request.form.get('autista')} ---")
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            c.update({
                "destinazione": request.form.get("destinazione"),
                "km_a": request.form.get("km_arrivo"),
                "data_a": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            
            # 1. Scrittura su Google Sheets
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], c['data_a'], c['autista'], c['targa'], c['partenza'], c['destinazione'], c['km_p'], c['km_a']]]
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                    valueInputOption="RAW", body={'values': values}
                ).execute()
                print("✅ [LOG] Excel aggiornato")
            except Exception as e:
                print(f"❌ [LOG] Errore Excel: {e}")

            # 2. Generazione PDF e Invio Email in Background
            pdf_content = genera_pdf_buffer(c)
            # Avviamo il thread per non bloccare il caricamento della pagina
            email_thread = threading.Thread(target=invia_email_veloce, args=(c, pdf_content))
            email_thread.start()
                
        return redirect("/")
    
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
