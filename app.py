
import os, json, urllib.parse
from flask import Flask, render_template, request, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = "valerio_2026_final_fix"

# Dati Render
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
MIO_NUMERO = "393714737368"

@app.route("/", methods=["GET", "POST"])
def index():
    link_wa = None
    corsa_in_corso = "corsa" in session

    if request.method == "POST":
        azione = request.form.get("azione")
        
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "data_p": datetime.now().strftime("%d/%m %H:%M")
            }
            corsa_in_corso = True
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa") # Rimuove la corsa dalla sessione subito
            dest = request.form.get("destinazione")
            km_a = request.form.get("km_arrivo")
            data_a = datetime.now().strftime("%d/%m %H:%M")

            # 1. TENTATIVO SALVATAGGIO EXCEL
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], data_a, c['autista'], c['targa'], c['partenza'], dest, c['km_p'], km_a]]
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                    valueInputOption="RAW", body={'values': values}
                ).execute()
            except Exception as e:
                print(f"Errore Excel (ignorato per mostrare WA): {e}")

            # 2. CREAZIONE MESSAGGIO WHATSAPP
            testo = (f"🚚 *RAPPORTO FURGONE*\n\n"
                     f"👤 *Autista:* {c['autista']}\n"
                     f"🔢 *Targa:* {c['targa']}\n"
                     f"📍 *Percorso:* {c['partenza']} ➔ {dest}\n"
                     f"🛣 *KM:* {c['km_p']} ➔ {km_a}")
            
            testo_url = urllib.parse.quote(testo)
            link_wa = f"https://wa.me/{MIO_NUMERO}?text={testo_url}"
            corsa_in_corso = False

    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=corsa_in_corso, link_wa=link_wa)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
