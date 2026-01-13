# 🚀 M.A.R.K. Rover - INSTALLATION START HIER!

## 📋 Überblick

Diese Anleitung führt dich in **4 einfachen Schritten** vom USB-Stick zum fahrenden Rover.

**Gesamtzeit:** Ca. 60 Minuten  
**Schwierigkeit:** ⭐⭐⭐ (Mittel)

---

# 🎯 SCHRITT 1: USB-STICK VORBEREITEN (10 Min)

## 1.1 Dateien auf USB-Stick kopieren

**Auf deinem Windows-PC:**

1. **USB-Stick formatieren** (FAT32 oder exFAT)
   - Rechtsklick auf USB-Stick → Formatieren
   - Dateisystem: FAT32 oder exFAT
   - Schnellformatierung: ✓

2. **Alle Rover-Dateien kopieren**
   ```
   Quelle: C:\Users\chriv\.gemini\antigravity\scratch\rover-steuerung\
   
   Kopiere ALLES nach: USB-Stick:\rover-steuerung\
   ```

3. **Prüfen: 29 Dateien auf USB-Stick**
   ```
   rover-steuerung/
   ├── config.json              ✓
   ├── main.py                  ✓
   ├── install.sh               ✓
   ├── (... 26 weitere Dateien)
   ```

4. **USB-Stick sicher entfernen**

---

# 🔌 SCHRITT 2: RASPBERRY PI SETUP (30 Min)

## 2.1 Hardware vorbereiten

**Was du brauchst:**
- ✅ Raspberry Pi 5 mit Raspberry Pi OS installiert
- ✅ Monitor, Tastatur, Maus (für Setup)
- ✅ Internet-Verbindung (WLAN oder Ethernet)
- ✅ USB-Stick mit Rover-Software

**Hardware NOCH NICHT anschließen!** Erst Software installieren.

---

## 2.2 Raspberry Pi starten

1. **Raspberry Pi einschalten**
2. **Warten bis Desktop erscheint**
3. **Terminal öffnen** (schwarzes Icon oben)

---

## 2.3 USB-Stick mounten

**Im Terminal:**

```bash
# 1. USB-Stick einstecken

# 2. Warte 5 Sekunden

# 3. Prüfe ob gemountet:
ls /media/pi/

# Sollte zeigen: USB-STICK oder ähnlich

# 4. Ins Verzeichnis wechseln:
cd /media/pi/*/rover-steuerung

# 5. Prüfen ob Dateien da sind:
ls
# Sollte 29 Dateien zeigen
```

---

## 2.4 Software installieren (AUTOMATISCH!)

```bash
# 1. Installation starten (OHNE sudo!):
bash install.sh

# 2. Bei Frage "systemd Services installieren?" → y drücken

# 3. Warten... (15-20 Minuten)
#    Das Script macht:
#    - System Update
#    - Dependencies installieren
#    - RTKLIB kompilieren
#    - Python Packages installieren
#    - I2C aktivieren
```

**⏰ Kaffee holen! Dauert ~15-20 Min**

---

## 2.5 Neustart

**WICHTIG:** Nach Installation MUSS Pi neu starten!

```bash
sudo reboot
```

**Warte bis Desktop wieder da ist.**

---

# 🔧 SCHRITT 3: HARDWARE ANSCHLIESSEN (15 Min)

## 3.1 Hardware-Checkliste

**Jetzt Hardware anschließen:**

### GPS/GNSS (u-blox ZED-F9P):
```
1. USB-Kabel an Pi anschließen
2. GPS-Antenne aufstecken
3. Antenne AUßEN platzieren (freie Sicht zum Himmel!)
```

### IMU (BNO085):
```
Raspberry Pi 5 GPIO:
- SDA (Pin 3)  → BNO085 SDA
- SCL (Pin 5)  → BNO085 SCL
- 3.3V (Pin 1) → BNO085 VIN
- GND (Pin 6)  → BNO085 GND
```

### Motor Controller (RoboClaw 2x15A):
```
1. USB-Kabel an Pi anschließen
2. Motoren an M1 (links) und M2 (rechts)
3. Batterie anschließen (12V, ERST AM ENDE!)
```

---

## 3.2 Hardware testen

**Terminal öffnen:**

```bash
# 1. Ins Rover-Verzeichnis:
cd ~/rover-steuerung

# 2. Virtual Environment aktivieren:
source venv/bin/activate

# 3. Ports automatisch erkennen:
python3 setup_ports.py

# Sollte zeigen:
# ✓ GNSS gefunden: /dev/ttyACM1
# ✓ Motor Controller gefunden: /dev/ttyACM0
# ✓ config.json aktualisiert
```

**Wenn Ports nicht erkannt:**
```bash
# Manuell anzeigen:
ls -l /dev/ttyACM*

# Sollte zeigen: ttyACM0 und ttyACM1
# Falls andere Ports: config.json manuell anpassen
```

---

## 3.3 GPS testen

```bash
source venv/bin/activate
python3 test_gnss.py

# Erwartete Ausgabe (nach 1-2 Min):
# Position: 50.933383, 6.988584
# Fix Quality: GPS  (noch nicht RTK!)
# Satellites: 12
```

**Strg+C zum Beenden**

---

## 3.4 IMU testen

```bash
# I2C scannen:
sudo i2cdetect -y 1

# Sollte zeigen: 4a (das ist der BNO085!)

# IMU Test:
python3 test_imu.py

# Erwartete Ausgabe:
# Heading: 45.3° (0=North, 90=East)
# Roll: 0.2°
# Pitch: -1.5°
```

**Drehe den Pi → Heading sollte sich ändern!**

**Strg+C zum Beenden**

---

## 3.5 Motoren testen

**⚠️ VORSICHT! Batterie erst JETZT anschließen!**

```bash
# Batterie an RoboClaw anschließen (B+ und B-)

python3 test_motors.py

# Sollte zeigen:
# Battery: 12.4 V
# Befehle: 1, 2, 3, 4, 5, s, q

# Teste:
# Eingabe: 1  → Beide Räder vorwärts 2 Sek
# Eingabe: s  → Stop
# Eingabe: q  → Quit
```

**Wenn Motoren nicht drehen:**
→ RoboClaw Einstellungen prüfen (BasicMicro Motion Studio nötig)

---

# 🌐 SCHRITT 4: INTERNET & RTK (15 Min)

## 4.1 Mobile Hotspot einrichten

**Auf deinem Smartphone:**
1. Mobilen Hotspot aktivieren
2. SSID & Passwort notieren

**Auf Raspberry Pi:**
1. WLAN-Icon klicken (oben rechts)
2. Deinen Hotspot auswählen
3. Passwort eingeben
4. Verbinden

**Internet testen:**
```bash
ping -c 3 google.de

# Sollte antworten!
```

---

## 4.2 RTK/NTRIP Service starten

```bash
# Service starten:
sudo systemctl start rtk-ntrip.service

# Status prüfen:
sudo systemctl status rtk-ntrip.service

# Sollte zeigen: "active (running)"

# Logs live anschauen:
sudo journalctl -u rtk-ntrip.service -f
```

**Warten auf RTK Fix:**
```
0-2 Min:   GPS (Fix Quality = 1)
2-5 Min:   RTK Float (Fix Quality = 5)
5-15 Min:  RTK Fixed (Fix Quality = 4) ← ZIEL! ✅
```

**Kontrollieren:**
```bash
# In neuem Terminal:
source venv/bin/activate
python3 test_gnss.py

# Sollte zeigen:
# Fix Quality: RTK Fixed ✅
```

**Strg+C zum Beenden**

---

# 🚗 ROVER STARTEN!

## Option A: Manueller Start (für Tests)

```bash
cd ~/rover-steuerung
source venv/bin/activate

python3 main.py
```

**Ausgabe sollte zeigen:**
```
============================================================
M.A.R.K. Rover Control System - Initialisierung
============================================================
📋 Validiere Konfiguration...
✅ Konfiguration erfolgreich geladen

============================================================
⚙️  Hardware-Initialisierung
============================================================
🔍 Automatische Port-Erkennung...
✓ GNSS Auto-erkannt: /dev/ttyACM1
✓ Motor Controller Auto-erkannt: /dev/ttyACM0

📡 Verbinde GNSS...
✅ GNSS verbunden

🧭 Verbinde IMU...
✅ IMU verbunden

🤖 Verbinde Motor Controller...
✅ Motor Controller verbunden

🛡️  Starte GPS-Watchdog...
✅ Watchdog aktiv (Timeout: 30s)

============================================================
✅ Alle Hardware-Module erfolgreich initialisiert!
============================================================

State: IDLE | Pos: 50.933383, 6.988584 | Fix: RTK Fixed | Sats: 18
```

**Rover fährt los wenn:**
- ✅ `waypoints.json` geladen
- ✅ RTK Fixed erreicht
- ✅ Alle Safety-Checks OK

---

## Option B: Automatischer Start (Service)

```bash
# Service aktivieren (startet beim Booten):
sudo systemctl enable rover-control.service

# Service manuell starten:
sudo systemctl start rover-control.service

# Logs anschauen:
sudo journalctl -u rover-control.service -f
```

---

# 🗺️ EIGENE ROUTE ERSTELLEN

## Waypoints aufzeichnen

```bash
# GPS-Position live anzeigen:
python3 test_gnss.py

# Gehe zu gewünschten Punkten im Garten
# Notiere Koordinaten:
```

**Beispiel:**
```
Punkt 1: 50.9333833, 6.9885841
Punkt 2: 50.9334000, 6.9885841
Punkt 3: 50.9334000, 6.9886000
Punkt 4: 50.9333833, 6.9886000
```

## waypoints.json bearbeiten

```bash
nano waypoints.json
```

```json
{
  "id": "mein_garten",
  "name": "Rechteck Route",
  "waypoints": [
    {"lat": 50.9333833, "lon": 6.9885841, "speed_ms": 0.3},
    {"lat": 50.9334000, "lon": 6.9885841, "speed_ms": 0.3},
    {"lat": 50.9334000, "lon": 6.9886000, "speed_ms": 0.25},
    {"lat": 50.9333833, "lon": 6.9886000, "speed_ms": 0.25},
    {"lat": 50.9333833, "lon": 6.9885841, "speed_ms": 0.3}
  ]
}
```

**Speichern:** Strg+O, Enter, Strg+X

---

# ⚠️ TROUBLESHOOTING

## Problem: GPS findet keinen Fix

**Lösung:**
1. Antenne hat FREIE Sicht zum Himmel?
2. Im Freien (nicht im Gebäude)?
3. Warte länger (kann 15 Min dauern)
4. NTRIP läuft? `sudo systemctl status rtk-ntrip.service`

## Problem: IMU nicht gefunden

**Lösung:**
```bash
# I2C scannen:
sudo i2cdetect -y 1

# Wenn leer:
# 1. Verkabelung prüfen
# 2. I2C aktiviert? sudo raspi-config
# 3. Neustart: sudo reboot
```

## Problem: Motoren drehen nicht

**Lösung:**
1. Batterie angeschlossen? (min. 11V)
2. RoboClaw Einstellungen:
   - Baudrate: 38400
   - Adresse: 128 (0x80)
   - Mode: Packet Serial
3. Motor-Verkabelung korrekt?

## Problem: Rover fährt falsche Richtung

**Lösung:**
```bash
# Motor-Richtung tauschen:
# 1. M1 Kabel umdrehen (+ und -)
# ODER
# 2. Im RoboClaw: Motor Direction invertieren
```

---

# ✅ ERFOLGS-CHECKLISTE

- [ ] USB-Stick vorbereitet (29 Dateien)
- [ ] `install.sh` erfolgreich durchgelaufen
- [ ] Raspberry Pi neugestartet
- [ ] GPS angeschlossen & getestet (RTK Fixed!)
- [ ] IMU angeschlossen & getestet (Heading korrekt)
- [ ] Motoren angeschlossen & getestet (drehen sich)
- [ ] Mobile Hotspot verbunden
- [ ] RTK Service läuft
- [ ] `main.py` startet ohne Fehler
- [ ] Waypoints erstellt
- [ ] **ROVER FÄHRT!** 🎉

---

# 🎓 NÄCHSTE SCHRITTE

1. **PID Tuning** (wenn Rover zu stark schwingt)
   ```bash
   nano config.json
   # Ändere: control.cross_track_pid
   ```

2. **Web Dashboard** bauen (API läuft auf Port 5000)

3. **Mehr Funktionen:**
   - Obstacle Detection
   - Spray-Actions
   - Multi-Routen

---

# 📞 HILFE

**Logs anschauen:**
```bash
# System-Logs:
sudo journalctl -n 100

# RTK Logs:
sudo journalctl -u rtk-ntrip.service -n 50

# Rover Logs:
sudo journalctl -u rover-control.service -n 50
```

**Detaillierte Anleitungen:**
- `USB_INSTALLATION.md` - Ausführliche Anleitung
- `README.md` - Technische Details
- `ROVER_LAYOUT.md` - Mechanischer Aufbau
- `INSTALLATION.md` - Schnellstart

---

# 🚀 VIEL ERFOLG!

**Du hast es geschafft! Dein autonomer Rover ist jetzt einsatzbereit!** 🤖🌱

**Sicherheitshinweise:**
- ⚠️ Erste Tests in sicherem Bereich
- ⚠️ Emergency Stop bereithalten (API: `/api/rover/emergency_stop`)
- ⚠️ RTK Fixed abwarten vor Start
- ⚠️ Batterie-Spannung überwachen

**Happy Roving!** 🎉
