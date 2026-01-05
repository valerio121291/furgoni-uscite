import os, json, requests, re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# CONFIGURAZIONE: Sostituisci qui la tua chiave Perplexity
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "TUO_TOKEN_PERPLEXITY_QUI")

@app.route("/")
def index():
    # Definiamo uno stato fittizio per far caricare il form.html originale senza errori
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
        print(f"Testo ricevuto: {testo}")

        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system", 
                    "content": "Sei un estrattore dati. Rispondi SOLO in JSON puro. Mappe furgoni: 'piccolo'->GA087CH, 'medio'->GX942TS, 'grande'->GG862HC."
                },
                {
                    "role": "user", 
                    "content": f"Estrai targa, autista, km (numero), partenza da: {testo}. Formato: {{\"targa\":\"...\",\"autista\":\"...\",\"km\":0, \"partenza\":\"...\"}}"
                }
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        
        if r.status_code != 200:
            print(f"Errore Perplexity: {r.text}")
            return jsonify({"error": "Errore API Perplexity"}), 500

        res_text = r.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        
        if match:
            return jsonify(json.loads(match.group()))
        
        return jsonify({"error": "Dati non trovati"}), 500

    except Exception as e:
        print(f"Errore: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
