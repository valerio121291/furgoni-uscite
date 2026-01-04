import os, json, io, requests
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "csa_logistica_2026_pplx_final"

# CHIAVE PERPLEXITY
PPLX_KEY = os.getenv("PPLX_KEY", "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")
DB_FILE = "stato_furgoni.json"

# --- 1. PRIMA DEFINIAMO LE FUNZIONI (LE FONDAMENTA) ---

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
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

# --- 2. POI DEFINIAMO LE ROTTE (IL SITO VERO E PROPRIO) ---

@app.route("/", methods=["GET", "POST"])
def index():
    # Ora Python sa già cos'è carica_stato perché l'ha letto sopra!
    furgoni = carica_stato()
    targa_attiva = session.get("targa_in_uso")
    corsa_attiva = furgoni.get(targa_attiva) if targa_attiva else None

    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")

        if azione == "start":
            furgoni[targa] = {
                "targa": targa, 
                "stato": "In Viaggio", 
                "posizione": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"), 
                "autista": request.form.get("autista"),
                "step": 1, 
                "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        elif azione == "arrivo_dest":
            if targa in furgoni:
                furgoni[targa].update({
                    "dest_intermedia": request.form.get("destinazione"),
                    "km_d": request.form.get("km_destinazione"),
                    "step": 2, 
                    "data_d": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                salva_stato(furgoni)
            return redirect(url_for('index'))

        elif azione == "stop":
            if targa in furgoni:
                furgoni[targa] = {
                    "stato": "Libero", 
                    "posizione": "Sede", 
                    "km": request.form.get("km_rientro"), 
                    "autista": "-", 
                    "step": 0
                }
                salva_stato(furgoni)
                session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

        elif azione == "annulla":
            if targa and targa in furgoni:
                furgoni[targa]["stato"] = "Libero"
                furgoni[targa]["step"] = 0
            session.pop("targa_in_uso", None)
            salva_stato(furgoni)
            return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/chat_ia", methods=["POST"])
def chat_ia():
    try:
        dati = request.get_json()
        msg = dati.get("messaggio", "")
        
        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": "Rispondi SOLO in JSON: {\"autista\": \"nome\", \"partenza\": \"città\", \"km\": 0, \"destinazione\": \"città\", \"risposta\": \"breve\"}. Nomi: Valerio, Daniele, Costantino, Stefano."
                },
                {"role": "user", "content": msg}
            ],
            "response_format": { "type": "json_object" }
        }
        headers = {
            "Authorization": f"Bearer {PPLX_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
        
    except Exception as e:
        return json.dumps({"risposta": "Errore collegamento IA."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
