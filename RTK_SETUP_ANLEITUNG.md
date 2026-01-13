# RTK GPS Setup - Schritt-für-Schritt Anleitung

## 🎯 Ziel

Das u-blox ZED-F9P GPS-Modul mit RTK (Real-Time Kinematic) Korrekturen über NTRIP zum Laufen bringen für zentimetergenaue Navigation.

---

## ⚠️ Voraussetzungen

- ✅ M.A.R.K. Rover mit Raspberry Pi 5
- ✅ u-blox ZED-F9P GPS-Modul (über USB verbunden)
- ✅ GPS-Antenne mit freier Sicht zum Himmel
- ✅ Internet-Verbindung (für NTRIP Server)
- ✅ SAPOS Niedersachsen Account (bereits in `config.json`)

---

## 📋 Phase 1: Hardware-Check

### Schritt 1.1: USB-Verbindung prüfen

```bash
# Alle USB Serial Devices anzeigen
ls -l /dev/ttyACM* /dev/ttyUSB*

# Erwarte: /dev/ttyACM0 oder /dev/ttyACM1
```

**Erwartetes Ergebnis:**

```
crw-rw---- 1 root dialout 166, 0 Jan  9 10:00 /dev/ttyACM0
```

### Schritt 1.2: GPS-Modul identifizieren

```bash
# u-blox Device finden
lsusb | grep -i "u-blox\|1546"

# Oder:
dmesg | tail -20 | grep tty
```

**Erwartetes Ergebnis:**

```
Bus 001 Device 004: ID 1546:01a9 u-blox AG
```

---

## 📋 Phase 2: RTK Diagnose (OHNE NTRIP)

### Schritt 2.1: Python Dependencies installieren

```bash
cd ~/rover-steuerung07.01.26/rover-steuerung

# Installiere Python Serial Library
pip3 install pyserial
```

### Schritt 2.2: RTK Diagnose-Tool ausführen

```bash
# Auto-Detection (empfohlen)
python3 rtk_diagnostics.py

# Oder: Manuell Port angeben
python3 rtk_diagnostics.py --port /dev/ttyACM0
```

**Erwartetes Ergebnis (nach 30 Sekunden):**

```
🔍 Searching for u-blox GPS module...
✅ Found u-blox at: /dev/ttyACM0
   Description: u-blox GNSS receiver

============================================================
RTK GPS Monitor
============================================================

Port: /dev/ttyACM0
Baudrate: 115200
Duration: infinite

Press Ctrl+C to stop

✅ Connected to GPS module

[10:05:23] Update #1
  Position:   50.9333833°, 6.9885841°
  Altitude:   347.50 m
  Fix Quality: GPS Standard (1)
  Satellites: 8
  HDOP:       1.2
  ⚠️  Waiting for RTK corrections...
```

**✅ Erfolg, wenn:**

- Fix Quality = 1 (GPS Standard)
- Satellites >= 6
- Position ändert sich leicht

**❌ Problem, wenn:**

- Fix Quality = 0 (Invalid)
- Satellites = 0
- Keine Updates

**Lösung bei Problemen:**

- Antenne nach draußen bringen
- 5 Minuten warten (Cold Start)
- Anderen USB-Port testen

---

## 📋 Phase 3: RTKLIB Installation

### Schritt 3.1: RTKLIB kompilieren und installieren

```bash
# Als root ausführen
sudo bash setup_rtklib.sh
```

**Das Script macht:**

1. System Updates installieren
2. Git und Build-Tools installieren
3. RTKLIB von GitHub clonen
4. str2str kompilieren
5. Nach `/usr/local/bin/` installieren

**Dauer:** ~5-10 Minuten

**Erwartetes Ergebnis:**

```
✅ Installation complete!

Verifying installation:
/usr/local/bin/str2str
✅ str2str is installed correctly
```

### Schritt 3.2: GPS Verbindung testen

```bash
# Teste Raw NMEA Output
str2str -in serial://ttyACM0:115200
```

**Erwartetes Ergebnis:**

```
$GNGGA,105234.00,5056.0030,N,00659.3150,E,1,08,1.2,347.5,M,...
$GNRMC,105234.00,A,5056.0030,N,00659.3150,E,0.01,234.5,090126,...
$GNGSA,A,3,29,26,31,18,28,25,05,16,,,,,1.8,1.2,1.4,1*02
...
```

**Stoppe mit:** `Ctrl+C`

---

## 📋 Phase 4: NTRIP Test (Manuell)

### Schritt 4.1: NTRIP Verbindung manuell testen

**⚠️ WICHTIG:** Dieser Test läuft im Vordergrund - öffne dafür ein **separates Terminal!**

```bash
# Terminal 1: NTRIP Streamer starten
str2str -in ntrip://nw-9112470:123ABCde@sapos-nw-ntrip.de:2101/VRS_3_4G_NW \
        -p 50.9334 6.9886 0 \
        -n 1 \
        -out serial://ttyACM0:115200
```

**Erwartetes Ergebnis:**

```
(keine Fehlermeldung = gut!)
```

**Häufige Fehler:**

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| `connection refused` | Keine Internet-Verbindung | WLAN/LAN prüfen |
| `401 Unauthorized` | Falsche Credentials | `config.json` prüfen |
| `timeout` | Firewall blockiert | Port 2101 freigeben |

### Schritt 4.2: RTK Fix überwachen

**In einem ZWEITEN Terminal:**

```bash
# Terminal 2: GPS-Status überwachen
python3 rtk_diagnostics.py --duration 900
```

**Timeline:**

| Zeit | Fix Quality | Status |
|------|-------------|--------|
| 0-2 Min | 1 (GPS) | Normal GPS |
| 2-5 Min | 1 → 5 | NTRIP Daten empfangen, RTK Float |
| 5-15 Min | 5 → 4 | RTK Fixed! 🎉 |

**Erwartetes Ergebnis nach 10-15 Minuten:**

```
[10:18:42] Update #89
  Position:   50.9333834°, 6.9885842°
  Altitude:   347.98 m
  Fix Quality: RTK Fixed (4)
  Satellites: 18
  HDOP:       0.8
  ✅ RTK FIXED - Centimeter accuracy!

🔄 FIX CHANGED: RTK Float → RTK Fixed
```

**✅ Erfolg, wenn:**

- Fix Quality = 4 (RTK Fixed)
- Satellites >= 12
- HDOP < 1.0
- Position stabil (±2cm Varianz)

**⏳ Wenn RTK Float (5) bleibt:**

- **Normal!** RTK Float = ±10cm Genauigkeit (bereits sehr gut)
- Für RTK Fixed: Mehr Zeit warten, Rover **stillhalten**
- Mehr freie Sicht zum Himmel

**Stoppe beide Terminals mit:** `Ctrl+C`

---

## 📋 Phase 5: Systemd Daemon Setup

### Schritt 5.1: Daemon einrichten

```bash
# Als root ausführen
sudo bash setup_rtk_daemon.sh
```

**Das Script macht:**

1. `config.json` lesen
2. systemd Service-File erstellen (`/etc/systemd/system/rtk-ntrip.service`)
3. Service aktivieren (auto-start beim Boot)
4. **Optional:** Service sofort starten

**Erwartetes Ergebnis:**

```
✅ NTRIP Configuration:
   Server: sapos-nw-ntrip.de:2101
   Mountpoint: VRS_3_4G_NW
   Username: nw-9112470
   Reference Position: 50.9334, 6.9886, 0m
   GPS Port: /dev/ttyACM0 @ 115200 baud

Do you want to start the service now? (y/n)
```

**Drücke:** `y` (Yes)

### Schritt 5.2: Service-Status prüfen

```bash
# Status anzeigen
sudo systemctl status rtk-ntrip

# Live-Logs anzeigen
sudo journalctl -u rtk-ntrip -f
```

**Erwartetes Ergebnis:**

```
● rtk-ntrip.service - RTK NTRIP Streamer (str2str)
     Loaded: loaded (/etc/systemd/system/rtk-ntrip.service; enabled)
     Active: active (running) since Thu 2026-01-09 10:25:12 CET
```

---

## 📋 Phase 6: Langzeit-Test

### Schritt 6.1: RTK Fix über Zeit überwachen

```bash
# 60 Minuten Monitoring
python3 rtk_diagnostics.py --duration 3600
```

**Erwartetes Ergebnis:**

- RTK Fixed bleibt stabil
- Keine Connection Losses
- Koordinaten driften nicht ab (±5cm max)

### Schritt 6.2: Integration in main.py testen

```bash
# GNSS-Modul Test
python3 test_gnss.py
```

**Erwartetes Ergebnis:**

```
=============================================================
GNSS Module Test
=============================================================
Connected to GNSS successfully
Reading data... (Press Ctrl+C to stop)

Update #1
  Position: 50.933383, 6.988584
  Altitude: 347.98 m
  Fix Quality: RTK Fixed
  Satellites: 18
  HDOP: 0.8
  Speed: 0.0 km/h
  ✅ RTK FIX ACTIVE!
  Filtered: 50.933383, 6.988584
```

---

## 📋 Phase 7: Outdoor Test Vorbereitung

### Schritt 7.1: Rover Outdoor Test

**Checkliste:**

- [ ] Batterie voll geladen (>12V)
- [ ] WLAN/Mobile Daten verfügbar
- [ ] GPS-Antenne hat freie Sicht
- [ ] str2str Service läuft (`sudo systemctl status rtk-ntrip`)
- [ ] RTK Fixed erreicht (mit `rtk_diagnostics.py` prüfen)

### Schritt 7.2: Erste Route planen und testen

```bash
# Web-Interface starten (auf anderem PC im gleichen Netzwerk)
cd ~/rover-steuerung07.01.26/rover-steuerung
python3 app.py
```

**Öffne im Browser:** `http://<RASPBERRY_PI_IP>:5000`

1. Klicke auf "New Job"
2. Plane eine kleine Test-Route (3-5 Waypoints, max 10m)
3. Speichere Route
4. **WICHTIG:** Warte auf RTK Fixed bevor du startest!

---

## 🔧 Troubleshooting

### Problem: Kein GPS Fix

**Symptom:** Fix Quality bleibt bei 0

**Checkliste:**

1. Antenne korrekt angeschlossen?
2. Antenne hat Sicht zum Himmel?
3. 5 Minuten gewartet? (Cold Start)
4. `dmesg | grep tty` zeigt USB-Device?

### Problem: GPS Fix, aber kein RTK

**Symptom:** Fix Quality = 1, bleibt nicht bei 4/5

**Checkliste:**

1. str2str Service läuft? `sudo systemctl status rtk-ntrip`
2. Internet-Verbindung? `ping sapos-nw-ntrip.de`
3. NTRIP Logs prüfen: `sudo journalctl -u rtk-ntrip -n 50`
4. Genug Satelliten? (>= 8 benötigt)
5. 15 Minuten gewartet?

### Problem: RTK Fix wird immer wieder verloren

**Symptom:** Fix wechselt zwischen 4 → 5 → 1

**Mögliche Ursachen:**

- Bäume/Gebäude blockieren Satelliten
- Mobile Daten instabil (str2str verliert Verbindung)
- Batterie-Spannung zu niedrig (<11V)
- Rover bewegt sich zu schnell

**Lösung:**

- Offenere Umgebung wählen
- Mobile Daten Signal prüfen
- Batterie laden
- Langsamer fahren (max 0.3 m/s)

---

## ✅ Erfolgskriterien

Nach erfolgreichem Setup solltest du haben:

| Kriterium | Wert | Status |
|-----------|------|--------|
| GPS Fix Quality | 4 (RTK Fixed) | ⬜ |
| Satelliten | >= 12 | ⬜ |
| HDOP | < 1.0 | ⬜ |
| Positionsgenauigkeit | ±2cm | ⬜ |
| Update-Rate | 10 Hz | ⬜ |
| systemd Service | Running & Enabled | ⬜ |
| Connection Stability | > 60 Min ohne Loss | ⬜ |

---

## 📞 Nächste Schritte

1. **Heute:** RTK Fixed erreichen
2. **Heute:** Erste kleine Test-Route outdoor fahren (3-5m)
3. **Morgen:** Längere Route testen (10-20m)
4. **Diese Woche:** Vollständige autonome Garten-Route

---

## 🚀 Bereit für den Outdoor Test

Wenn alle Kriterien erfüllt sind, kann dein M.A.R.K. Rover seine erste autonome Route fahren! 🎉

**Du hast Fragen während des Setups? Frag einfach!**
