import os, json, requests, re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configura qui la tua chiave Perplexity
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "IL_TUO_TOKEN_QUI")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        data = request.json
        testo = data.get("testo", "")
        
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        # System prompt ottimizzato per estrarre anche la partenza
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system", 
                    "content": "Sei un estrattore dati per logistica. Rispondi SOLO in JSON puro. "
                               "Mappe furgoni: 'piccolo'->GA087CH, 'medio'->GX942TS, 'grande'->GG862HC. "
                               "Estrai: targa, autista, km (numero), partenza (città o via)."
                },
                {"role": "user", "content": f"Estrai dati da: {testo}. Formato: {{\"targa\":\"...\",\"autista\":\"...\",\"km\":0, \"partenza\":\"...\"}}"}
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        res_text = r.json()['choices'][0]['message']['content']
        
        # Estrazione pulita del JSON tramite Regex
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            return jsonify(json.loads(match.group()))
        
        return jsonify({"error": "Formato non riconosciuto"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
