import os, json, requests, re, smtplib
from flask import Flask, render_template, request, jsonify
from fpdf import FPDF
from email.message import EmailMessage

app = Flask(__name__)

# --- CONFIGURAZIONE PERPLEXITY ---
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "TUO_TOKEN_PERPLEXITY")

# --- CONFIGURAZIONE EMAIL ---
EMAIL_MITTENTE = "pvalerio910@gmail.com"
EMAIL_PASSWORD = "ogte uepp dqmt pcvg" # La tua password app
EMAIL_DESTINATARIO = "pvalerio910@gmail.com"

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
                {
                    "role": "system", 
                    "content": "Estrattore dati logistica. Mappe: piccolo->GA087CH, medio->GX942TS, grande->GG862HC. Rispondi SOLO JSON con chiavi: targa, autista, km, partenza."
                },
                {"role": "user", "content": f"Estrai dati da: {testo}"}
            ],
            "temperature": 0
        }
        
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        res_text = r.json()['choices'][0]['message']['content']
        
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            return jsonify(json.loads(match.group()))
        return jsonify({"error": "no_json"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/genera_e_invia", methods=["POST"])
def genera_e_invia():
    try:
        dati = request.json
        pdf_name = "Riepilogo_Viaggio.pdf"
        
        # 1. CREAZIONE PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="RAPPORTO PARTENZA MEZZO", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Data Invio: {dati.get('data_ora')}", ln=True)
        pdf.cell(200, 10, txt=f"Autista: {dati.get('autista')}", ln=True)
        pdf.cell(200, 10, txt=f"Targa Furgone: {dati.get('targa')}", ln=True)
        pdf.cell(200, 10, txt=f"Chilometri: {dati.get('km')}", ln=True)
        pdf.cell(200, 10, txt=f"Partenza: {dati.get('partenza')}", ln=True)
        
        pdf.output(pdf_name)

        # 2. INVIO EMAIL
        msg = EmailMessage()
        msg['Subject'] = f"Report Viaggio: {dati.get('autista')} ({dati.get('targa')})"
        msg['From'] = EMAIL_MITTENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg.set_content(f"Ciao Valerio, in allegato trovi il riepilogo del viaggio generato vocalmente.")

        with open(pdf_name, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=pdf_name)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_MITTENTE, EMAIL_PASSWORD)
            smtp.send_message(msg)

        return jsonify({"status": "success", "message": "Email e PDF inviati a te stesso!"})

    except Exception as e:
        print(f"Errore: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
