import os, json, io, requests
from flask import Flask, render_template, request, session, send_file, redirect, url_for, jsonify
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from vercel_kv import kv  # Importa il database KV dal Marketplace

# Librerie per Google Sheets
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = "logistica_csa_valerio_2026_top"

# --- CONFIGURAZIONE IA ---
PPLX_API_KEY = "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"

# --- GESTIONE STATO CON VERCEL KV ---
def carica_stato():
    try:
        # Legge lo stato dal database KV
        stato = kv.get("stato_furgoni")
        if stato:
            return stato
    except Exception as e:
        print(f"Errore lettura KV: {e}")
    
    # Stato iniziale se il database è vuoto o c'è un errore
    return {
        "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
        "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0},
        "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 0, "autista": "-", "step": 0}
    }

def salva_stato(stato):
    try:
        kv.set("stato_furgoni", stato)
    except Exception as e:
        print(f"Errore scrittura KV: {e}")

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
                "targa": targa, "stato": "In Viaggio",
                "posizione": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "autista": request.form.get("autista"),
                "step": 1, "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            session["targa_in_uso"] = targa
            salva_stato(furgoni)
            return redirect(url_for('index'))
            
        elif azione == "arrivo_dest":
            furgoni[targa].update({
                "dest_intermedia": request.form.get("destinazione"),
                "km_d": request.form.get("km_destinazione"),
                "step": 2, "data_d": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salva_stato(furgoni)
            return redirect(url_for('index'))

        elif azione == "stop":
            c = furgoni.get(targa)
            km_r = request.form.get("km_rientro")
            data_r = datetime.now().strftime("%d/%m/%Y %H:%M")

            # INVIO A GOOGLE SHEETS
            try:
                creds_json = os.getenv("GOOGLE_CREDENTIALS")
                spreadsheet_id = os.getenv("SPREADSHEET_ID")
                if creds_json and spreadsheet_id:
                    info = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                    service = build('sheets', 'v4', credentials=creds)
                    nuova_riga = [[c['data_p'], c.get('data_d', '-'), data_r, c['autista'], targa, c['posizione'], c.get('dest_intermedia', '-'), c['km_p'], c.get('km_d', '-'), km_r]]
                    service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range="Foglio1!A:J", valueInputOption="RAW", body={'values': nuova_riga}).execute()
            except Exception as e:
                print(f"Errore Excel: {e}")

            # CREAZIONE PDF
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            p.setFont("Helvetica-Bold", 18)
            p.drawCentredString(300, 800, "LOGISTICA CSA - REPORT VIAGGIO")
            
            y = 720
            def draw_block(titolo, info, km, data, y_pos, color_bg):
                p.setFillColor(color_bg)
                p.rect(50, y_pos-60, 500, 60, fill=1)
                p.setFillColor(colors.black)
                p.setFont("Helvetica-Bold", 11)
                p.drawString(60, y_pos-20, titolo)
                p.setFont("Helvetica", 10)
                p.drawString(60, y_pos-35, f"LUOGO: {info} | ORA: {data}")
                p.drawString(60, y_pos-50, f"KM: {km}")
                return y_pos - 80

            y = draw_block("1. PARTENZA", c['posizione'], c['km_p'], c['data_p'], y, colors.lightgrey)
            y = draw_block("2. ARRIVO DESTINAZIONE", c.get('dest_intermedia','-'), c.get('km_d','-'), c.get('data_d','-'), y, colors.whitesmoke)
            y = draw_block("3. RIENTRO ALLA BASE", "Tiburtina (Sede)", km_r, data_r, y, colors.lightgrey)
            
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, y-40, f"TOTALE KM: {int(km_r) - int(c['km_p'])}")
            p.showPage()
            p.save()
            buffer.seek(0)

            furgoni[targa] = {"stato": "Libero", "posizione": "Sede", "km": km_r, "autista": "-", "step": 0}
            salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return send_file(buffer, as_attachment=True, download_name=f"CSA_{targa}.pdf", mimetype='application/pdf')

        elif azione == "annulla":
            if targa:
                furgoni[targa].update({"stato": "Libero", "step": 0})
                salva_stato(furgoni)
            session.pop("targa_in_uso", None)
            return redirect(url_for('index'))

    return render_template("form.html", furgoni=furgoni, corsa_attiva=corsa_attiva, targa_attiva=targa_attiva)

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        data = request.json
        testo_vocale = data.get("testo", "")
        prompt = f"Analizza: '{testo_vocale}'. Rispondi SOLO in JSON: {{\"targa\": \"GA087CH\" se piccolo, \"GX942TS\" se medio, \"GG862HC\" se grosso, \"autista\": \"Nome\", \"km\": numero, \"luogo\": \"Posto\"}}"
        
        headers = {"Authorization": f"Bearer {PPLX_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [{"role": "system", "content": "Rispondi solo in JSON."}, {"role": "user", "content": prompt}],
            "temperature": 0
        }
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        risposta_ia = r.json()['choices'][0]['message']['content']
        json_pulito = risposta_ia.replace('```json', '').replace('```', '').strip()
        return jsonify(json.loads(json_pulito))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
