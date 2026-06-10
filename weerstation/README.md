# 🌦️ Raspberry Pi Weerstation (Render Cloud Version)

Dit project is een online weerstation dat draait op een Raspberry Pi met een BME280-sensor.  
De data wordt elke 10 seconden naar een gratis Render-webserver gestuurd, waar een dashboard de laatste 60 minuten aan metingen toont.

✔ Geen port-forwarding  
✔ Geen Cloudflare nodig  
✔ Volledig HTTPS  
✔ Overal ter wereld te bekijken  
✔ Gratis hosting via Render  

---

## 📡 Hoe werkt het?

### Raspberry Pi
- Leest elke 10 seconden temperatuur, luchtvochtigheid en luchtdruk uit.
- Stuurt deze data naar de Render-cloud via een API (`/api/upload`).

### Render (Cloud)
- Draait een Flask-webserver.
- Slaat de data op in een SQLite-database.
- Verwijdert automatisch alle data ouder dan 1 uur.
- Toont een live grafiek via Chart.js.

---

## 🗂️ Bestanden in dit project

