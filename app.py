from flask import Flask, render_template, request, redirect, session
import os, requests, base64, json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "furgoni_final_2026"

# CONFIGURAZIONE API (L'unica che attraversa i blocchi di Render)
BREVO_API_KEY = "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"
MITTENTE = "pvalerio910@gmail.com"
DESTINATARIO = "valerio121291@hotmail.it"

def invia_con_api_brevo(pdf_path, filename):
    """Invia il PDF tramite chiamata HTTP (porta 443), saltando i blocchi SMTP"""
    try:
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": BREVO_API_KEY
        }
        payload = {
            "sender": {"name": "Sistema Furgoni", "email": MITTENTE},
            "to": [{"email": DESTINATARIO}],
            "subject": f"🚚 Rapporto Corsa: {filename}",
            "htmlContent": "<html><body><p>Rapporto in allegato.</p></body></html>",
            "attachment": [{"content": pdf_base64, "name": filename}]
        }

        # Questa è una richiesta web normale, Render NON la blocca
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            print("✅ SUCCESSO: Email inviata tramite API!")
        else:
            print(f"❌ ERRORE API: {response.text}")
    except Exception as e:
        print(f"❌ ERRORE DI CONNESSIONE: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "km_p": request.form.get("km_partenza")
            }
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            km_a = request.form.get("km_arrivo")
            nome_f = f"Rapporto_{c['autista']}_{datetime.now().strftime('%H%M%S')}.pdf"
            path = f"/tmp/{nome_f}"
            
            # Generazione PDF semplice
            doc = SimpleDocTemplate(path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = [Paragraph(f"Autista: {c['autista']}", styles['Heading1']), Spacer(1,12)]
            doc.build(elements)
            
            # Invio via API
            invia_con_api_brevo(path, nome_f)
            
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
