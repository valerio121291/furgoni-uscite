import os, json, requests, re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

PPLX_API_KEY = os.getenv("PPLX_API_KEY", "TUO_TOKEN_QUI")

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        testo = request.json.get("testo", "")
        headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "Estrattore dati logistica. Mappe: piccolo->GA087CH, medio->GX942TS, grande->GG862HC. Rispondi SOLO JSON puro con chiavi: targa, autista, km, partenza."},
                {"role": "user", "content": f"Estrai dati da: {testo}"}
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        res_text = r.json()['choices'][0]['message']['content']
        
        # Estrazione sicura del JSON
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            d = json.loads(match.group())
            # Forziamo i nomi delle chiavi per il frontend
            return jsonify({
                "targa": d.get("targa", ""),
                "autista": d.get("autista", ""),
                "km": d.get("km", ""),
                "partenza": d.get("partenza", "")
            })
        return jsonify({"error": "no_json"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
