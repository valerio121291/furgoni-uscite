
import os, json, io, smtplib
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "chiave_valerio_2026_finale"

# Variabili Ambiente da Render
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "km_p": request.form.get("km_partenza"),
                "data_p": datetime.now().strftime("%d/%m %H:%M")
            }
            print(f"--- [LOG] Corsa Iniziata per {session['corsa']['autista']} ---")
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            c.update({
                "destinazione": request.form.get("destinazione"),
                "km_a": request.form.get("km_arrivo"),
                "data_a": datetime.now().strftime("%d/%m %H:%M")
            })

            # 1. CREAZIONE PDF SEMPLICE
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer)
            p.drawString(100, 800, "RIEPILOGO CORSA FURGONE")
            p.drawString(100, 780, f"Autista: {c['autista']}")
            p.drawString(100, 760, f"Targa: {c['targa']}")
            p.drawString(100, 740, f"Percorso: {c['km_p']} km -> {c['km_a']} km")
            p.drawString(100, 720, f"Orario: {c['data_p']} -> {c['data_a']}")
            p.save()
            pdf_data = buffer.getvalue()

            # 2. INVIO EMAIL CON PORTA 465 (SSL)
            print(f"--- [LOG] Tentativo Invio Email con Password App a {GMAIL_USER} ---")
            
            msg = EmailMessage()
            msg.set_content(f"Rapporto corsa furgone.\nAutista: {c['autista']}\nTarga: {c['targa']}")
            msg['Subject'] = f"Rapporto {c['autista']} - {c['targa']}"
            msg['From'] = GMAIL_USER
            msg['To'] = GMAIL_USER
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename="rapporto.pdf")

            try:
                # Connessione SSL diretta (Porta 465 è obbligatoria per password app GMX)
                with smtplib.SMTP_SSL("mail.gmx.com", 465, timeout=20) as server:
                    server.login(GMAIL_USER, GMAIL_PASS)
                    server.send_message(msg)
                print("✅ ✅ ✅ EMAIL INVIATA CON SUCCESSO!")
            except Exception as e:
                print(f"❌ ERRORE EMAIL: {str(e)}")

            # 3. SCRITTURA EXCEL (Opzionale, dopo l'email)
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], c['data_a'], c['autista'], c['targa'], "N/D", c['destinazione'], c['km_p'], c['km_a']]]
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                    valueInputOption="RAW", body={'values': values}
                ).execute()
                print("✅ Excel Aggiornato")
            except Exception as e:
                print(f"❌ Errore Excel: {e}")

        return redirect("/")
    
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
