import os, json
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chiave-di-emergenza")

# CONFIGURAZIONI DA RENDER
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
creds_json = os.getenv("GOOGLE_CREDENTIALS")

def scrivi_su_excel(dati):
    try:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        service = build('sheets', 'v4', credentials=creds)
        
        values = [[
            dati.get("data_p"), dati.get("data_a"), dati.get("autista"),
            dati.get("targa"), dati.get("partenza"), dati.get("destinazione"),
            dati.get("km_p"), dati.get("km_a")
        ]]
        
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Foglio1!A:H", # Controlla che il foglio si chiami Foglio1
            valueInputOption="RAW",
            body={'values': values}
        ).execute()
        print("✅ SALVATO SU EXCEL")
    except Exception as e:
        print(f"❌ ERRORE EXCEL: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "data_p": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            c.update({
                "destinazione": request.form.get("destinazione"),
                "km_a": request.form.get("km_arrivo"),
                "data_a": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            scrivi_su_excel(c)
        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
