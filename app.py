import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "valerio_daniele_excel_2026"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")

@app.route("/", methods=["GET", "POST"])
def index():
    session.permanent = True 
    
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
            return redirect("/")
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            dest = request.form.get("destinazione")
            km_a = request.form.get("km_arrivo")
            data_a = datetime.now().strftime("%d/%m/%Y %H:%M")

            # 1. SALVA SU EXCEL
            try:
                if CREDS_JSON and SPREADSHEET_ID:
                    info = json.loads(CREDS_JSON)
                    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                    service = build('sheets', 'v4', credentials=creds)
                    values = [[c['data_p'], data_a, c['autista'], c['targa'], c['partenza'], dest, c['km_p'], km_a]]
                    service.spreadsheets().values().append(
                        spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                        valueInputOption="RAW", body={'values': values}
                    ).execute()
            except Exception as e:
                print(f"Errore Excel: {e}")

            # 2. GENERAZIONE PDF STILE TABELLA EXCEL
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            w, h = A4

            # Titolo
            p.setFont("Helvetica-Bold", 18)
            p.drawCentredString(w/2, h - 50, "RAPPORTO ATTIVITÀ FURGONE")
            
            # Disegno Tabella (Stile Excel)
            y = h - 100
            def draw_row(label, value, y_pos):
                p.setFillColor(colors.lightgrey)
                p.rect(50, y_pos, 150, 25, fill=1) # Cella etichetta
                p.setFillColor(colors.black)
                p.rect(200, y_pos, 350, 25, fill=0) # Cella valore
                p.setFont("Helvetica-Bold", 10)
                p.drawString(60, y_pos + 7, label.upper())
                p.setFont("Helvetica", 11)
                p.drawString(210, y_pos + 7, str(value))

            # Righe della tabella
            draw_row("Autista", c['autista'], y); y -= 25
            draw_row("Targa Veicolo", c['targa'], y); y -= 25
            draw_row("Luogo Partenza", c['partenza'], y); y -= 25
            draw_row("Data/Ora Inizio", c['data_p'], y); y -= 25
            draw_row("KM Iniziali", c['km_p'], y); y -= 40 # Spazio
            
            draw_row("Luogo Arrivo", dest, y); y -= 25
            draw_row("Data/Ora Fine", data_a, y); y -= 25
            draw_row("KM Finali", km_a, y); y -= 40 # Spazio

            # Totale evidenziato
            try:
                totale = int(km_a) - int(c['km_p'])
                p.setFillColor(colors.yellow) # Evidenziatore giallo per il totale
                p.rect(50, y, 500, 30, fill=1)
                p.setFillColor(colors.black)
                p.setFont("Helvetica-Bold", 14)
                p.drawCentredString(w/2, y + 10, f"CHILOMETRI TOTALI PERCORSI: {totale} KM")
            except: pass

            p.showPage()
            p.save()
            buffer.seek(0)

            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"Rapporto_{c['autista']}_{datetime.now().strftime('%d%m')}.pdf",
                mimetype='application/pdf'
            )

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
