from flask import Flask, render_template, request, send_file, jsonify, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from datetime import datetime
from google.oauth2 import service_account
import gspread
import os
import io
from pathlib import Path

app = Flask(__name__)

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Load credentials from environment variable
credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
if credentials_json:
    import json
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(credentials_json),
        scopes=SCOPES
    )
    gc = gspread.authorize(credentials)
    sheet = gc.open('Uscite Furgoni').sheet1
else:
    sheet = None

# Create uploads directory for storing PDFs
UPLOAD_FOLDER = Path('/tmp/pdf_uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)

def create_pdf(driver_name, departure_city, km, arrival_city, arrival_address):
    """Generate PDF and save locally"""
    try:
        # Create PDF in memory first
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"<b>Uscita Furgone - {driver_name}</b>", styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Data table
        data = [
            ['Conducente', driver_name],
            ['Partenza da', departure_city],
            ['Km', str(km)],
            ['Arrivo', arrival_city],
            ['Indirizzo Arrivo', arrival_address],
            ['Data', datetime.now().strftime("%d/%m/%Y %H:%M")]
        ]
        
        table = Table(data, colWidths=[200, 300])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        # Save to file locally
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pdf_filename = f"{driver_name}_{timestamp}.pdf"
        pdf_path = UPLOAD_FOLDER / pdf_filename
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        print(f"✅ PDF salvato localmente: {pdf_path}")
        return str(pdf_path), pdf_filename
        
    except Exception as e:
        print(f"❌ Errore nella creazione del PDF: {e}")
        return None, None

def save_to_sheets(driver_name, departure_city, km, arrival_city, arrival_address):
    """Save data to Google Sheets"""
    if not sheet:
        print("⚠️  Google Sheets non configurato")
        return
    
    try:
        row = [
            driver_name,
            departure_city,
            km,
            arrival_city,
            arrival_address,
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ]
        sheet.append_row(row)
        print(f"✅ Dati salvati su Google Sheets")
    except Exception as e:
        print(f"❌ Errore caricamento su Google Sheets: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.form
        driver_name = data.get('driver_name')
        departure_city = data.get('departure_city')
        km = data.get('km')
        arrival_city = data.get('arrival_city')
        arrival_address = data.get('arrival_address')
        
        # Create PDF
        pdf_path, pdf_filename = create_pdf(driver_name, departure_city, km, arrival_city, arrival_address)
        
        # Save to Google Sheets
        save_to_sheets(driver_name, departure_city, km, arrival_city, arrival_address)
        
        if pdf_path:
            # Return success with download link
            return jsonify({
                'success': True,
                'message': 'PDF generato con successo!',
                'pdf_url': url_for('download_pdf', filename=pdf_filename)
            })
        else:
            return jsonify({'success': False, 'message': 'Errore nella generazione del PDF'})
            
    except Exception as e:
        print(f"❌ Errore: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download/<filename>')
def download_pdf(filename):
    """Download PDF file"""
    try:
        pdf_path = UPLOAD_FOLDER / filename
        if pdf_path.exists():
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            return jsonify({'error': 'File non trovato'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
