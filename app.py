import os, json, io, requests
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "valerio_centrale_blindata_2026_gps"

# CHIAVE PERPLEXITY
PERPLEXITY_API_KEY = "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"
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

@app.route("/process_voice", methods=["POST"])
def process_voice():
    testo_vocale = request.json.get("text")
    # Il prompt ordina all'IA di restituire solo i dati che ci servono
    prompt = f"Analizza la frase: '{testo_vocale}'. Rispondi SOLO in formato JSON con queste chiavi: 'autista' (Valerio, Daniele, Costantino, Simone, Stefano), 'targa' (piccolo->GA087CH, medio->GX942TS, grande->GG862HC), 'partenza', 'km' (solo numero). Esempio: {{\"autista\":\"Valerio\",\"targa\":\"GG862HC\",\"partenza\":\"Tiburtina\",\"km\":1500}}"
    
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [{"role": "system", "content": "Sei un assistente che estrae dati tecnici."}, {"role": "user", "content": prompt}]
    }
    try:
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)
        content = r.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return {"error": "IA non disponibile"}, 500

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
            furgoni[targa].update({
                "dest_intermedia": request.form.get("destinazione"), "km_d": request.form.get("km_destinazione"),
                "step": 2, "data_d": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salva_stato(furgoni)
        elif azione == "stop":
            c = furgoni[targa]
            km_r = request.form.get("km_rientro")
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.drawString(100, 800, f"Report Viaggio {targa}")
            p.drawString(100, 780, f"Autista: {c['autista']}")
            p.save()
            buffer.seek(0)
            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": km_r, "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return send_file(buffer, as_attachment=True, download_name=f"Report_{targa}.pdf")
        elif azione == "annulla":
            if targa in furgoni: furgoni[targa]["step"] = 0; furgoni[targa]["stato"] = "Libero"
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
        return redirect(url_for('index'))
    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

if __name__ == "__main__":
    app.run(debug=True)
