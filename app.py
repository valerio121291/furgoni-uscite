from flask import Flask, render_template, request, redirect, session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
import gspread
import os
from datetime import datetime
import io

app = Flask(__name__)
app.secret_key = "super-segreto-furgoni-123"

# Configurazione Google Sheets
SPREADSHEET_ID = "13vzhKIN6GkFaGhoPkTX0vnUNGZy6wcMT0JWZCpIsx68"  # ← AGGIORNA CON TUO ID
SHEET_NAME = "Foglio1"
FURGONI_FOLDER = "furgoni"

# Carica le credenziali da variabile d'ambiente o file
def get_sheets_client():
    """Ottiene un client di Google Sheets autenticato"""
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    if creds_json:
        import json
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    
    gc = gspread.authorize(creds)
    return gc


def salva_su_sheets(dati_corsa):
    """Salva i dati della corsa su Google Sheets"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        
        # Aggiungi la riga ai dati del foglio
        sheet.append_row([
            dati_corsa["data_ora_partenza"],
            dati_corsa["data_ora_arrivo"],
            dati_corsa["autista"],
            dati_corsa["targa"],
            dati_corsa["partenza"],
            dati_corsa["destinazione"],
            dati_corsa["km_partenza"],
            dati_corsa["km_arrivo"],
        ])
        print("✅ Dati salvati su Google Sheets")
    except Exception as e:
        print(f"❌ Errore salvataggio su Google Sheets: {e}")

def genera_pdf(corsa_data):
    """Genera un PDF non modificabile della corsa"""
    autista = corsa_data["autista"]
    cartella_autista = os.path.join(FURGONI_FOLDER, autista)
    os.makedirs(cartella_autista, exist_ok=True)
    
    timestamp = corsa_data["data_ora_partenza"].replace(" ", "_").replace(":", "-")
    pdf_filename = f"{timestamp}_{autista}.pdf"
    pdf_path = os.path.join(cartella_autista, pdf_filename)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=1
    )
    elements.append(Paragraph("Rapporto Corsa Furgone", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    data = [
        ["Campo", "Valore"],
        ["Data/Ora Partenza", corsa_data["data_ora_partenza"]],
        ["Data/Ora Arrivo", corsa_data["data_ora_arrivo"]],
        ["Autista", corsa_data["autista"]],
        ["Targa Furgone", corsa_data["targa"]],
        ["Luogo Partenza", corsa_data["partenza"]],
        ["Destinazione", corsa_data["destinazione"]],
        ["KM Partenza", corsa_data["km_partenza"]],
        ["KM Arrivo", corsa_data["km_arrivo"]],
        ["KM Percorsi", str(int(corsa_data["km_arrivo"]) - int(corsa_data["km_partenza"]))],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    footer_text = f"Documento generato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=2)
    elements.append(Paragraph(footer_text, footer_style))
    
    doc.build(elements)
    print(f"✅ PDF generato: {pdf_path}")
    return pdf_path

@app.route("/", methods=["GET", "POST"])
def registra_uscita():
    corsa_in_corso = "corsa" in session

    if request.method == "POST":
        azione = request.form.get("azione")

        if azione == "start":
            autista = request.form.get("autista", "").strip()
            targa = request.form.get("targa", "").strip()
            partenza = request.form.get("partenza", "").strip()
            km_partenza = request.form.get("km_partenza", "").strip()
            data_ora_partenza = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            session["corsa"] = {
                "data_ora_partenza": data_ora_partenza,
                "autista": autista,
                "targa": targa,
                "partenza": partenza,
                "km_partenza": km_partenza,
            }
            return redirect("/")

        elif azione == "stop" and corsa_in_corso:
            destinazione = request.form.get("destinazione", "").strip()
            km_arrivo = request.form.get("km_arrivo", "").strip()
            data_ora_arrivo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            corsa = session["corsa"]
            corsa_completa = {
                "data_ora_partenza": corsa["data_ora_partenza"],
                "data_ora_arrivo": data_ora_arrivo,
                "autista": corsa["autista"],
                "targa": corsa["targa"],
                "partenza": corsa["partenza"],
                "destinazione": destinazione,
                "km_partenza": corsa["km_partenza"],
                "km_arrivo": km_arrivo,
            }

            # 1. Salva su Google Sheets
            salva_su_sheets(corsa_completa)

            # 2. Genera PDF
            genera_pdf(corsa_completa)

            # Pulisci la sessione
            session.pop("corsa", None)
            return redirect("/")

    corsa = session.get("corsa")
    return render_template("form.html", corsa=corsa, corsa_in_corso=bool(corsa))

if __name__ == "__main__":
    print("Avvio Flask su http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
