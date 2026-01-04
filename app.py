import os, json, pandas as pd
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "csa_logistica_manuale_2026"

DB_FILE = "stato_furgoni.json"

def salva_stato(stato):
    with open(DB_FILE, "w") as f:
        json.dump(stato, f)

def carica_stato():
    if not os.path.exists(DB_FILE):
        iniziale = {
            "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
            "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
            "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
        }
        salva_stato(iniziale)
        return iniziale
    with open(DB_FILE, "r") as f:
        return json.load(f)

def crea_excel_log(dati):
    try:
        nome_file = f"Corsa_{dati['targa']}_{datetime.now().strftime('%d-%m-%Y_%H%M')}.xlsx"
        df = pd.DataFrame([{
            "Data": dati.get("data_p"),
            "Targa": dati.get("targa"),
            "Autista": dati.get("autista"),
            "Partenza": dati.get("posizione"),
            "KM Partenza": dati.get("km_p"),
            "Destinazione": dati.get("dest_intermedia"),
            "KM Arrivo": dati.get("km_d"),
            "KM Rientro": dati.get("km_rientro"),
            "Fine Corsa": datetime.now().strftime("%d/%m/%Y %H:%M")
        }])
        df.to_excel(nome_file, index=False)
        return nome_file
    except:
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    furgoni = carica_stato()
    targa_attiva = session.get("targa_in_uso")
    corsa_attiva = furgoni.get(targa_attiva) if targa_attiva else None

    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")

        if azione == "start":
            furgoni[targa] = {
                "targa": targa, "stato": "In Viaggio", "posizione": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"), "autista": request.form.get("autista"),
                "step": 1, "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
        elif azione == "arrivo_dest":
            furgoni[targa].update({
                "dest_intermedia": request.form.get("destinazione"),
                "km_d": request.form.get("km_destinazione"),
                "step": 2
            })
            salva_stato(furgoni)
        elif azione == "stop":
            furgoni[targa]["km_rientro"] = request.form.get("km_rientro")
            crea_excel_log(furgoni[targa])
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": request.form.get("km_rientro", 0), "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
        elif azione == "annulla":
            if targa in furgoni: furgoni[targa]["step"] = 0
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
        return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
