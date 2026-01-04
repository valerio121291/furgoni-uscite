
import os, json, io, smtplib
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "chiave_valerio_2026"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        azione = request.form.get("azione")
        if azione == "start":
            session["corsa"] = {
                "autista": request.form.get("autista"), "targa": request.form.get("targa"),
                "km_p": request.form.get("km_partenza"), "data_p": datetime.now().strftime("%H:%M")
            }
        elif azione == "stop" and "corsa" in session:
            c = session.pop("corsa")
            # 1. Crea un PDF semplicissimo
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer)
            p.drawString(100, 750, f"Rapporto {c['autista']} - {c['targa']}")
            p.showPage()
            p.save()
            pdf_data = buffer.getvalue()
            
            # 2. Invio Email FORZATO (senza thread)
            user = os.getenv("GMAIL_USER")
            pw = os.getenv("GMAIL_PASS")
            print(f"--- TENTATIVO EMAIL PER {user} ---")
            
            from email.message import EmailMessage
            msg = EmailMessage()
            msg.set_content(f"Rapporto furgone per {c['autista']}")
            msg['Subject'] = f"Rapporto {c['autista']}"
            msg['From'] = user
            msg['To'] = user
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename="rapporto.pdf")

            try:
                # Proviamo la porta 587 con timeout lungo
                with smtplib.SMTP("mail.gmx.com", 587, timeout=30) as server:
                    server.starttls()
                    server.login(user, pw)
                    server.send_message(msg)
                print("✅ EMAIL SPEDITA!")
            except Exception as e:
                print(f"❌ ERRORE: {str(e)}")

        return redirect("/")
    return render_template("form.html", corsa=session.get("corsa"), corsa_in_corso=("corsa" in session))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
