import os, json, requests, pandas as pd
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "csa_logistica_2026_full_dest"

# CONFIGURAZIONE CHIAVI
PPLX_KEY = os.getenv("PPLX_KEY", "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")
DB_FILE = "stato_furgoni.json"

# --- 1. FUNZIONI DI SERVIZIO (DEVONO STARE IN ALTO) ---

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

def crea_excel_log(dati):
    """Genera un file Excel con i dati della corsa appena terminata"""
    try:
        nome_file = f"Corsa_{dati['targa']}_{datetime.now().strftime('%d-%m-%Y')}.xlsx"
        # Organizziamo i dati per le colonne dell'Excel
        report = [{
            "Data": dati.get("data_p", "-"),
            "Targa": dati.get("targa", "-"),
            "Autista": dati.get("autista", "-"),
            "Partenza": dati.get("posizione", "-"),
            "KM Partenza": dati.get("km_p", 0),
            "Destinazione": dati.get("dest_intermedia", "-"),
            "KM Arrivo": dati.get("km_d", 0),
            "KM Rientro": dati.get("km_rientro", 0),
            "Data Fine": datetime.now().strftime("%d/%m/%Y %H:%M")
        }]
        df = pd.DataFrame(report)
        df.to_excel(nome_file, index=False)
        print(f"Excel Creato: {nome_file}")
        return nome_file
    except Exception as e:
        print(f"Errore creazione Excel: {e}")
        return None

# --- 2. ROTTE DEL SITO ---

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
            if targa in furgoni:
                furgoni[targa].update({
                    "dest_intermedia": request.form.get("destinazione"),
                    "km_d": request.form.get("km_destinazione"),
                    "step": 2, "data_d": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                salva_stato(furgoni)

        elif azione == "stop":
            if targa in furgoni:
                furgoni[targa]["km_rientro"] = request.form.get("km_rientro")
                # Genera Excel prima di resettare
                crea_excel_log(furgoni[targa])
                
                # Reset furgone
                furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": request.form.get("km_rientro", 0), "autista": "-", "step": 0}
                salva_stato(furgoni)
                session.pop("targa_in_uso", None)

        elif azione == "annulla":
            if targa in furgoni: furgoni[targa]["step"] = 0
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            
        return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/chat_ia", methods=["POST"])
def chat_ia():
    try:
        msg = request.get_json().get("messaggio", "")
        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system", 
                    "content": """Estrai dati. Rispondi SOLO JSON. 
                    Nomi: Valerio, Daniele, Costantino, Stefano. 
                    Luoghi: Tiburtina, Rieti, Sede, L'Aquila, Roma.
                    Formato: {"autista": "nome", "partenza": "luogo", "km": 0, "destinazione": "luogo", "risposta": "breve"}. 
                    Se manca qualcosa metti null."""
                },
                {"role": "user", "content": msg}
            ],
            "response_format": {"type": "json_object"}
        }
        headers = {"Authorization": f"Bearer {PPLX_KEY}", "Content-Type": "application/json"}
        r = requests.post(url, json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except:
        return json.dumps({"risposta": "Errore collegamento IA."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
