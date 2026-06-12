# 🌦️ Raspberry Pi Weerstation (Render Cloud Version)

Dit project is een online weerstation dat draait op een Raspberry Pi met een BME280-sensor.
De data wordt elke 10 seconden naar een gratis Render-webserver gestuurd, waar een dashboard de laatste 60 minuten toont.

✔ Geen port-forwarding  
✔ Gratis hosting  
✔ HTTPS automatisch  
✔ Overal ter wereld te bekijken  

## 📡 Raspberry Pi → Render Upload

Gebruik dit script op je Pi:

```python
import time
import requests
from bme280 import read_bme280

while True:
    temp, hum, pres = read_bme280()

    requests.post(
        "https://jouw-render-url.onrender.com/api/upload",
        json={
            "temperature": temp,
            "humidity": hum,
            "pressure": pres
        }
    )

    time.sleep(10)
