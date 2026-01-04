import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "logistica_csa_super_fix_2026"

# Configurazione IA: Prende la chiave da Render
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCxfGEZAcmMc00D6CCwsaAwAC0GY6EAaUc")
genai.configure(api_key=API_KEY)

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
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Analizza la frase: "{msg}"
        Estrai i dati e rispondi SOLO con un oggetto JSON puro.
        Nomi ammessi: Valerio, Daniele, Costantino, Stefano.
        Struttura:
        {{
          "autista": "nome",
          "partenza": "città",
          "km": "numero",
          "destinazione": "città",
          "risposta": "conferma breve"
        }}
        Se un dato non c'è, scrivi null. Non aggiungere commenti.
        """
        
        response = model.generate_content(prompt)
        testo_pulito = response.text.strip()
        
        # SUPER PULITORE: Trova l'inizio { e la fine } del JSON
        inizio = testo_pulito.find('{')
        fine = testo_pulito.rfind('}') + 1
        json_finale = testo_pulito[inizio:fine]
        
        return json.loads(json_finale)
    except Exception as e:
        print(f"ERRORE: {e}")
        return {"risposta": "Non ho capito bene, puoi ripetere?"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
