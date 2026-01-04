import os, json, io
from flask import Flask, render_template, request, session, send_file
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "valerio_pdf_final_2026"

# Configurazione
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")

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
                "data_p": datetime.now().strftime("%d/%m %H:%M")
            }
            return render_template("form.html", corsa=session["corsa"], corsa_in_corso=True)
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            dest = request.form.get("destinazione")
            km_a = request.form.get("km_arrivo")
            data_a = datetime.now().strftime("%d/%m %H:%M")

            # 1. SALVATAGGIO EXCEL (Silenzioso)
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

            # 2. GENERAZIONE PDF
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setTitle(f"Rapporto_{c['autista']}")
            
            # Disegno del PDF
            p.setFont("Helvetica-Bold", 20)
            p.drawString(50, 800, "REPORT USCITA FURGONE")
            p.line(50, 790, 550, 790)
            
            p.setFont("Helvetica", 14)
            p.drawString(50, 760, f"Autista: {c['autista']}")
            p.drawString(50, 740, f"Targa Veicolo: {c['targa']}")
            
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, 700, "DETTAGLI VIAGGIO:")
            p.setFont("Helvetica", 12)
            p.drawString(50, 680, f"Partenza da: {c['partenza']} ({c['data_p']}) - KM: {c['km_p']}")
            p.drawString(50, 660, f"Arrivo a: {dest} ({data_a}) - KM: {km_a}")
            
            try:
                totale = int(km_a) - int(c['km_p'])
                p.setFont("Helvetica-Bold", 14)
                p.drawString(50, 620, f"CHILOMETRI TOTALI: {totale} km")
            except:
                pass

            p.showPage()
            p.save()
            buffer.seek(0)

            # 3. INVIO DEL FILE PDF AL BROWSER (Scarica sul telefono)
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"Rapporto_{c['autista']}_{datetime.now().strftime('%d%m')}.pdf",
                mimetype='application/pdf'
            )

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

