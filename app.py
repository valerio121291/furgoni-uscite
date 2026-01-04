from flask import Flask, render_template, request, redirect, session, send_file
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "segreto_valerio_furgoni_2024" # Necessario per la memoria della sessione

# Database temporaneo per lo stato dei furgoni (in produzione si userebbe un DB reale)
stato_furgoni = {
    "GA087CH": {"stato": "Libero", "posizione": "Sede", "km": 100000},
    "GX942TS": {"stato": "Libero", "posizione": "Sede", "km": 120000},
    "GG862HC": {"stato": "Libero", "posizione": "Sede", "km": 150000},
}

@app.route("/", methods=["GET", "POST"])
def index():
    # 1. Recupera se c'è una corsa attiva nella sessione dell'utente
    corsa_attiva = None
    targa_in_uso = None
    for key in session:
        if key.startswith("corsa_"):
            targa_in_uso = key.split("_")[1]
            corsa_attiva = session[key]
            break

    if request.method == "POST":
        azione = request.form.get("azione")
        targa = request.form.get("targa")

        # --- AZIONE: ANNULLA (Reset manuale) ---
        if azione == "annulla":
            session.pop(f"corsa_{targa}", None)
            if targa in stato_furgoni:
                stato_furgoni[targa]["stato"] = "Libero"
            return redirect("/")

        # --- AZIONE: INIZIO GIRO (Step 1) ---
        if azione == "start":
            autista = request.form.get("autista")
            partenza = request.form.get("partenza")
            km_p = request.form.get("km_partenza")
            
            # Salviamo i dati nella sessione (L'app ora "sa" che furgone usi)
            session[f"corsa_{targa}"] = {
                "targa": targa,
                "autista": autista,
                "punto_partenza": partenza,
                "km_partenza": km_p,
                "ora_partenza": datetime.now().strftime("%H:%M"),
                "step": 1 # Siamo in viaggio verso la destinazione
            }
            stato_furgoni[targa]["stato"] = "In Viaggio"
            stato_furgoni[targa]["posizione"] = f"Da {partenza}"
            return redirect("/")

        # --- AZIONE: ARRIVO A DESTINAZIONE (Step 2) ---
        elif azione == "arrivo_dest":
            destinazione = request.form.get("destinazione")
            km_d = request.form.get("km_destinazione")
            
            if f"corsa_{targa}" in session:
                session[f"corsa_{targa}"]["destinazione"] = destinazione
                session[f"corsa_{targa}"]["km_destinazione"] = km_d
                session[f"corsa_{targa}"]["ora_destinazione"] = datetime.now().strftime("%H:%M")
                session[f"corsa_{targa}"]["step"] = 2 # Arrivato, ora deve solo rientrare
                
                stato_furgoni[targa]["posizione"] = destinazione
                stato_furgoni[targa]["km"] = km_d
                session.modified = True
            return redirect("/")

        # --- AZIONE: RIENTRO E CHIUSURA (Step 3) ---
        elif azione == "stop":
            km_r = request.form.get("km_rientro")
            
            if f"corsa_{targa}" in session:
                dati_finali = session[f"corsa_{targa}"]
                # Qui potresti generare il PDF con i dati completi
                print(f"GIRO CONCLUSO: {dati_finali['autista']} su {targa}")
                print(f"KM Totali: {int(km_r) - int(dati_finali['km_partenza'])}")
                
                # Reset stato e sessione
                stato_furgoni[targa]["stato"] = "Libero"
                stato_furgoni[targa]["posizione"] = "Sede"
                stato_furgoni[targa]["km"] = km_r
                session.pop(f"corsa_{targa}")
                
                # Messaggio di conferma (opzionale)
                return "<h1>Giro Concluso! PDF Generato (Simulazione).</h1><a href='/'>Torna alla Home</a>"

    return render_template("form.html", furgoni=stato_furgoni, corsa_attiva=corsa_attiva)

if __name__ == "__main__":
    # Crea la cartella templates se non esiste
    if not os.path.exists("templates"):
        os.makedirs("templates")
    app.run(debug=True, port=5000)
