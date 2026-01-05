import os, json, requests, re, smtplib
from flask import Flask, render_template, request, jsonify
from fpdf import FPDF
from email.message import EmailMessage

app = Flask(__name__)

# --- CONFIGURAZIONE ---
# Assicurati di impostare PPLX_API_KEY su Vercel (Settings > Environment Variables)
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "TUO_TOKEN_PERPLEXITY")

# Credenziali Email (Password App corretta senza spazi)
EMAIL_MITTENTE = "pvalerio910@gmail.com"
EMAIL_PASSWORD = "ogteueppdqmtpcvg"  # Password corretta senza spazi
EMAIL_DESTINATARIO = "pvalerio910@gmail.com"

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/elabora_voce", methods=["POST"])
def elabora_voce():
    try:
        testo = request.json.get("testo", "")
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system", 
                    "content": "Sei un estrattore dati logistici. Rispondi SOLO in JSON puro. Mappe furgoni: piccolo->GA087CH, medio->GX942TS, grande->GG862HC. Chiavi obbligatorie: targa, autista, km, partenza."
                },
                {"role": "user", "content": f"Estrai dati da: {testo}"}
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=15)
        res_data = r.json()
        res_text = res_data['choices'][0]['message']['content']
        
        # Estrazione sicura del blocco JSON
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            return jsonify(json.loads(match.group()))
        
        return jsonify({"error": "No JSON found"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/genera_e_invia", methods=["POST"])
def genera_e_invia():
    try:
        d = request.json
        # Percorso temporaneo obbligatorio per Vercel
        pdf_path = "/tmp/Riepilogo_Viaggio.pdf"
        
        # 1. CREAZIONE PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="RAPPORTO PARTENZA MEZZO", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Data/Ora: {d.get('data_ora', 'N/D')}", ln=True)
        pdf.ln(5)
        pdf.cell(200, 10, txt=f"Conducente: {d.get('autista', 'N/D')}", ln=True)
        pdf.cell(200, 10, txt=f"Targa Veicolo: {d.get('targa', 'N/D')}", ln=True)
        pdf.cell(200, 10, txt=f"Chilometri: {d.get('km', '0')}", ln=True)
        pdf.cell(200, 10, txt=f"Localita Partenza: {d.get('partenza', 'Tiburtina')}", ln=True)
        
        # Salvataggio nel file system temporaneo
        pdf.output(pdf_path)

        # 2. INVIO EMAIL
        msg = EmailMessage()
        msg['Subject'] = f"Report Viaggio: {d.get('autista')} - {d.get('targa')}"
        msg['From'] = EMAIL_MITTENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg.set_content(f"In allegato trovi il riepilogo del viaggio per il mezzo {d.get('targa')}.")

        # Lettura del file da /tmp/
        with open(pdf_path, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(
                file_data, 
                maintype='application', 
                subtype='pdf', 
                filename="Report_Viaggio.pdf"
            )

        # Invio tramite SMTP Gmail
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_MITTENTE, EMAIL_PASSWORD)
            smtp.send_message(msg)

        return jsonify({"status": "success", "message": "PDF inviato con successo!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
