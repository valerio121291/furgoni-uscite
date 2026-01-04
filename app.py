import os, json, io
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "furgoni_2026_valerio")

# CONFIGURAZIONI RENDER
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")

def get_google_services():
    info = json.loads(CREDS_JSON)
    creds = Credentials.from_service_account_info(info, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ])
    return build('sheets', 'v4', credentials=creds), build('drive', 'v3', credentials=creds)

def salva_pdf_su_drive(dati, drive_service):
    """Crea un PDF e lo carica forzando i parametri di compatibilità per Service Account"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    try:
        tot_km = int(dati['km_a']) - int(dati['km_p'])
    except:
        tot_km = "N/D"

    elementi = [
        Paragraph(f"RAPPORTO CORSA - {dati['autista']}", styles['Heading1']),
        Spacer(1, 12),
        Table([
            ["Data Inizio", dati['data_p']], ["Data Fine", dati['data_a']],
            ["Autista", dati['autista']], ["Targa", dati['targa']],
            ["Da", dati['partenza']], ["A", dati['destinazione']],
            ["KM Partenza", dati['km_p']], ["KM Arrivo", dati['km_a']],
            ["TOTALE KM", str(tot_km)]
        ], style=TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
            ('PADDING', (0,0), (-1,-1), 8)
        ])),
    ]
    doc.build(elementi)
    buffer.seek(0)
    
    nome_file = f"Rapporto_{dati['autista']}_{datetime.now().strftime('%d%m%Y_%H%M')}.pdf"
    media = MediaIoBaseUpload(buffer, mimetype='application/pdf')
    
    # PARAMETRI CRITICI: supportsAllDrives=True permette di usare lo spazio della cartella padre
    drive_service.files().create(
        body={'name': nome_file, 'parents': [FOLDER_ID]},
        media_body=media,
        fields='id',
        supportsAllDrives=True
    ).execute()
    print(f"✅ PDF caricato con successo nella cartella")

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
            
            try:
                sheets_service, drive_service = get_google_services()
                
                # 1. Scrittura Excel
                sheets_service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                    valueInputOption="RAW", body={'values': [[
                        c['data_p'], c['data_a'], c['autista'], c['targa'],
                        c['partenza'], c['destinazione'], c['km_p'], c['km_a']
                    ]]}
                ).execute()
                
                # 2. Creazione PDF
                salva_pdf_su_drive(c, drive_service)
            except Exception as e:
                print(f"❌ Errore durante il salvataggio: {e}")
                
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
