import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "valerio_centrale_2026_full"

# DATABASE LOCALE PER DASHBOARD
DB_FILE = "stato_furgoni.json"
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")

def carica_stato():
    if not os.path.exists(DB_FILE):
        return {
            "GA087CH": {"stato": "Libero", "posizione": "Tiburtina", "km": 0, "autista": "-", "alert": ""},
            "GX942TS": {"stato": "Libero", "posizione": "Tiburtina", "km": 0, "autista": "-", "alert": ""},
            "GG862HC": {"stato": "Libero", "posizione": "Tiburtina", "km": 0, "autista": "-", "alert": ""}
        }
    with open(DB_FILE, "r") as f: return json.load(f)

def salva_stato(stato):
    with open(DB_FILE, "w") as f: json.dump(stato, f)

@app.route("/", methods=["GET", "POST"])
def index():
    stato_globale = carica_stato()
    
    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")
        
        # 1. INIZIO VIAGGIO
        if azione == "start":
            autista = request.form.get("autista")
            partenza = request.form.get("partenza")
            km_p = int(request.form.get("km_partenza"))
            data_p = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            stato_globale[targa] = {
                "stato": "In Viaggio", "posizione": partenza, "km": km_p, 
                "autista": autista, "data_p": data_p, "alert": ""
            }
            salva_stato(stato_globale)
            session[f"corsa_{targa}"] = stato_globale[targa]
            session[f"corsa_{targa}"]["targa"] = targa
            return redirect("/")

        # 2. ARRIVO A DESTINAZIONE (META' CORSA)
        elif azione == "arrivo_dest" and f"corsa_{targa}" in session:
            dest = request.form.get("destinazione")
            km_d = int(request.form.get("km_destinazione"))
            data_d = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            stato_globale[targa].update({"posizione": dest, "km": km_d})
            salva_stato(stato_globale)
            
            session[f"corsa_{targa}"].update({"dest": dest, "km_d": km_d, "data_d": data_d, "step": 2})
            session.modified = True
            return redirect("/")

        # 3. FINE E PDF
        elif azione == "stop" and f"corsa_{targa}" in session:
            c = session.pop(f"corsa_{targa}")
            km_r = int(request.form.get("km_rientro"))
            data_r = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # Manutenzione ogni 20.000 km
            alert = "⚠️ TAGLIANDO!" if km_r % 20000 > 19500 else ""
            stato_globale[targa] = {"stato": "Libero", "posizione": "Tiburtina", "km": km_r, "autista": "-", "alert": alert}
            salva_stato(stato_globale)

            # SALVA SU EXCEL
            try:
                if CREDS_JSON and SPREADSHEET_ID:
                    info = json.loads(CREDS_JSON)
                    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                    service = build('sheets', 'v4', credentials=creds)
                    values = [[c['data_p'], c.get('data_d','-'), data_r, c['autista'], targa, c['posizione'], c.get('dest','-'), c['km'], c.get('km_d',0), km_r]]
                    service.spreadsheets().values().append(
                        spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:J",
                        valueInputOption="RAW", body={'values': values}
                    ).execute()
            except: pass

            # GENERAZIONE PDF
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(300, 800, "RAPPORTO VIAGGIO COMPLETO")
            
            y = 750
            def draw_s(tit, loc, dt, km, y_p, col):
                p.setFillColor(col); p.rect(50, y_p-50, 500, 50, fill=1)
                p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 10)
                p.drawString(60, y_p-15, tit)
                p.setFont("Helvetica", 9); p.drawString(60, y_p-30, f"LUOGO: {loc} | ORE: {dt} | KM: {km}")
                return y_p - 65

            y = draw_s("1. PARTENZA", c['posizione'], c['data_p'], c['km'], y, colors.lightgrey)
            y = draw_s("2. DESTINAZIONE", c.get('dest','-'), c.get('data_d','-'), c.get('km_d',0), y, colors.whitesmoke)
            y = draw_s("3. RIENTRO", "Tiburtina", data_r, km_r, y, colors.lightgrey)
            
            p.showPage(); p.save(); buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name=f"Report_{targa}.pdf", mimetype='application/pdf')

    return render_template("form.html", furgoni=stato_globale)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
