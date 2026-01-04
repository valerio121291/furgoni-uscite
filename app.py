import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "valerio_tappe_pro_2026"
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
                "data_p": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "stato": "in_viaggio"
            }
            return redirect("/")
            
        elif azione == "arrivo_dest" and "corsa" in session:
            session["corsa"].update({
                "destinazione": request.form.get("destinazione"),
                "km_d": request.form.get("km_destinazione"),
                "data_d": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "stato": "arrivato"
            })
            session.modified = True
            return redirect("/")

        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            km_r = request.form.get("km_rientro")
            data_r = datetime.now().strftime("%d/%m/%Y %H:%M")

            # 1. SALVA SU GOOGLE SHEETS
            try:
                if CREDS_JSON and SPREADSHEET_ID:
                    info = json.loads(CREDS_JSON)
                    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                    service = build('sheets', 'v4', credentials=creds)
                    values = [[c['data_p'], c['data_d'], data_r, c['autista'], c['targa'], c['partenza'], c['destinazione'], c['km_p'], c['km_d'], km_r]]
                    service.spreadsheets().values().append(
                        spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:J",
                        valueInputOption="RAW", body={'values': values}
                    ).execute()
            except Exception as e: print(f"Errore Excel: {e}")

            # 2. GENERAZIONE PDF PROFESSIONALE
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            w, h = A4
            
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(w/2, h - 50, "RAPPORTO VIAGGIO COMPLETO")
            
            y = h - 100
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y, f"AUTISTA: {c['autista']}")
            p.drawString(300, y, f"VEICOLO: {c['targa']}")
            y -= 30

            def draw_step(title, loc, date, km, y_pos, color):
                p.setFillColor(color)
                p.rect(50, y_pos-55, 500, 55, fill=1)
                p.setFillColor(colors.black)
                p.setFont("Helvetica-Bold", 11)
                p.drawString(60, y_pos - 15, title)
                p.setFont("Helvetica", 10)
                p.drawString(60, y_pos - 32, f"LUOGO: {loc} | ORA: {date}")
                p.drawString(60, y_pos - 47, f"KM: {km}")
                return y_pos - 70

            y = draw_step("1. PARTENZA DALLA BASE", c['partenza'], c['data_p'], c['km_p'], y, colors.lightgrey)
            y = draw_step("2. ARRIVO A DESTINAZIONE", c['destinazione'], c['data_d'], c['km_d'], y, colors.whitesmoke)
            y = draw_step("3. RIENTRO ALLA BASE", c['partenza'], data_r, km_r, y, colors.lightgrey)

            try:
                tot = int(km_r) - int(c['km_p'])
                p.setFillColor(colors.yellow); p.rect(50, y-10, 500, 30, fill=1)
                p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 13)
                p.drawCentredString(w/2, y + 2, f"TOTALE CHILOMETRI PERCORSI: {tot} KM")
            except: pass

            p.showPage(); p.save(); buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name=f"Report_{c['autista']}.pdf", mimetype='application/pdf')

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
