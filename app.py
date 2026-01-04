import os, json, urllib.parse
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = "valerio_furgoni_2026_wa"

# Configurazione Variabili Render
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
MIO_NUMERO = "393714737368" # Il tuo numero con prefisso 39

@app.route("/", methods=["GET", "POST"])
def index():
    link_wa = None
    
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
            
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            dest = request.form.get("destinazione")
            km_a = request.form.get("km_arrivo")
            data_a = datetime.now().strftime("%d/%m %H:%M")

            # 1. SALVATAGGIO SU GOOGLE EXCEL
            try:
                info = json.loads(CREDS_JSON)
                creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                service = build('sheets', 'v4', credentials=creds)
                values = [[c['data_p'], data_a, c['autista'], c['targa'], c['partenza'], dest, c['km_p'], km_a]]
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                    valueInputOption="RAW", body={'values': values}
                ).execute()
                print("✅ Excel aggiornato")
            except Exception as e:
                print(f"❌ Errore Excel: {e}")

            # 2. PREPARAZIONE MESSAGGIO WHATSAPP
            testo = (f"🚚 *NUOVO RAPPORTO FURGONE*\n\n"
                     f"👤 *Autista:* {c['autista']}\n"
                     f"🔢 *Targa:* {c['targa']}\n"
                     f"📍 *Percorso:* {c['partenza']} ➔ {dest}\n"
                     f"⏱ *Orario:* {c['data_p']} - {data_a}\n"
                     f"🛣 *Chilometri:* {c['km_p']} ➔ {km_a}")
            
            # Codifica per URL
            testo_url = urllib.parse.quote(testo)
            link_wa = f"https://wa.me/{MIO_NUMERO}?text={testo_url}"
            
            # Salviamo il link temporaneamente per mostrarlo nella pagina
            session["ultimo_wa"] = link_wa
            return redirect("/")

    link_wa = session.pop("ultimo_wa", None)
    return render_template("form.html", corsa=session.get("corsa"), link_wa=link_wa)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

