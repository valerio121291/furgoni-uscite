from flask import Flask, render_template, request, redirect, session
import os, requests, base64, json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "furgoni_valerio_2026_brevo"

# CONFIGURAZIONE DIRETTA
BREVO_API_KEY = "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"
MITTENTE = "pvalerio910@gmail.com"
DESTINATARIO = "valerio121291@hotmail.it"

def invia_con_brevo(pdf_path, filename):
    """Invia il PDF usando le API HTTP di Brevo (Sicuro al 100%)"""
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
            "htmlContent": f"<html><body><h2>Rapporto del {datetime.now().strftime('%d/%m/%Y')}</h2><p>In allegato trovi il file PDF con i dettagli della corsa.</p></body></html>",
            "attachment": [{"content": pdf_base64, "name": filename}]
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 201:
            print("✅ EMAIL INVIATA CON SUCCESSO!")
        else:
            print(f"❌ ERRORE BREVO: {response.text}")
            
    except Exception as e:
        print(f"❌ ERRORE TECNICO: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "km_partenza": request.form.get("km_partenza"),
                "ora_inizio": datetime.now().strftime("%H:%M")
            }
        
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            km_fine = request.form.get("km_arrivo")
            filename = f"Rapporto_{c['autista']}_{datetime.now().strftime('%H%M%S')}.pdf"
            path = f"/tmp/{filename}"
            
            # Generazione PDF Professionale
            doc = SimpleDocTemplate(path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Calcolo KM
            try:
                tot_km = int(km_fine) - int(c['km_partenza'])
            except:
                tot_km = "N/D"

            data_tabella = [
                ["CAMPO", "VALORE"],
                ["Autista", c['autista']],
                ["Targa", c['targa']],
                ["KM Partenza", c['km_partenza']],
                ["KM Arrivo", km_fine],
                ["KM Totali", str(tot_km)],
                ["Ora Fine", datetime.now().strftime("%H:%M")]
            ]
            
            tabella = Table(data_tabella, colWidths=[100, 250])
            tabella.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.blue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('PADDING', (0,0), (-1,-1), 6)
            ]))

            elements = [
                Paragraph(f"RAPPORTO USCITA - {c['autista']}", styles['Heading1']),
                Spacer(1, 12),
                tabella
            ]
            doc.build(elements)
            
            # Invio Email
            invia_con_brevo(path, filename)
            
        return redirect("/")
    
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
