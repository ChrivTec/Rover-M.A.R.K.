# 🚀 M.A.R.K. Rover - USB-Stick Installation & Deployment

## Übersicht

Diese Anleitung erklärt, wie du das komplette M.A.R.K. Rover System vom Windows-PC auf einen USB-Stick kopierst und dann auf dem Raspberry Pi 5 installierst.

---

## Teil 1: USB-Stick vorbereiten (Windows PC)

### Schritt 1: Dateien auf USB-Stick kopieren

1. **USB-Stick einstecken** (mindestens 1 GB frei)

2. **Kompletten Projekt-Ordner kopieren:**

   ```
   Quelle: C:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung
   Ziel:   E:\mark-rover\  (E: = dein USB-Stick)
   ```

3. **Überprüfen, dass alle Dateien da sind:**
   - ✅ 19 Python-Dateien (`.py`)
   - ✅ `config.json`
   - ✅ `waypoints_test.json` (die Route vom Web-Interface)
   - ✅ `requirements.txt`

> [!IMPORTANT]
> **Kritische Dateien prüfen:**
>
> - `config.json` - Adresse muss **131** sein!
> - `motor_module.py` - Neue Version mit signed duty commands
> - `test_motors.py` - Mit Tests 6-10 für Spot-Turns

### Schritt 2: USB-Stick sicher entfernen

Windows: Rechtsklick auf USB-Stick → "Auswerfen"

---

## Teil 2: Raspberry Pi 5 Installation

### Voraussetzungen

**Hardware:**

- ✅ Raspberry Pi 5 (bereits vorbereitet aus vorherigen Tests)
- ✅ RoboClaw 2x15A (Adresse 131, Baudrate 38400)
- ✅ 12V Netzteil für Motoren
- ✅ USB-Kabel für RoboClaw

**Software-Basis:**

- ✅ Raspberry Pi OS (Bookworm oder neuer)
- ✅ Python 3.11+

### Schritt 3: USB-Stick am Raspberry Pi einstecken

1. **USB-Stick einstecken**
2. **Terminal öffnen** (Strg+Alt+T)
3. **USB-Stick finden:**

   ```bash
   lsblk
   # Suche nach /dev/sda1 oder /dev/sdb1
   ```

4. **USB-Stick mounten (falls nicht automatisch):**

   ```bash
   sudo mkdir -p /mnt/usb
   sudo mount /dev/sda1 /mnt/usb
   ls /mnt/usb  # Sollte 'mark-rover' Ordner zeigen
   ```

### Schritt 4: Projekt ins Home-Verzeichnis kopieren

```bash
# Ins Home-Verzeichnis wechseln
cd ~

# Projekt kopieren
cp -r /mnt/usb/mark-rover ~/rover-steuerung

# In Projekt-Ordner wechseln
cd ~/rover-steuerung

# Überprüfen
ls -la
# Sollte alle .py Dateien und config.json zeigen
```

### Schritt 5: Python-Abhängigkeiten installieren

```bash
# Virtual Environment erstellen (empfohlen)
python3 -m venv venv

# Virtual Environment aktivieren
source venv/bin/activate

# Abhängigkeiten installieren
pip install --upgrade pip
pip install -r requirements.txt
```

**Erwartete Pakete:**

- pyserial
- numpy
- flask
- smbus2 (für IMU)

### Schritt 6: Berechtigungen setzen

```bash
# Aktuellen User zur dialout-Gruppe hinzufügen (für Serial)
sudo usermod -a -G dialout $USER

# I2C aktivieren (für IMU)
sudo raspi-config
# → Interface Options → I2C → Enable

# System neu starten (wichtig!)
sudo reboot
```

Nach dem Neustart:

```bash
cd ~/rover-steuerung
source venv/bin/activate
```

---

## Teil 3: Hardware-Tests durchführen

### Test 1: RoboClaw Verbindung prüfen

```bash
python3 test_roboclaw_address.py
```

**Erwartete Ausgabe:**

```
Scanning for RoboClaw controllers...
Found RoboClaw at address 131 (0x83)
Battery voltage: 12.0V
```

> [!WARNING]
> **Wenn Adresse NICHT 131 ist:**
>
> 1. Gefundene Adresse notieren (z.B. 128)
> 2. In `config.json` ändern:
>
>    ```bash
>    nano config.json
>    # Ändere "roboclaw_address": 131 → gefundene Adresse
>    # Strg+O zum Speichern, Strg+X zum Beenden
>    ```

### Test 2: Motortest (KRITISCH!)

**Vorbereitung:**

1. ✅ 12V Netzteil für Motoren EINSCHALTEN
2. ✅ Rover auf Böcke stellen (Räder frei drehen)
3. ✅ Emergency-Stop vorbereiten (Netzteil-Schalter)

**Test starten:**

```bash
python3 test_motors.py
```

**Test-Ablauf:**

```
Connected to RoboClaw successfully
Battery: 12.0 V  ← WICHTIG: Muss angezeigt werden!

Motor Test Commands:
  1 - Forward test (both motors 0.2 m/s for 2s)
  ...
  6 - SPOT-TURN LEFT (M1 backward, M2 forward)
  7 - SPOT-TURN RIGHT (M1 forward, M2 backward)
  ...

Enter command: 
```

**Test-Sequenz:**

| Schritt | Eingabe | Erwartetes Verhalten |
|---------|---------|---------------------|
| 1 | `1` | ✅ Beide Räder drehen vorwärts (2 Sek) |
| 2 | `s` | ✅ Räder stoppen sofort |
| 3 | `2` | ✅ Beide Räder drehen rückwärts (2 Sek) |
| 4 | `9` | ✅ Nur LINKES Rad dreht vorwärts |
| 5 | `0` | ✅ Nur RECHTES Rad dreht rückwärts |
| 6 | `6` | ✅ SPOT-TURN LINKS: L rückwärts, R vorwärts |
| 7 | `7` | ✅ SPOT-TURN RECHTS: L vorwärts, R rückwärts |

> [!CAUTION]
> **Wenn sich der Rover bei Test 6/7 vorwärts bewegt statt zu drehen:**
>
> - Motoren sind spiegelverkehrt angeschlossen
> - Lösung: M1 und M2 Kabel am RoboClaw vertauschen

**Test beenden:**

```
Enter command: q
```

### Test 3: GPS-Modul (optional, wenn verfügbar)

```bash
python3 test_gnss.py
```

Erwartete Ausgabe:

```
GNSS Fix: RTK Fixed
Satellites: 18
Position: 50.933383, 6.988584
HDOP: 0.8
```

### Test 4: IMU-Modul (optional, wenn verfügbar)

```bash
python3 test_imu.py
```

Erwartete Ausgabe:

```
BNO085 calibration: MAG=3, GYRO=3, ACCEL=3
Heading: 245.3°
```

---

## Teil 4: Simulation testen (ohne Hardware)

Falls du die Navigation testen willst OHNE dass die Hardware verbunden ist:

```bash
python3 simulate.py
```

**Das simuliert:**

- Rover fährt die Route aus `waypoints_test.json` ab
- Nutzt Differential-Drive-Kinematik
- Zeigt Navigation-Entscheidungen in Echtzeit

**Erwartete Ausgabe:**

```
M.A.R.K. Rover - SIMULATION MODE
Loaded 11 waypoints
Total route distance: 45.2m

[  10] State: ROTATING        | Pos: (50.933458, 6.988536) | Heading:  12.3° | Distance:  1.23m
[  20] State: DRIVING         | Pos: (50.933451, 6.988542) | Heading:  15.7° | Distance:  0.89m
...
Waypoint reached! (distance: 0.12m)
MISSION COMPLETE!
```

---

## Teil 5: Live-Test mit echtem Rover

### Vorbereitung

**Hardware-Setup:**

1. ✅ RoboClaw angeschlossen (USB + 12V Netzteil)
2. ✅ GNSS-Modul angeschlossen falls vorhanden
3. ✅ IMU angeschlossen falls vorhanden (I2C)
4. ✅ Rover auf sicherem Testgelände (min. 50m² frei)

**Software-Check:**

```bash
cd ~/rover-steuerung
source venv/bin/activate

# Ports automatisch erkennen
python3 setup_ports.py

# Config überprüfen
cat config.json | grep "address\|motor_controller"
# Sollte zeigen: "roboclaw_address": 131
```

### Main-Programm starten (DRY-RUN ohne GPS)

Wenn du erstmal nur die Motoren testen willst:

```bash
# test_motors.py nutzen (siehe oben)
python3 test_motors.py
```

### Main-Programm mit GPS starten

**Nur wenn GNSS + IMU bereit:**

```bash
# NTRIP-Daemon starten (für RTK)
sudo systemctl start rtk-ntrip.service
sudo systemctl status rtk-ntrip.service
# Sollte "active (running)" zeigen

# Main-Programm starten
python3 main.py
```

**Erwartete Ausgabe:**

```
====================================================
M.A.R.K. Rover Control System - Initialisierung
====================================================
✓ Konfiguration erfolgreich geladen
✓ GNSS verbunden
✓ IMU verbunden  
✓ Motor Controller verbunden
✓ Watchdog aktiv (Timeout: 30s)
====================================================
Starting main loop at 10 Hz
State: IDLE | Pos: 50.933383, 6.988584 | Heading: 245°
```

**Mission starten über API:**

In einem zweiten Terminal:

```bash
curl -X POST http://localhost:5000/api/start
```

Rover sollte jetzt:

1. Zu Waypoint 1 rotieren
2. Losfahren
3. Waypoints sequentiell abarbeiten

**Not-Stopp:**

```bash
curl -X POST http://localhost:5000/api/emergency_stop
```

---

## Troubleshooting

### Problem: "Failed to connect to RoboClaw"

**Lösung 1: Port finden**

```bash
ls /dev/ttyACM*
# Ausgabe z.B.: /dev/ttyACM0  /dev/ttyACM1

# In config.json eintragen:
nano config.json
# "motor_controller": "/dev/ttyACM0"
```

**Lösung 2: Berechtigungen**

```bash
sudo chmod 666 /dev/ttyACM0
# Oder dauerhaft:
sudo usermod -a -G dialout $USER
sudo reboot
```

**Lösung 3: Adresse scannen**

```bash
python3 test_roboclaw_address.py
# Gefundene Adresse in config.json eintragen
```

### Problem: "Battery voltage: None"

**Ursache:** RoboClaw empfängt keine Befehle

**Checkliste:**

- [ ] 12V Netzteil eingeschaltet?
- [ ] Grüne LED am RoboClaw leuchtet?
- [ ] USB-Kabel richtig angeschlossen?
- [ ] Adresse 131 in config.json?
- [ ] Baudrate 38400?

### Problem: Motoren drehen in falsche Richtung

**Test:**

```bash
python3 test_motors.py
# Eingabe: 6 (Spot-Turn LEFT)
```

**Erwartung:** Rover dreht LINKS (gegen Uhrzeigersinn)

**Tatsächlich:** Rover dreht RECHTS oder fährt vorwärts

**Lösung:** M1 und M2 Kabel am RoboClaw vertauschen

---

## Zusammenfassung: Schnell-Installation

```bash
# 1. USB-Stick mounten
cd ~
cp -r /mnt/usb/mark-rover ~/rover-steuerung
cd ~/rover-steuerung

# 2. Python-Umgebung
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Permissions
sudo usermod -a -G dialout $USER
sudo reboot

# 4. Nach Reboot
cd ~/rover-steuerung
source venv/bin/activate

# 5. Motortest
python3 test_motors.py
# Tests 1, 6, 7 durchführen

# 6. Fertig!
```

---

## Nächste Schritte

Nach erfolgreichem Motortest:

1. **GPS-Drift-Optimierung** (siehe `recommendations.md`)
2. **Encoder-Feedback** implementieren
3. **Live-Testfahrt** mit waypoints_test.json

**Viel Erfolg! 🚀**
