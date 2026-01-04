import os, json, io
from flask import Flask, render_template, request, session, send_file
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "valerio_forza_pdf_2026"

# Configurazione Render
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
            return redirect("/")
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            dest = request.form.get("destinazione")
            km_a = request.form.get("km_arrivo")
            data_a = datetime.now().strftime("%d/%m %H:%M")

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

            # 2. GENERA IL PDF (Questo file verrà scaricato dall'autista)
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setFont("Helvetica-Bold", 18)
            p.drawString(50, 800, "RAPPORTO USCITA FURGONE")
            p.line(50, 795, 550, 795)
            
            p.setFont("Helvetica", 12)
            p.drawString(50, 770, f"Autista: {c['autista']}")
            p.drawString(50, 755, f"Targa: {c['targa']}")
            p.drawString(50, 730, f"Partenza: {c['partenza']} - {c['data_p']} (KM: {c['km_p']})")
            p.drawString(50, 715, f"Arrivo: {dest} - {data_a} (KM: {km_a})")
            
            try:
                p.setFont("Helvetica-Bold", 14)
                p.drawString(50, 680, f"TOTALE PERCORSO: {int(km_a) - int(c['km_p'])} km")
            except: pass
            
            p.showPage()
            p.save()
            buffer.seek(0)

            # IL COMANDO CHE SCARICA IL FILE
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"Rapporto_{c['autista']}.pdf",
                mimetype='application/pdf'
            )

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

# Aggiunto redirect per pulire la pagina dopo lo start
from flask import redirect

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
