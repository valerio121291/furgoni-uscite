import os, json, requests, re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Assicurati di impostare la variabile d'ambiente o scriverla qui per il test locale
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "TUO_TOKEN_QUI")

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        testo = request.json.get("testo", "")
        print(f"Testo ricevuto: {testo}") # Per vedere cosa arriva nel terminale

        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system", 
                    "content": (
                        "Sei un estrattore dati per logistica. Rispondi SOLO in JSON puro. "
                        "Mappe furgoni: 'piccolo'->GA087CH, 'medio'->GX942TS, 'grande' o 'grosso'->GG862HC. "
                        "Usa queste chiavi esatte: targa, autista, km, partenza."
                    )
                },
                {"role": "user", "content": f"Estrai dati da: {testo}"}
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        
        if r.status_code != 200:
            return jsonify({"error": f"Errore API: {r.status_code}"}), 500

        res_text = r.json()['choices'][0]['message']['content']
        print(f"Risposta IA: {res_text}")

        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            d = json.loads(match.group())
            # Forziamo i valori a stringa per evitare problemi con il campo 'number' di HTML
            return jsonify({
                "targa": str(d.get("targa", "")),
                "autista": str(d.get("autista", "")),
                "km": str(d.get("km", "")),
                "partenza": str(d.get("partenza", ""))
            })
        
        return jsonify({"error": "L'IA non ha restituito un JSON valido"}), 500

    except Exception as e:
        print(f"Errore: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
