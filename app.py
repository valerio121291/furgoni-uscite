import os, json, io, requests
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "csa_perplexity_2026"

# CHIAVE PERPLEXITY
PPLX_KEY = "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"

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
            return redirect(url_for('index'))
        elif azione == "stop" or azione == "annulla":
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))
            
    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/chat_ia", methods=["POST"])
def chat_ia():
    try:
        dati = request.get_json()
        msg = dati.get("messaggio", "")
        
        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "sonar", # Modello veloce ed efficace
            "messages": [
                {
                    "role": "system",
                    "content": "Estrai dati logistici. Rispondi SOLO in JSON: {\"autista\": \"...\", \"partenza\": \"...\", \"km\": 0, \"destinazione\": \"...\", \"risposta\": \"...\"}. Nomi: Valerio, Daniele, Costantino, Stefano. Se mancano dati metti null."
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
        res_data = response.json()
        content = res_data['choices'][0]['message']['content']
        
        return json.loads(content)
        
    except Exception as e:
        print(f"Errore PPLX: {e}")
        return {"risposta": "Perplexity non ha risposto correttamente."}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
