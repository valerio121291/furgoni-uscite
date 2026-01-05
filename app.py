import os, json, io, requests
from flask import Flask, render_template, request, session, send_file, redirect, url_for, jsonify
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from upstash_redis import Redis

app = Flask(__name__)
app.secret_key = "logistica_csa_valerio_2026_top"

# Inizializzazione Redis con i nomi variabili esatti di Vercel/Upstash
try:
    kv = Redis(url=os.getenv("KV_REST_API_URL"), token=os.getenv("KV_REST_API_TOKEN"))
except:
    kv = None

STATO_INIZIALE = {
    "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
    "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
    "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
}

def carica_stato():
    if not kv: return STATO_INIZIALE
    try:
        s = kv.get("stato_furgoni")
        return s if isinstance(s, dict) else json.loads(s)
    except: return STATO_INIZIALE

def salva_stato(s):
    if kv: kv.set("stato_furgoni", json.dumps(s))

@app.route("/", methods=["GET", "POST"])
def index():
    furgoni = carica_stato()
    targa_attiva = session.get("targa_in_uso")
    corsa_attiva = furgoni.get(targa_attiva) if targa_attiva else None
    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")
        if azione == "start":
            furgoni[targa] = {"targa": targa, "stato": "In Viaggio", "posizione": request.form.get("partenza"), "km_p": request.form.get("km_partenza"), "autista": request.form.get("autista"), "step": 1, "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")}
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
        elif azione == "stop":
            # (Codice PDF e Sheets abbreviato per brevità, tieni quello precedente se vuoi)
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
        return redirect(url_for('index'))
    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

if __name__ == "__main__":
    app.run()
