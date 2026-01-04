import os, json, urllib.parse
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = "valerio_furgoni_safe_2026"

# Configurazione Variabili (Prese da Render)
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS")
MIO_NUMERO = "393714737368"  # Il tuo numero già configurato

@app.route("/", methods=["GET", "POST"])
def index():
    link_wa = None
    
    if request.method == "POST":
        azione = request.form.get("azione")
        
        # --- INIZIO CORSA ---
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"),
                "targa": request.form.get("targa"),
                "partenza": request.form.get("partenza"),
                "km_p": request.form.get("km_partenza"),
                "data_p": datetime.now().strftime("%d/%m %H:%M")
            }
            print(f"--- [LOG] Corsa iniziata da {session['corsa']['autista']} ---")
            return redirect("/")
            
        # --- FINE CORSA ---
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa") # Toglie la corsa dalla sessione
            dest = request.form.get("destinazione")
            km_a = request.form.get("km_arrivo")
            data_a = datetime.now().strftime("%d/%m %H:%M")

            # 1. SALVATAGGIO SU GOOGLE SHEETS
            try:
                if CREDS_JSON and SPREADSHEET_ID:
                    info = json.loads(CREDS_JSON)
                    creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
                    service = build('sheets', 'v4', credentials=creds)
                    
                    values = [[
                        c['data_p'], data_a, c['autista'], c['targa'], 
                        c['partenza'], dest, c['km_p'], km_a
                    ]]
                    
                    service.spreadsheets().values().append(
                        spreadsheetId=SPREADSHEET_ID, range="Foglio1!A:H",
                        valueInputOption="RAW", body={'values': values}
                    ).execute()
                    print("✅ Excel aggiornato con successo")
            except Exception as e:
                print(f"❌ Errore Excel: {e}")

            # 2. CREAZIONE LINK WHATSAPP
            testo = (f"🚚 *NUOVO RAPPORTO FURGONE*\n\n"
                     f"👤 *Autista:* {c['autista']}\n"
                     f"🔢 *Targa:* {c['targa']}\n"
                     f"📍 *Percorso:* {c['partenza']} ➔ {dest}\n"
                     f"⏱ *Orario:* {c['data_p']} - {data_a}\n"
                     f"🛣 *Chilometri:* {c['km_p']} ➔ {km_a}")
            
            # Codifica il testo per renderlo un URL valido
            testo_url = urllib.parse.quote(testo)
            link_wa = f"https://wa.me/{MIO_NUMERO}?text={testo_url}"
            
            # 3. MOSTRA IL RISULTATO (Senza fare redirect, così il link_wa resta visibile)
            return render_template("form.html", link_wa=link_wa, corsa_in_corso=False)

    # Caricamento normale della pagina
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    # Avvio dell'app sulla porta corretta per Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

