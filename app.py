import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "valerio_key_2026_blindata"

# File per la memoria permanente
DB_FILE = "stato_furgoni.json"

def carica_stato():
    if not os.path.exists(DB_FILE):
        iniziale = {
            "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
            "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
            "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
        }
        salva_stato(iniziale)
        return iniziale
    with open(DB_FILE, "r") as f: return json.load(f)

def salva_stato(stato):
    with open(DB_FILE, "w") as f: json.dump(stato, f)

@app.route("/", methods=["GET", "POST"])
def index():
    furgoni = carica_stato()
    
    # Cerchiamo se l'utente ha una sessione attiva
    targa_attiva = session.get("targa_in_uso")
    corsa_attiva = furgoni.get(targa_attiva) if targa_attiva else None

    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")

        if azione == "start":
            furgoni[targa] = {
                "stato": "In Viaggio",
                "posizione": request.form.get("partenza"),
                "km": request.form.get("km_partenza"),
                "autista": request.form.get("autista"),
                "step": 1,
                "data_p": datetime.now().strftime("%d/%m %H:%M")
            }
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            
        elif azione == "arrivo_dest":
            furgoni[targa].update({
                "posizione": request.form.get("destinazione"),
                "km_dest": request.form.get("km_destinazione"),
                "step": 2,
                "data_d": datetime.now().strftime("%H:%M")
            })
            salva_stato(furgoni)

        elif azione == "stop":
            # Qui si chiude tutto e si resetta
            furgoni[targa] = {
                "stato": "Libero",
                "posizione": "Tiburtina",
                "km": request.form.get("km_rientro"),
                "autista": "-",
                "step": 0
            }
            session.pop("targa_in_uso", None)
            salva_stato(furgoni)
            return redirect(url_for('index'))

        elif azione == "annulla":
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

        return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
