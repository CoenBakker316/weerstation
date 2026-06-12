import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# -----------------------------
# DATABASE INITIALISATIE
# -----------------------------
def init_db():
    conn = sqlite3.connect("weather.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature REAL,
            humidity REAL,
            pressure REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# API: Raspberry Pi upload
# -----------------------------
@app.route("/api/upload", methods=["POST"])
def upload():
    data = request.json
    temp = data["temperature"]
    hum = data["humidity"]
    pres = data["pressure"]

    conn = sqlite3.connect("weather.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO measurements (temperature, humidity, pressure)
        VALUES (?, ?, ?)
    """, (temp, hum, pres))

    c.execute("""
        DELETE FROM measurements
        WHERE timestamp < datetime('now', '-1 hour')
    """)

    conn.commit()
    conn.close()

    return "OK"

# -----------------------------
# API: Data voor grafieken
# -----------------------------
@app.route("/data")
def data():
    conn = sqlite3.connect("weather.db")
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, temperature, humidity, pressure
        FROM measurements
        WHERE timestamp >= datetime('now', '-1 hour')
    """)
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)

# -----------------------------
# HTML DASHBOARD
# -----------------------------
@app.route("/")
def index():
    return """
    <!doctype html>
    <html>
    <head>
        <title>Weerstation</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

        <style>
            body { background:#111; color:white; font-family:Arial; text-align:center; }

            /* Blokjes */
            .cards {
                display:flex;
                justify-content:center;
                gap:20px;
                margin:20px auto;
                flex-wrap:wrap;
            }
            .card {
                background:#222;
                padding:20px;
                border-radius:10px;
                width:150px;
                box-shadow:0 0 10px #000;
            }
            .value {
                font-size:32px;
                font-weight:bold;
                margin-top:10px;
                transition:0.3s;
            }

            /* Tabbladen */
            .tabs {
                display:flex;
                justify-content:center;
                margin-top:20px;
            }
            .tab {
                padding:10px 20px;
                margin:0 5px;
                background:#222;
                border-radius:5px;
                cursor:pointer;
            }
            .tab.active { background:#444; }

            .chart-container { display:none; }
            .chart-container.active { display:block; }
        </style>
    </head>

    <body>
        <h1>Weerstation – Live</h1>

        <!-- Bovenste blokjes -->
        <div class="cards">
            <div class="card">
                <div>Temperatuur</div>
                <div id="tempVal" class="value">-- °C</div>
            </div>

            <div class="card">
                <div>Luchtvochtigheid</div>
                <div id="humVal" class="value">-- %</div>
            </div>

            <div class="card">
                <div>Luchtdruk</div>
                <div id="presVal" class="value">-- hPa</div>
            </div>
        </div>

        <!-- Tabbladen -->
        <div class="tabs">
            <div class="tab active" onclick="showTab(0)">Temperatuur</div>
            <div class="tab" onclick="showTab(1)">Vochtigheid</div>
            <div class="tab" onclick="showTab(2)">Luchtdruk</div>
        </div>

        <!-- Grafieken -->
        <div id="chart0" class="chart-container active">
            <canvas id="tempChart"></canvas>
        </div>

        <div id="chart1" class="chart-container">
            <canvas id="humChart"></canvas>
        </div>

        <div id="chart2" class="chart-container">
            <canvas id="presChart"></canvas>
        </div>

        <script>
        function showTab(index) {
            document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active', i===index));
            document.querySelectorAll('.chart-container').forEach((c,i)=>c.classList.toggle('active', i===index));
        }

        async function loadData() {
            const res = await fetch('/data');
            const data = await res.json();

            if (data.length > 0) {
                const last = data[data.length - 1];

                const t = last[1];
                const h = last[2];
                const p = last[3];

                // waarden invullen
                document.getElementById('tempVal').innerText = t.toFixed(1) + " °C";
                document.getElementById('humVal').innerText  = h.toFixed(1) + " %";
                document.getElementById('presVal').innerText = p.toFixed(1) + " hPa";

                // kleurregels
                document.getElementById('tempVal').style.color = t > 30 ? "red" : "white";
                document.getElementById('humVal').style.color  = h > 80 ? "red" : "white";
                document.getElementById('presVal').style.color = p < 990 ? "red" : "white";
            }

            const labels = data.map(r => r[0]);
            const temp = data.map(r => r[1]);
            const hum  = data.map(r => r[2]);
            const pres = data.map(r => r[3]);

            tempChart.data.labels = labels;
            tempChart.data.datasets[0].data = temp;
            tempChart.update();

            humChart.data.labels = labels;
            humChart.data.datasets[0].data = hum;
            humChart.update();

            presChart.data.labels = labels;
            presChart.data.datasets[0].data = pres;
            presChart.update();
        }

        const tempChart = new Chart(document.getElementById('tempChart'), {
            type: 'line',
            data: { labels: [], datasets: [{ label:'Temperatuur (°C)', borderColor:'red', data:[] }] }
        });

        const humChart = new Chart(document.getElementById('humChart'), {
            type: 'line',
            data: { labels: [], datasets: [{ label:'Vochtigheid (%)', borderColor:'cyan', data:[] }] }
        });

        const presChart = new Chart(document.getElementById('presChart'), {
            type: 'line',
            data: { labels: [], datasets: [{ label:'Luchtdruk (hPa)', borderColor:'yellow', data:[] }] }
        });

        setInterval(loadData, 2000);
        loadData();
        </script>
    </body>
    </html>
    """

# -----------------------------
# RENDER START
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
