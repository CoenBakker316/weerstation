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

    # Nieuwe meting opslaan
    c.execute("""
        INSERT INTO measurements (temperature, humidity, pressure)
        VALUES (?, ?, ?)
    """, (temp, hum, pres))

    # Oude data verwijderen (ouder dan 1 uur)
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
    </head>
    <body style="background:#111; color:white; font-family:Arial; text-align:center;">
        <h1>Weerstation – Live</h1>
        <canvas id="chart" style="width:100%; height:300px;"></canvas>

        <script>
        async function loadData() {
            const res = await fetch('/data');
            const data = await res.json();

            const labels = data.map(r => r[0]);
            const temp = data.map(r => r[1]);

            chart.data.labels = labels;
            chart.data.datasets[0].data = temp;
            chart.update();
        }

        const ctx = document.getElementById('chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperatuur (°C)',
                    data: [],
                    borderColor: 'red'
                }]
            }
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
