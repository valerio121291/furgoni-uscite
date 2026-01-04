import os, json, io
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Google & IA
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "logistica_csa_2026_ultra"

# Usa la chiave che hai creato prima
genai.configure(api_key="AIzaSyCxfGEZAcmMc00D6CCwsaAwAC0GY6EAaUc")

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
            
        elif azione == "stop":
            # (Logica Excel e PDF rimane la stessa dei messaggi precedenti)
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

        elif azione == "annulla":
            if targa: furgoni[targa]["step"] = 0
            session.pop("targa_in_uso", None)
            salva_stato(furgoni)
            return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/chat_ia", methods=["POST"])
def chat_ia():
    dati = request.json
    msg = dati.get("messaggio", "").lower()
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Prompt ultra-preciso per evitare errori di formato
        prompt = f"""
        Analizza: "{msg}". 
        Estrai i dati e rispondi SOLO con un oggetto JSON. 
        Nomi autisti: Valerio, Daniele, Costantino, Stefano.
        Formato richiesto:
        {{
          "autista": "nome",
          "partenza": "città",
          "km": "numero",
          "destinazione": "città",
          "risposta": "conferma breve"
        }}
        Se un dato manca usa null. Non aggiungere altro testo.
        """
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        
        # Pulizia dei blocchi di codice se l'IA li inserisce
        if "```" in res_text:
            res_text = res_text.split("```")[1]
            if res_text.startswith("json"): res_text = res_text[4:]
        
        return json.loads(res_text)
    except Exception as e:
        print(f"ERRORE IA: {e}")
        return {"risposta": "Non ho capito bene, puoi ripetere?"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
