import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.secret_key = "valerio_memoria_lunga_2026"

# --- AGGIUNTA: La sessione dura 24 ore anche se chiude il browser ---
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")

@app.route("/", methods=["GET", "POST"])
def index():
    # Rende la sessione permanente (salvata su disco del telefono)
    session.permanent = True 
    
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

            # 2. GENERA PDF PER DOWNLOAD
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setFont("Helvetica-Bold", 18)
            p.drawString(50, 800, "RAPPORTO USCITA FURGONE")
            p.setFont("Helvetica", 12)
            p.drawString(50, 770, f"Autista: {c['autista']} | Targa: {c['targa']}")
            p.drawString(50, 750, f"Percorso: {c['partenza']} -> {dest}")
            p.drawString(50, 730, f"KM: {c['km_p']} -> {km_a}")
            p.drawString(50, 710, f"Orario: {c['data_p']} -> {data_a}")
            p.save()
            buffer.seek(0)

            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"Rapporto_{c['autista']}.pdf",
                mimetype='application/pdf'
            )

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
