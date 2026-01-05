import os, json, requests, re, smtplib
from flask import Flask, render_template, request, jsonify
from fpdf import FPDF
from email.message import EmailMessage

app = Flask(__name__)

# --- CONFIGURAZIONE ---
PPLX_API_KEY = os.getenv("PPLX_API_KEY", "TUO_TOKEN_PERPLEXITY")
EMAIL_MITTENTE = "pvalerio910@gmail.com"
EMAIL_PASSWORD = "ogteueppdqmtpcvg" # Password App senza spazi
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
                {"role": "system", "content": "Estrai dati logistica in JSON: targa, autista, km. Mappa: piccolo->GA087CH, medio->GX942TS, grande->GG862HC."},
                {"role": "user", "content": testo}
            ],
            "temperature": 0
        }
        r = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=payload, timeout=10)
        res_text = r.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        return jsonify(json.loads(match.group())) if match else jsonify({"error": "No JSON"}), 200
    except:
        return jsonify({"status": "IA offline, uso dati locali"}), 200

@app.route("/genera_e_invia", methods=["POST"])
def genera_e_invia():
    try:
        d = request.json
        pdf_path = "/tmp/Riepilogo_Viaggio.pdf" # Percorso obbligatorio per Vercel
        
        # 1. Creazione PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORT PARTENZA LOGISTICA", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, f"Data/Ora: {d.get('data_ora')}", ln=True)
        pdf.cell(200, 10, f"Autista: {d.get('autista')}", ln=True)
        pdf.cell(200, 10, f"Targa: {d.get('targa')}", ln=True)
        pdf.cell(200, 10, f"KM: {d.get('km')}", ln=True)
        pdf.cell(200, 10, f"Partenza: {d.get('partenza')}", ln=True)
        pdf.output(pdf_path)

        # 2. Invio Email
        msg = EmailMessage()
        msg['Subject'] = f"Report Viaggio: {d.get('autista')} - {d.get('targa')}"
        msg['From'] = EMAIL_MITTENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg.set_content(f"In allegato il report del viaggio.\nAutista: {d.get('autista')}\nKM: {d.get('km')}")

        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename="Report_Viaggio.pdf")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_MITTENTE, EMAIL_PASSWORD)
            smtp.send_message(msg)

        return jsonify({"status": "success", "message": "Email inviata con successo!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
