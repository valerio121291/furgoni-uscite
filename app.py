from flask import Flask, render_template, request, redirect, session
import os
import json
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "furgoni-valerio-secret-2026")

# CONFIGURAZIONI (Assicurati che queste variabili siano su Render)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1S_87-B9Y2hXN-f3p0XyO6fI87oT6pYmYV7N5vB8k") # Il tuo ID foglio
RANGE_NAME = "Foglio1!A:H"

def ottieni_service_sheets():
    """Connessione alle API di Google Sheets"""
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        return None
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict, 
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=creds)

def scrivi_su_excel(dati_corsa):
    """Aggiunge una riga al foglio Google Sheets"""
    try:
        service = ottieni_service_sheets()
        if not service:
            print("Errore: Credenziali Google mancanti")
            return

        values = [[
            dati_corsa.get("data_p"),
            dati_corsa.get("data_a"),
            dati_corsa.get("autista"),
            dati_corsa.get("targa"),
            dati_corsa.get("partenza"),
            dati_corsa.get("destinazione"),
            dati_corsa.get("km_p"),
            dati_corsa.get("km_a")
        ]]
        
        body = {'values': values}
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption="RAW",
            body=body
        ).execute()
        print("✅ Dati salvati su Excel!")
    except Exception as e:
        print(f"❌ Errore Sheets: {e}")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        
        if azione == "start":
            # Salva i dati di inizio in sessione
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "data_p": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        elif azione == "stop" and "corsa" in session:
            # Recupera dati inizio e aggiungi dati fine
            corsa = session.pop("corsa")
            corsa.update({
                "destinazione": request.form.get("destinazione"),
                "km_a": request.form.get("km_arrivo"),
                "data_a": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Scrittura finale su Google Drive
            scrivi_su_excel(corsa)
            
        return redirect("/")
    
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
