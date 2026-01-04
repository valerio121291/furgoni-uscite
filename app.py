import os, json, io
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = "csa_ultra_stabile_2026"

# Configurazione IA: Assicurati che su Render in Environment ci sia GEMINI_API_KEY
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCxfGEZAcmMc00D6CCwsaAwAC0GY6EAaUc")
genai.configure(api_key=API_KEY)

@app.route("/", methods=["GET", "POST"])
def index():
    # ... (il resto della logica furgoni rimane uguale a prima)
    return render_template("form.html", furgoni=carica_stato(), targa_attiva=session.get("targa_in_uso"))

@app.route("/chat_ia", methods=["POST"])
def chat_ia():
    try:
        dati = request.get_json()
        msg = dati.get("messaggio", "")
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prompt super-comando: l'IA deve rispondere SOLO il JSON
        prompt = f"""
        Estrai i dati da questa frase: "{msg}"
        Rispondi esclusivamente con un oggetto JSON. 
        Campi: autista (Valerio, Daniele, Costantino, Stefano), partenza, km, destinazione, risposta (una frase breve).
        Esempio: {{"autista": "Valerio", "partenza": "Tiburtina", "km": 1000, "destinazione": null, "risposta": "Ricevuto"}}
        Non aggiungere commenti o spiegazioni.
        """
        
        response = model.generate_content(prompt)
        testo = response.text.strip()
        
        # Pulizia chirurgica: prende solo ciò che è dentro le parentesi graffe
        start = testo.find('{')
        end = testo.rfind('}') + 1
        if start == -1:
            return {"risposta": "Non ho trovato dati nella frase."}
            
        json_valido = testo[start:end]
        return json.loads(json_valido)
        
    except Exception as e:
        print(f"Errore: {e}")
        return {"risposta": "C'è stato un piccolo errore tecnico, riprova."}
