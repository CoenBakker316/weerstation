import time
import threading
import sqlite3
import os
from smbus2 import SMBus
from flask import Flask, jsonify, send_from_directory

# -----------------------------
# BME280 SENSOR INITIALISATIE
# -----------------------------

BME280_ADDR = 0x76
bus = SMBus(1)

def read_bytes(reg, length):
    return bus.read_i2c_block_data(BME280_ADDR, reg, length)

def write_reg(reg, value):
    bus.write_byte_data(BME280_ADDR, reg, value)

# Kalibratie uitlezen
calib = read_bytes(0x88, 24)
calib_h = read_bytes(0xA1, 1) + read_bytes(0xE1, 7)

dig_T1 = calib[1] << 8 | calib[0]
dig_T2 = (calib[3] << 8) | calib[2]
dig_T3 = (calib[5] << 8) | calib[4]

dig_P1 = calib[7] << 8 | calib[6]
dig_P2 = (calib[9] << 8) | calib[8]
dig_P3 = (calib[11] << 8) | calib[10]
dig_P4 = (calib[13] << 8) | calib[12]
dig_P5 = (calib[15] << 8) | calib[14]
dig_P6 = (calib[17] << 8) | calib[16]
dig_P7 = (calib[19] << 8) | calib[18]
dig_P8 = (calib[21] << 8) | calib[20]
dig_P9 = (calib[23] << 8) | calib[22]

dig_H1 = calib_h[0]
dig_H2 = (calib_h[2] << 8) | calib_h[1]
dig_H3 = calib_h[3]
dig_H4 = (calib_h[4] << 4) | (calib_h[5] & 0x0F)
dig_H5 = (calib_h[6] << 4) | (calib_h[5] >> 4)
dig_H6 = calib_h[7]

write_reg(0xF2, 0x01)
write_reg(0xF4, 0x27)
write_reg(0xF5, 0xA0)

t_fine = 0

def compensate_temperature(adc_T):
    global t_fine
    var1 = (((adc_T >> 3) - (dig_T1 << 1)) * dig_T2) >> 11
    var2 = (((((adc_T >> 4) - dig_T1) * ((adc_T >> 4) - dig_T1)) >> 12) * dig_T3) >> 14
    t_fine = var1 + var2
    T = (t_fine * 5 + 128) >> 8
    return T / 100.0

def compensate_pressure(adc_P):
    global t_fine
    var1 = t_fine - 128000
    var2 = var1 * var1 * dig_P6
    var2 = var2 + ((var1 * dig_P5) << 17)
    var2 = var2 + (dig_P4 << 35)
    var1 = ((var1 * var1 * dig_P3) >> 8) + ((var1 * dig_P2) << 12)
    var1 = (((1 << 47) + var1) * dig_P1) >> 33
    if var1 == 0:
        return 0
    p = 1048576 - adc_P
    p = (((p << 31) - var2) * 3125) // var1
    var1 = (dig_P9 * (p >> 13) * (p >> 13)) >> 25
    var2 = (dig_P8 * p) >> 19
    p = ((p + var1 + var2) >> 8) + (dig_P7 << 4)
    return p / 25600.0

def compensate_humidity(adc_H):
    global t_fine
    v_x1 = t_fine - 76800
    v_x1 = (((((adc_H << 14) - (dig_H4 << 20) - (dig_H5 * v_x1)) + 16384) >> 15) *
            (((((((v_x1 * dig_H6) >> 10) * (((v_x1 * dig_H3) >> 11) + 32768)) >> 10) + 2097152) *
              dig_H2 + 8192) >> 14))
    v_x1 = v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) * dig_H1) >> 4)
    v_x1 = max(min(v_x1, 419430400), 0)
    return (v_x1 >> 12) / 1024.0

def read_bme280():
    data = read_bytes(0xF7, 8)
    adc_P = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
    adc_T = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
    adc_H = (data[6] << 8) | data[7]
    temp = compensate_temperature(adc_T)
    pres = compensate_pressure(adc_P)
    hum = compensate_humidity(adc_H)
    return temp, hum, pres

# -----------------------------
# DATABASE LOGGER THREAD
# -----------------------------

def logger_thread():
    while True:
        temp, hum, pres = read_bme280()
        conn = sqlite3.connect("weather.db")
        c = conn.cursor()

        # Nieuwe meting opslaan
        c.execute(
            "INSERT INTO measurements (temperature, humidity, pressure) VALUES (?, ?, ?)",
            (temp, hum, pres)
        )

        # Oude data verwijderen (ouder dan 1 uur)
        c.execute("""
            DELETE FROM measurements
            WHERE timestamp < datetime('now', '-1 hour')
        """)

        conn.commit()
        conn.close()

        time.sleep(10)  # elke 10 seconden loggen

threading.Thread(target=logger_thread, daemon=True).start()

# -----------------------------
# FLASK APP
# -----------------------------

app = Flask(__name__)

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

# PWA-bestanden serveren
@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.path.dirname(__file__), 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(os.path.dirname(__file__), 'service-worker.js')

# -----------------------------
# HTML MET DRIE TABBLADEN + PWA
# -----------------------------

HTML = """
<!doctype html>
<html>
<head>
    <title>Weerstation</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#111111">
    <link rel="manifest" href="/manifest.json">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background:#111; color:#eee; font-family:Arial; text-align:center; margin:0; }
        h1 { margin:20px 0; }
        .tabs { display:flex; justify-content:center; margin:0 0 10px 0; background:#000; }
        .tab {
            padding:10px 20px;
            margin:5px;
            background:#222;
            border-radius:5px;
            cursor:pointer;
            font-size:14px;
        }
        .tab.active { background:#444; }
        .content { display:none; padding:10px; }
        .content.active { display:block; }
        canvas { max-width:100%; height:300px; }
    </style>
</head>

<body>
    <h1>Weerstation – Live Data</h1>

    <div class="tabs">
        <div class="tab active" onclick="showTab('temp')">Temperatuur</div>
        <div class="tab" onclick="showTab('hum')">Luchtvochtigheid</div>
        <div class="tab" onclick="showTab('pres')">Luchtdruk</div>
    </div>

    <div id="temp" class="content active">
        <canvas id="chartTemp"></canvas>
    </div>

    <div id="hum" class="content">
        <canvas id="chartHum"></canvas>
    </div>

    <div id="pres" class="content">
        <canvas id="chartPres"></canvas>
    </div>

<script>
function showTab(id) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));

    document.querySelector(`.tab[onclick="showTab('${id}')"]`).classList.add('active');
    document.getElementById(id).classList.add('active');
}

async function fetchData() {
    const res = await fetch('/data');
    return await res.json();
}

const ctxTemp = document.getElementById('chartTemp').getContext('2d');
const ctxHum  = document.getElementById('chartHum').getContext('2d');
const ctxPres = document.getElementById('chartPres').getContext('2d');

const chartTemp = new Chart(ctxTemp, {
    type: 'line',
    data: { labels: [], datasets: [{ label:'Temperatuur (°C)', data:[], borderColor:'red' }] },
    options: { responsive:true, maintainAspectRatio:false }
});

const chartHum = new Chart(ctxHum, {
    type: 'line',
    data: { labels: [], datasets: [{ label:'Luchtvochtigheid (%)', data:[], borderColor:'cyan' }] },
    options: { responsive:true, maintainAspectRatio:false }
});

const chartPres = new Chart(ctxPres, {
    type: 'line',
    data: { labels: [], datasets: [{ label:'Luchtdruk (hPa)', data:[], borderColor:'yellow' }] },
    options: { responsive:true, maintainAspectRatio:false }
});

async function updateCharts() {
    const data = await fetchData();

    const labels = data.map(r => r[0]);
    const temp   = data.map(r => r[1]);
    const hum    = data.map(r => r[2]);
    const pres   = data.map(r => r[3]);

    chartTemp.data.labels = labels;
    chartTemp.data.datasets[0].data = temp;
    chartTemp.update();

    chartHum.data.labels = labels;
    chartHum.data.datasets[0].data = hum;
    chartHum.update();

    chartPres.data.labels = labels;
    chartPres.data.datasets[0].data = pres;
    chartPres.update();
}

setInterval(updateCharts, 2000);
updateCharts();

// Service worker registreren voor PWA
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js')
        .then(reg => console.log('Service worker geregistreerd:', reg))
        .catch(err => console.log('Service worker fout:', err));
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return HTML

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
