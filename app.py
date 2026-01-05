import os, json, requests, re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# CONFIGURAZIONE
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "TUO_TOKEN_PERPLEXITY_QUI")

@app.route("/")
def index():
    # Definiamo uno stato fittizio per far caricare il form.html
    furgoni_test = {
        "GA087CH": {"stato": "Libero"},
        "GX942TS": {"stato": "Libero"},
        "GG862HC": {"stato": "Libero"}
    }
    return render_template("form.html", furgoni=furgoni_test, targa_attiva=None)

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        data = request.json
        testo = data.get("testo", "")
        print(f"Testo da analizzare: {testo}")

        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        # PROMPT OTTIMIZZATO: Specificato meglio il campo partenza e km
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system", 
                    "content": (
                        "Sei un assistente logistico. Estrai dati da un comando vocale. "
                        "Mappe furgoni: 'piccolo'->GA087CH, 'medio'->GX942TS, 'grande' o 'grosso'->GG862HC. "
                        "Rispondi ESCLUSIVAMENTE con un oggetto JSON. "
                        "Se un dato manca, usa una stringa vuota o 0 per i km."
                    )
                },
                {
                    "role": "user", 
                    "content": f"Estrai in JSON {{targa, autista, km, partenza}} da questo testo: {testo}"
                }
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        
        if r.status_code != 200:
            print(f"Errore API: {r.text}")
            return jsonify({"error": "Errore Perplexity"}), 500

        res_text = r.json()['choices'][0]['message']['content']
        print(f"Risposta IA: {res_text}")

        # Regex migliorata per trovare il JSON anche se l'IA aggiunge testo inutile
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        
        if match:
            dati_estratti = json.loads(match.group())
            # Assicuriamoci che tutti i campi esistano nel JSON per non far crashare il JS
            risultato = {
                "targa": dati_estratti.get("targa", ""),
                "autista": dati_estratti.get("autista", ""),
                "km": dati_estratti.get("km", 0),
                "partenza": dati_estratti.get("partenza", "")
            }
            return jsonify(risultato)
        
        return jsonify({"error": "JSON non trovato nella risposta"}), 500

    except Exception as e:
        print(f"Errore generale: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
