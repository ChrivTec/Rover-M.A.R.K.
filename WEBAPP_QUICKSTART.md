# M.A.R.K. Rover - Modern WebApp Quick Start

Schnellstart-Anleitung für die M.A.R.K. Rover WebApp

## 🚀 WebApp starten (lokal testen)

```bash
cd c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung
python app.py
```

Dann im Browser öffnen: **<http://localhost:5000>**

## 📱 Zugriff vom Handy (Hotspot)

### 1. Raspberry Pi mit Handy-Hotspot verbinden

```bash
# IP-Adresse des Raspberry Pi finden
hostname -I
```

### 2. WebApp vom Handy aus öffnen

```
http://<raspberry-pi-ip>:5000
```

Typische IPs: `192.168.43.x` oder `192.168.1.x`

## 🎯 Feature-Übersicht

### Dashboard (`/`)

- ✅ Echtzeit-Telemetrie (Batterie, GPS, Motoren)
- ✅ Live-Rover-Tracking auf Karte
- ✅ Route-Auswahl und Vorschau
- ✅ Start/Stop/Notaus Controls
- ✅ System-Status (CPU, Speicher, WLAN)

### Routenplanung (`/new_job`)

- ✅ Interaktives Route-Zeichnen
- ✅ Segment-Färbung (Farbe = Geschwindigkeit)
- ✅ Undo/Redo (Strg+Z / Strg+Y)
- ✅ Zoom-Controls (Strg+Scroll für Extra-Zoom)
- ✅ Route speichern und laden

## 🎨 Segment-Farben = Geschwindigkeiten

| Farbe | Geschwindigkeit |
|-------|----------------|
| 🔴 Rot | 0.1 m/s (langsam) |
| 🟠 Orange | 0.15 m/s |
| 🟡 Gelb | 0.2 m/s (mittel) |
| 🟢 Grün | 0.3 m/s (normal) |
| 🔵 Blau | 0.5 m/s (schnell) |
| 🟣 Lila | 0.4 m/s |

## 🤖 Auto-Start am Raspberry Pi

### Installation

```bash
# Systemd Service kopieren
sudo cp systemd/mark-webapp.service /etc/systemd/system/

# Log-Verzeichnis erstellen
sudo mkdir -p /var/log/mark-rover

# Service aktivieren
sudo systemctl daemon-reload
sudo systemctl enable mark-webapp.service
sudo systemctl start mark-webapp.service
```

### Status prüfen

```bash
# Service-Status
sudo systemctl status mark-webapp

# Logs anzeigen
sudo tail -f /var/log/mark-rover/webapp.log
```

### Service steuern

```bash
# Starten
sudo systemctl start mark-webapp

# Stoppen
sudo systemctl stop mark-webapp

# Neu starten
sudo systemctl restart mark-webapp
```

## 📡 API-Endpunkte

### Rover-Kontrolle

- `POST /api/rover/start` - Mission starten
- `POST /api/rover/stop` - Sanft stoppen
- `POST /api/rover/emergency_stop` - Notaus

### Telemetrie

- `GET /api/telemetry` - Aktualisierte Daten
- `GET /api/telemetry/stream` - Echtzeit-Stream (SSE)

### Routen-Management

- `POST /api/save_route` - Route speichern
- `GET /api/routes` - Alle Routen auflisten
- `GET /api/route/<id>` - Route laden
- `DELETE /api/route/<id>` - Route löschen

## 🧪 Test-Modus vs. Live-Modus

**Test-Modus** (ohne Hardware):

- WebApp zeigt simulierte Daten
- Ideal zum Testen der UI
- Kein Rover nötig

**Live-Modus** (am Raspberry Pi):

- Echte Sensor-Daten
- Rover-Steuerung funktional
- GPS, IMU, Motoren aktiv

## ⚙️ Konfiguration

Port ändern (optional):

```python
# In app.py, Zeile ~660:
port = 5000  # Beliebigen Port wählen
```

## 🐛 Troubleshooting

**WebApp lädt nicht:**

- Firewall-Regeln prüfen
- Port 5000 verfügbar?
- `python app.py` zeigt Fehler?

**Keine Route-Daten:**

- `routes/` Verzeichnis existiert?
- Schreibrechte vorhanden?

**Echtzeit-Updates funktionieren nicht:**

- Browser unterstützt Server-Sent Events?
- Chrome/Firefox empfohlen

**Rover reagiert nicht:**

- Hardware initialisiert? (Live-Modus)
- `main.py` läuft parallel?
- Logs prüfen: `/var/log/mark-rover/`

## 📞 Support

Bei Problemen:

1. Logs prüfen: `sudo journalctl -u mark-webapp -f`
2. Test-Modus verwenden für UI-Tests
3. Hardware-Verbindungen checken

---

**Viel Erfolg mit M.A.R.K.! 🚀**
