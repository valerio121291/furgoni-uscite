<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>Logistica CSA - Dashboard</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --bg-dark: #0f172a; --card-dark: #1e293b; --accent: #38bdf8; --success: #22c55e; --warning: #f59e0b; --danger: #ef4444; --text-main: #f8fafc; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg-dark); margin: 0; padding-bottom: 50px; color: var(--text-main); }
        .header { background: #000; color: var(--accent); padding: 25px; text-align: center; font-weight: 800; border-bottom: 2px solid var(--accent); text-transform: uppercase; letter-spacing: 2px; }
        
        /* Dashboard Targhe */
        .status-container { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding: 15px; }
        .truck-card { background: var(--card-dark); padding: 15px 5px; border-radius: 15px; text-align: center; border: 1px solid #334155; position: relative; }
        .truck-card.In.Viaggio { border: 2px solid var(--warning); box-shadow: 0 0 10px rgba(245, 158, 11, 0.3); }
        .truck-card.Libero { border: 2px solid var(--success); opacity: 0.9; }
        
        /* Tanica Gasolio */
        .fuel-indicator { margin-top: 8px; font-size: 1.3rem; }
        .fuel-text { font-size: 0.6rem; text-transform: uppercase; display: block; margin-top: 2px; font-weight: bold; }
        .btn-refuel { background: rgba(34, 197, 94, 0.1); border: 1px solid var(--success); color: var(--success); padding: 6px; border-radius: 8px; font-size: 0.6rem; margin-top: 10px; cursor: pointer; width: 90%; font-weight: 800; }

        /* Form e Input */
        .main-container { padding: 0 15px; }
        .card { background: var(--card-dark); padding: 25px; border-radius: 24px; border: 1px solid #334155; margin-top: 10px; }
        label { display: block; margin-top: 15px; font-weight: 600; font-size: 0.75rem; color: var(--accent); text-transform: uppercase; }
        select, input { width: 100%; padding: 16px; margin-top: 8px; border-radius: 12px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; font-size: 1rem; }
        
        /* Bottoni */
        .btn { width: 100%; padding: 20px; margin-top: 15px; border-radius: 15px; border: none; font-weight: 800; cursor: pointer; text-transform: uppercase; display: block; transition: 0.3s; }
        .btn-start { background: linear-gradient(135deg, #0284c7, #0369a1); color: white; }
        .btn-stop { background: linear-gradient(135deg, #16a34a, #15803d); color: white; }
        .btn-nav { background: #334155; color: #fbbf24; border: 1px solid #fbbf24; margin-top: 10px; padding: 12px; font-size: 0.8rem; }
        .btn-wa { background: #25d366; color: white; margin-top: 10px; }
        .btn-annulla { background: #475569; color: white; margin-top: 10px; font-size: 0.8rem; }
        
        /* Vocal Search */
        .voice-wrapper { text-align: center; margin: 20px 0; padding: 15px; background: rgba(15, 23, 42, 0.5); border-radius: 15px; border: 1px solid #334155; }
        .mic-btn { width: 65px; height: 65px; border-radius: 50%; background: var(--accent); border: 4px solid var(--card-dark); font-size: 24px; display: flex; align-items: center; justify-content: center; margin: 0 auto; cursor: pointer; color: #0f172a; }
        .mic-btn.recording { background: var(--danger); animation: pulse 1s infinite; color: white; }
        
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
    </style>
</head>
<body>
    <div class="header">LOGISTICA CSA</div>

    <div class="status-container">
        {% for t, info in furgoni.items() %}
        <div class="truck-card {{ info.stato }}">
            <strong>{{ t }}</strong>
            <div class="fuel-indicator">
                {% if info.carburante == "Pieno" %}
                    <i class="fas fa-gas-pump" style="color: var(--success);"></i>
                    <span class="fuel-text" style="color: var(--success);">Pieno</span>
                {% elif info.carburante == "Metà" %}
                    <i class="fas fa-gas-pump" style="color: var(--warning);"></i>
                    <span class="fuel-text" style="color: var(--warning);">Metà</span>
                {% elif info.carburante == "Semivuoto" %}
                    <i class="fas fa-gas-pump" style="color: #f97316;"></i>
                    <span class="fuel-text" style="color: #f97316;">Quasi Vuoto</span>
                {% else %}
                    <i class="fas fa-gas-pump" style="color: var(--danger);"></i>
                    <span class="fuel-text" style="color: var(--danger);">Riserva</span>
                {% endif %}
            </div>
            <button type="button" class="btn-refuel" onclick="vaiARifornimento('{{ t }}')">
                <i class="fas fa-plus"></i> <i class="fas fa-gas-pump"></i> LITRI
            </button>
            <div style="font-size: 0.55rem; margin-top: 5px; opacity: 0.7;">{{ info.stato }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="main-container">
        <div class="card">
            <form method="post" id="main-form">
                {% if not targa_attiva %}
                    <label>Seleziona Mezzo</label>
                    <select name="targa" id="targa_select">
                        <option value="GA087CH">🚚 Piccolo (GA087CH)</option>
                        <option value="GX942TS">🚚🚚 Medio (GX942TS)</option>
                        <option value="GG862HC">🚚🚚🚚 Grosso (GG862HC)</option>
                    </select>

                    <label>Autista</label>
                    <select name="autista">
                        <option value="Valerio">Valerio</option>
                        <option value="Daniele">Daniele</option>
                        <option value="Costantino">Costantino</option>
                        <option value="Simone">Simone</option>
                        <option value="Stefano">Stefano</option>
                    </select>

                    <label>KM Iniziali (Lettura Cruscotto)</label>
                    <input type="number" name="km_partenza" id="km_input" placeholder="Es. 125400" required>
                    
                    <div class="voice-wrapper">
                        <div class="mic-btn" id="mic-btn"><i class="fas fa-microphone"></i></div>
                        <p style="font-size: 0.7rem; margin-top: 10px; color: var(--accent);">Dì i chilometri a voce</p>
                    </div>

                    <button type="submit" name="azione" value="start" class="btn btn-start">Inizia Missione</button>

                {% else %}
                    <input type="hidden" name="targa" value="{{ targa_attiva }}">
                    
                    {% if corsa_attiva.step == 1 %}
                        <label>Destinazione Consegna</label>
                        <select name="destinazione" id="destinazione_field">
                            <option value="POLICLINICO UMBERTO 1">Policlinico Umberto I</option>
                            <option value="SAN GIOVANNI">San Giovanni (Via dei Laterani 4)</option>
                            <option value="PTV">PTV (Tor Vergata P.S.)</option>
                            <option value="VIMINALE">Viminale</option>
                            <option value="VIA CAVOUR 5">Via Cavour 5</option>
                            <option value="VIA GENOVA">Via Genova (Vigili del Fuoco)</option>
                            <option value="AVEZZANO">Ospedale Avezzano</option>
                            <option value="AQUILA">Ospedale L'Aquila</option>
                            <option value="SULMONA">Ospedale Sulmona</option>
                            <option value="PRATICA DI MARE">Aeronautica Pratica di Mare</option>
                            <option value="EUR ARCHIVIO DI STATO">EUR Archivio di Stato</option>
                            <option value="GIRO LIBERO">Giro Libero / Altro</option>
                        </select>
                        <button type="button" class="btn btn-nav" onclick="apriNavigatore()">🧭 APRI NAVIGATORE</button>
                        
                        <label>KM all'Arrivo</label>
                        <input type="number" name="km_destinazione" id="km_input" required>
                        <button type="submit" name="azione" value="arrivo_dest" class="btn btn-start" style="background:var(--warning)">Registra Arrivo</button>
                    
                    {% else %}
                        <label>KM Finali (Rientro in sede)</label>
                        <input type="number" name="km_rientro" id="km_input" required>
                        
                        <label>Livello Gasolio al Rientro</label>
                        <select name="carburante">
                            <option value="Pieno">🟢 PIENO</option>
                            <option value="Metà">🟡 METÀ</option>
                            <option value="Semivuoto">🟠 QUASI VUOTO</option>
                            <option value="Vuoto">🔴 RISERVA</option>
                        </select>
                        
                        <button type="submit" name="azione" value="stop" class="btn btn-stop">Chiudi e Invia Report</button>
                        <button type="button" class="btn btn-wa" onclick="inviaWhatsApp()">🟢 INVIA SU WHATSAPP</button>
                    {% endif %}
                    
                    <button type="submit" name="azione" value="annulla" class="btn btn-annulla" formnovalidate>Annulla / Errore</button>
                {% endif %}
            </form>
        </div>
    </div>

    <script>
    // Funzione Rifornimento Automatica
    function vaiARifornimento(targa) {
        const litri = prompt("Quanti litri di gasolio hai messo nel furgone " + targa + "?");
        if(litri && !isNaN(litri)) {
            fetch('/rifornimento', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({targa: targa, litri: litri})
            }).then(() => {
                alert("Calcolo tanica aggiornato!");
                location.reload();
            });
        }
    }

    // Navigatore Intelligente
    function apriNavigatore() {
        const d = document.getElementById('destinazione_field').value;
        const database = {
            "POLICLINICO UMBERTO 1": "Viale del Policlinico 155, Roma",
            "SAN GIOVANNI": "Via dei Laterani 4, Roma",
            "PTV": "Viale Oxford 81, Roma",
            "VIMINALE": "Piazza del Viminale, Roma",
            "VIA CAVOUR 5": "Via Cavour 5, Roma",
            "VIA GENOVA": "Via Genova 1, Roma",
            "AVEZZANO": "Via Giuseppe di Vittorio, Avezzano",
            "AQUILA": "Via Lorenzo Natali 1, L'Aquila",
            "SULMONA": "Viale Giuseppe Mazzini 100, Sulmona",
            "PRATICA DI MARE": "Via Pratica di Mare 45, Pomezia",
            "EUR ARCHIVIO DI STATO": "Piazzale degli Archivi 27, Roma"
        };
        const indirizzo = database[d] || d + ", Italia";
        window.open("https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(indirizzo), "_blank");
    }

    // WhatsApp Rapido
    function inviaWhatsApp() {
        const km = document.getElementById('km_input').value;
        const targa = "{{ targa_attiva }}";
        const testo = "🚚 CSA LOGISTICA: Fine missione per il mezzo " + targa + ". Chilometri finali registrati: " + km;
        window.open("https://wa.me/?text=" + encodeURIComponent(testo), "_blank");
    }

    // Riconoscimento Vocale
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.lang = 'it-IT';
        
        document.getElementById('mic-btn').onclick = function(e) {
            e.preventDefault();
            recognition.start();
            this.classList.add('recording');
        };

        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            document.getElementById('mic-btn').classList.remove('recording');
            const numeri = transcript.match(/\d+/g);
            if(numeri) {
                document.getElementById('km_input').value = numeri.join('');
                const synth = window.speechSynthesis;
                const utterance = new SpeechSynthesisUtterance("Registrati " + numeri.join('') + " chilometri");
                utterance.lang = 'it-IT';
                synth.speak(utterance);
            }
        };

        recognition.onerror = function() {
            document.getElementById('mic-btn').classList.remove('recording');
        };
    }
    </script>
</body>
</html>
