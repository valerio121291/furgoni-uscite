import os, json, requests
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "csa_2026_final_v5"

# --- CONFIGURAZIONE ---
PPLX_KEY = os.getenv("PPLX_KEY", "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")
DB_FILE = "stato_furgoni.json"

# --- FUNZIONI (DEVONO STARE QUI IN ALTO) ---
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

# --- ROTTE ---
@app.route("/", methods=["GET", "POST"])
def index():
    # Qui Python ha già letto 'carica_stato' sopra, quindi non può fallire
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
        elif azione == "stop" or azione == "annulla":
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": request.form.get("km_rientro", 0), "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
        return redirect(url_for('index'))
    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/chat_ia", methods=["POST"])
def chat_ia():
    try:
        msg = request.get_json().get("messaggio", "")
        headers = {"Authorization": f"Bearer {PPLX_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "sonar",
            "messages": [{"role": "system", "content": "Rispondi SOLO JSON: {\"autista\": \"nome\", \"partenza\": \"città\", \"km\": 0, \"destinazione\": \"città\", \"risposta\": \"breve\"}. Nomi: Valerio, Daniele, Costantino, Stefano."}, {"role": "user", "content": msg}],
            "response_format": {"type": "json_object"}
        }
        r = requests.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except:
        return json.dumps({"risposta": "Errore IA"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
