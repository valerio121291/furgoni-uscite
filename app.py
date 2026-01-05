import os, json, requests, re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

PPLX_API_KEY = os.getenv("PPLX_API_KEY", "IL_TUO_TOKEN_QUI")

@app.route("/")
def index():
    furgoni_test = {
        "GA087CH": {"stato": "Libero"},
        "GX942TS": {"stato": "Libero"},
        "GG862HC": {"stato": "Libero"}
    }
    return render_template("form.html", furgoni=furgoni_test)

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        testo = request.json.get("testo", "")
        headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "Estrattore dati logistica. Rispondi SOLO JSON puro. Mappe: piccolo->GA087CH, medio->GX942TS, grande->GG862HC."},
                {"role": "user", "content": f"Estrai in JSON {{'targa','autista','km','partenza'}} da: {testo}"}
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        res_text = r.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        
        if match:
            dati = json.loads(match.group())
            # Normalizziamo le chiavi per il frontend
            return jsonify({
                "targa": dati.get("targa", ""),
                "autista": dati.get("autista", ""),
                "km": dati.get("km", ""),
                "partenza": dati.get("partenza", "")
            })
        return jsonify({"error": "no_json"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
