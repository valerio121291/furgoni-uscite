import os, json, io, requests
from flask import Flask, render_template, request, session, send_file, redirect, url_for
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# Librerie per Google Sheets
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = "valerio_centrale_blindata_2026_gps"

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
    with open(DB_FILE, "r") as f: 
        return json.load(f)

def salva_stato(stato):
    with open(DB_FILE, "w") as f: 
        json.dump(stato, f)

@app.route("/process_voice", methods=["POST"])
def process_voice():
    testo_vocale = request.json.get("text")
    
    prompt = f"""
    Analizza questa frase: "{testo_vocale}".
    Estrai i dati e rispondi SOLO con un oggetto JSON:
    - "autista": (Valerio, Daniele, Costantino, Simone o Stefano)
    - "targa": (se dice piccolo->GA087CH, medio->GX942TS, grande->GG862HC)
    - "partenza": (il luogo indicato)
    - "km": (solo il numero dei chilometri)
    
    Esempio output: {{"autista": "Valerio", "targa": "GG862HC", "partenza": "Tiburtina", "km": 12000}}
    """
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [{"role": "system", "content": "Sei un estrattore di dati preciso."}, 
                     {"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload)
        content = response.json()['choices'][0]['message']['content']
        # Pulizia da eventuali backticks Markdown
        clean_json = content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        return {"error": str(e)}, 500

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
                "targa": targa,
                "stato": "In Viaggio",
                "posizione": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "autista": request.form.get("autista"),
                "step": 1,
                "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        elif azione == "arrivo_dest":
            furgoni[targa].update({
                "dest_intermedia": request.form.get("destinazione"),
                "km_d": request.form.get("km_destinazione"),
                "step": 2,
                "data_d": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salva_stato(furgoni)
            return redirect(url_for('index'))

        elif azione == "stop":
            c = furgoni.get(targa)
            km_r = request.form.get("km_rientro")
            data_r = datetime.now().strftime("%d/%m/%Y %H:%M")

            # Integrazione Google Sheets (opzionale se configurato)
            try:
                creds_json = os.getenv("GOOGLE_CREDENTIALS")
                spreadsheet_id = os.getenv("SPREADSHEET_ID")
                if creds_json and spreadsheet_id:
                    info = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                    service = build('sheets', 'v4', credentials=creds)
                    nuova_riga = [[c['data_p'], c.get('data_d', '-'), data_r, c['autista'], targa, c['posizione'], c.get('dest_intermedia', '-'), c['km_p'], c.get('km_d', '-'), km_r]]
                    service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range="Foglio1!A:J", valueInputOption="RAW", body={'values': nuova_riga}).execute()
            except: pass

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setTitle(f"Report_{targa}")
            p.setFont("Helvetica-Bold", 18)
            p.drawCentredString(300, 800, "DIARIO DI BORDO - REPORT VIAGGIO")
            
            y = 720
            def draw_block(titolo, info, km, data, y_pos, color_bg):
                p.setFillColor(color_bg)
                p.rect(50, y_pos-60, 500, 60, fill=1)
                p.setFillColor(colors.black)
                p.setFont("Helvetica-Bold", 12)
                p.drawString(60, y_pos-20, titolo)
                p.setFont("Helvetica", 10)
                p.drawString(60, y_pos-35, f"LUOGO: {info} | DATA/ORA: {data}")
                p.drawString(60, y_pos-50, f"CHILOMETRI: {km}")
                return y_pos - 80

            y = draw_block("1. PARTENZA", c['posizione'], c['km_p'], c['data_p'], y, colors.lightgrey)
            y = draw_block("2. ARRIVO DESTINAZIONE", c.get('dest_intermedia','-'), c.get('km_d','-'), c.get('data_d','-'), y, colors.whitesmoke)
            y = draw_block("3. RIENTRO ALLA BASE", "Tiburtina (Sede)", km_r, data_r, y, colors.lightgrey)
            
            tot_km = int(km_r) - int(c['km_p'])
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, y-40, f"TOTALE CHILOMETRI PERCORSI: {tot_km} KM")
            p.showPage()
            p.save()
            buffer.seek(0)

            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": km_r, "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return send_file(buffer, as_attachment=True, download_name=f"Viaggio_{targa}.pdf", mimetype='application/pdf')

        elif azione == "annulla":
            if targa:
                furgoni[targa]["stato"] = "Libero"
                furgoni[targa]["step"] = 0
                salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
