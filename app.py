from flask import Flask, render_template, request, redirect, session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import csv
import os
from datetime import datetime


app = Flask(__name__)
FILE_LOG = "uscite_furgoni.csv"
FURGONI_FOLDER = "furgoni"  # cartella principale

app.secret_key = "super-segreto-furgoni-123"


def genera_pdf(corsa_data):
    """Genera un PDF non modificabile della corsa"""
    
    autista = corsa_data["autista"]
    cartella_autista = os.path.join(FURGONI_FOLDER, autista)
    
    # Crea la cartella dell'autista se non esiste
    os.makedirs(cartella_autista, exist_ok=True)
    
    # Nome file: data_ora_inizio_autista.pdf
    timestamp = corsa_data["data_ora_partenza"].replace(" ", "_").replace(":", "-")
    pdf_filename = f"{timestamp}_{autista}.pdf"
    pdf_path = os.path.join(cartella_autista, pdf_filename)
    
    # Crea il documento PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titolo
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=1  # Centro
    )
    elements.append(Paragraph("Rapporto Corsa Furgone", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Dati della corsa in tabella
    data = [
        ["Campo", "Valore"],
        ["Data/Ora Partenza", corsa_data["data_ora_partenza"]],
        ["Data/Ora Arrivo", corsa_data["data_ora_arrivo"]],
        ["Autista", corsa_data["autista"]],
        ["Targa Furgone", corsa_data["targa"]],
        ["Luogo Partenza", corsa_data["partenza"]],
        ["Destinazione", corsa_data["destinazione"]],
        ["KM Partenza", corsa_data["km_partenza"]],
        ["KM Arrivo", corsa_data["km_arrivo"]],
        ["KM Percorsi", str(int(corsa_data["km_arrivo"]) - int(corsa_data["km_partenza"]))],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer con timestamp di generazione
    footer_text = f"Documento generato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=2  # Destra
    )
    elements.append(Paragraph(footer_text, footer_style))
    
    # Costruisci il PDF (read-only per impostazione)
    doc.build(elements)
    
    print(f"✅ PDF generato: {pdf_path}")
    return pdf_path


@app.route("/", methods=["GET", "POST"])
def registra_uscita():
    corsa_in_corso = "corsa" in session

    if request.method == "POST":
        azione = request.form.get("azione")

        if azione == "start":
            autista = request.form.get("autista", "").strip()
            targa = request.form.get("targa", "").strip()
            partenza = request.form.get("partenza", "").strip()
            km_partenza = request.form.get("km_partenza", "").strip()

            data_ora_partenza = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            session["corsa"] = {
                "data_ora_partenza": data_ora_partenza,
                "autista": autista,
                "targa": targa,
                "partenza": partenza,
                "km_partenza": km_partenza,
            }

            return redirect("/")

        elif azione == "stop" and corsa_in_corso:
            destinazione = request.form.get("destinazione", "").strip()
            km_arrivo = request.form.get("km_arrivo", "").strip()
            data_ora_arrivo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            corsa = session["corsa"]

            # Crea il dizionario completo della corsa
            corsa_completa = {
                "data_ora_partenza": corsa["data_ora_partenza"],
                "data_ora_arrivo": data_ora_arrivo,
                "autista": corsa["autista"],
                "targa": corsa["targa"],
                "partenza": corsa["partenza"],
                "destinazione": destinazione,
                "km_partenza": corsa["km_partenza"],
                "km_arrivo": km_arrivo,
            }

            # 1. Salva su CSV
            with open(FILE_LOG, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    corsa_completa["data_ora_partenza"],
                    corsa_completa["data_ora_arrivo"],
                    corsa_completa["autista"],
                    corsa_completa["targa"],
                    corsa_completa["partenza"],
                    corsa_completa["destinazione"],
                    corsa_completa["km_partenza"],
                    corsa_completa["km_arrivo"],
                ])

            # 2. Genera PDF
            genera_pdf(corsa_completa)

            # Pulisci la sessione
            session.pop("corsa", None)

            return redirect("/")

    corsa = session.get("corsa")

    return render_template(
        "form.html",
        corsa=corsa,
        corsa_in_corso=bool(corsa),
    )


if __name__ == "__main__":
    print("Avvio Flask su http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
