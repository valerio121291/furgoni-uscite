import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "valerio_centrale_completa_2026"

# File per non perdere i dati se il server si riavvia
DB_FILE = "stato_furgoni.json"

def carica_stato():
    if not os.path.exists(DB_FILE):
        return {
            "GA087CH": {"stato": "Libero", "posizione": "Base", "km": 0, "autista": "-", "alert": ""},
            "GX942TS": {"stato": "Libero", "posizione": "Base", "km": 0, "autista": "-", "alert": ""},
            "GG862HC": {"stato": "Libero", "posizione": "Base", "km": 0, "autista": "-", "alert": ""}
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
        
        if azione == "start":
            autista = request.form.get("autista")
            km_p = int(request.form.get("km_partenza"))
            stato_globale[targa] = {
                "stato": "In Viaggio",
                "posizione": request.form.get("partenza"),
                "km": km_p,
                "autista": autista,
                "data_p": datetime.now().strftime("%d/%m %H:%M"),
                "alert": ""
            }
            salva_stato(stato_globale)
            session[f"corsa_{targa}"] = stato_globale[targa]
            
        elif azione == "arrivo_dest":
            dest = request.form.get("destinazione")
            km_d = int(request.form.get("km_destinazione"))
            stato_globale[targa].update({"posizione": dest, "km": km_d, "data_d": datetime.now().strftime("%d/%m %H:%M")})
            salva_stato(stato_globale)
            if f"corsa_{targa}" in session:
                session[f"corsa_{targa}"].update({"dest": dest, "km_d": km_d, "data_d": stato_globale[targa]["data_d"]})
                session.modified = True

        elif azione == "stop":
            c = session.pop(f"corsa_{targa}", None)
            km_r = int(request.form.get("km_rientro"))
            data_r = datetime.now().strftime("%d/%m %H:%M")
            
            # Controllo Manutenzione ogni 20.000km
            alert = "⚠️ TAGLIANDO!" if km_r % 20000 > 19000 else ""
            
            stato_globale[targa] = {"stato": "Libero", "posizione": "Tiburtina", "km": km_r, "autista": "-", "alert": alert}
            salva_stato(stato_globale)

            # --- GENERAZIONE PDF (Logica a 3 blocchi) ---
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(300, 800, "REPORT VIAGGIO COMPLETO")
            # (Qui va il codice del PDF che abbiamo già scritto, per brevità lo indico così)
            # ... (Logica draw_step e calcolo totale KM) ...
            p.showPage()
            p.save()
            buffer.seek(0)
            return send_file(buffer, as_attachment=True, download_name=f"Viaggio_{targa}.pdf", mimetype='application/pdf')

    return render_template("form.html", furgoni=stato_globale)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
