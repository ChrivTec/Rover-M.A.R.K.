# 🧪 M.A.R.K. Rover - Testing Guide

Komplette Anleitung für Indoor- und Outdoor-Tests mit der Web-App.

---

## Indoor-Tests (HEUTE - Ohne GPS)

### Vorbereitung

**Hardware:**

- [x] RoboClaw 2x15A (Adresse 131, 38400 Baud)
- [x] 12V Netzteil für Motoren angeschlossen
- [x] USB-Kabel RoboClaw → PC/Raspberry Pi
- [x] Rover auf Böcke stellen (Räder frei drehen)

**Software:**

```bash
cd c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung
# Oder auf Raspberry Pi:
cd ~/rover-steuerung
```

---

### Test 1: Web Interface starten

#### Windows

```bash
python app.py
```

#### Raspberry Pi

```bash
source venv/bin/activate
python3 app.py
# Oder:
./start_webui.sh
```

**Erwartete Ausgabe:**

```
==================================================
M.A.R.K. Rover - Web Interface
==================================================
⚠ Could not initialize rover system (hardware not available)
✓ Running in TEST MODE (simulated data)
Starting web server on http://0.0.0.0:5000
Press Ctrl+C to stop
==================================================
 * Running on all addresses
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.1.XX:5000
```

**✅ Erfolg wenn:**

- Server startet ohne Fehler
- URL wird angezeigt

---

### Test 2: Browser öffnen und UI prüfen

1. **Browser öffnen:** `http://localhost:5000`

2. **Oberfläche sollte zeigen:**
   - ✅ Leaflet-Karte (OpenStreetMap)
   - ✅ Rechtes Panel mit:
     - 🔴 NOTAUS-Button (rot)
     - ▶️ Start/Stop Buttons
     - 🧭 Kompass mit Nordpfeil
     - ⚡ Telemetrie Dashboard
     - 🗺️ Routen-Manager
   - ✅ Header mit:
     - Toggle "Test-Modus / Live-Modus"
     - Status-Icons (GPS, Internet, Rover)

3. **Test-Modus aktivieren:**
   - Toggle oben rechts auf "Test-Modus" schalten
   - Icons sollten grau/simuliert zeigen

**Screenshots für Verifikation:**

![Web UI Beispiel - Route Planner]

---

### Test 3: Route planen (Simuliert)

1. **Waypoints setzen:**
   - Auf Karte klicken → Waypoint 1 erscheint
   - Weitere Klicks → Waypoint 2, 3, ...
   - Mindestens 3 Waypoints setzen

2. **Route speichern:**
   - Routenname eingeben: `indoor-test`
   - "Route speichern" klicken
   - Toast-Nachricht: "Route gespeichert: indoor-test_13-45_07-01-2026.json"

3. **Route laden:**
   - "Route laden" klicken
   - Gespeicherte Routen werden angezeigt
   - Auf Route klicken → Waypoints werden auf Karte geladen

**✅ Erfolg wenn:**

- Waypoints auf Karte sichtbar
- Blaue gestrichelte Linie verbindet Waypoints
- Route wird in `routes/` Ordner gespeichert

---

### Test 4: Telemetrie-Anzeige (Test-Modus)

Im **Test-Modus** zeigt die Telemetrie simulierte Werte:

| Parameter | Erwarteter Wert | Beschreibung |
|-----------|-----------------|--------------|
| Spannung | ~12.2 V | Simulierte Batteriespannung |
| Strom | 0.0 A | Keine Motoren aktiv |
| Leistung | 0.0 W | Berechnet: V × A |
| Position | 50.933xxx, 6.988xxx | NTRIP Referenzpunkt |
| Satelliten | 18 | Simuliert - RTK Fixed |
| HDOP | 0.8 | Simuliert - Exzellent |
| Heading | 245° | Simuliert |
| CTE | 0.00 m | Cross-Track Error |

**Kompass:**

- Pfeil zeigt ~245° (Südwest)
- Heading-Wert unter Kompass: `245.0°`

**Status-Icons:**

- 🛰️ GPS: Grün, "RTK Fixed"  
- 📡 Internet: Blau, "GOOD"
- 🤖 Rover: Grau, "IDLE"

**✅ Erfolg wenn:**

- Alle Werte aktualisieren sich (live polling 1x/s)
- Kompass dreht sich sanft bei Heading-Änderung

---

### Test 5: Motortest mit echter Telemetrie

**Setup:**

1. RoboClaw am PC/Raspberry Pi anschließen
2. 12V Netzteil EINSCHALTEN
3. **Toggle auf "Live-Modus"** schalten
4. Web Interface sollte jetzt echte Werte vom RoboClaw lesen

**Terminal 2 öffnen:**

```bash
cd c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung
python test_motors.py
```

**Motortest durchführen:**

```
Enter command: 1   # Beide Räder vorwärts (2s)
```

**Erwartung in Web UI während Test 1:**

- ⚡ **Strom** steigt: 0.0A → 0.5-2.0A
- ⚡ **Leistung** steigt: 0.0W → 6-24W
- ⚡ **Spannung** bleibt ~12V

**Weitere Tests:**

```
Enter command: s   # Stopp
Enter command: 6   # Spot-Turn Links
Enter command: 7   # Spot-Turn Rechts
Enter command: q   # Beenden
```

**✅ Erfolg wenn:**

- Telemetrie reagiert auf Motorkommandos
- Stromwerte plausibel (0.5-3.0A pro Motor)
- Leistung = Voltage × Current

---

### Test 6: Emergency Stop (Tastatur)

1. **Web Interface im Fokus** (Browser-Tab aktiv)
2. **ESC** drücken
3. **ODER Leertaste** drücken

**Erwartung:**

- Emergency Stop wird ausgelöst (API Call)
- Im Test-Modus: Keine echte Aktion
- Im Live-Modus: Motoren stoppen sofort

**✅ Erfolg wenn:**

- Emergency Stop Button "blinkt" kurz dunkel
- Console Log: "Emergency stop: {status: 'emergency'}"

---  

### Test 7: Route Export/Import

1. **Route setzen** (3 Waypoints)
2. **"Route speichern"** klicken
3. **Browser DevTools öffnen** (F12)
4. **Network-Tab:**
   - `POST /api/route/upload`
   - Response: `{status: 'saved', filename: '...'}`

5. **Datei überprüfen:**

```bash
cat routes/indoor-test_*.json
```

Sollte zeigen:

```json
{
  "name": "indoor-test",
  "waypoints": [
    {"lat": 50.933xxx, "lon": 6.988xxx, "speed_ms": 0.3, "stop_duration_s": 0},
    ...
  ]
}
```

**✅ Erfolg wenn:**

- JSON-Datei korrekt formatiert
- Waypoints mit Lat/Lon vorhanden

---

## Outdoor-Tests (MORGEN - Mit GPS)

### Vorbereitung

**Hardware:**

- [x] Alle Indoor-Hardware
- [x] GNSS-Modul (ZED-F9P) angeschlossen
- [x] IMU (BNO085) angeschlossen
- [x] NTRIP-Verbindung aktiv (RTK)
- [x] Rover auf freiem Gelände (min. 50m² frei)

**NTRIP-Daemon starten:**

```bash
sudo systemctl start rtk-ntrip.service
sudo systemctl status rtk-ntrip.service
# Sollte "active (running)" zeigen
```

---

### Test 8: GPS-Fix bestätigen

1. **Web Interface öffnen:** `http://raspberrypi.local:5000`
2. **Live-Modus aktivieren**
3. **GPS-Status Icon** prüfen:

| Status | Icon-Farbe | Fix Quality | HDOP | Aktion |
|--------|-----------|-------------|------|--------|
| ✅ Excellent | Grün | RTK Fixed | < 2.0 | Bereit! |
| ⚠️ Good | Blau | RTK Float | < 5.0 | 2-3 Min warten |
| ⚠️ Fair | Gelb | Standard GPS | < 10.0 | Warten oder Position wechseln |
| ❌ Poor | Rot | No Fix | > 10.0 | Position prüfen! |

**Telemetrie prüfen:**

- **Satelliten:** > 10 (besser > 15)
- **HDOP:** < 2.0
- **Position:** Realistische Koordinaten (nicht 0,0)

**Karte:**

- Rover-Marker (roter Punkt) sollte auf aktueller Position erscheinen
- Karte sollte automatisch auf Rover zentrieren

**✅ Erfolg wenn:**

- GPS-Icon grün, "RTK Fixed"
- Rover-Position auf Karte sichtbar
- Kompass zeigt aktuelle Richtung

---

### Test 9: Kurze Testroute (5-10m)

**Route planen:**

1. Auf Karte 2 Waypoints setzen:
   - Waypoint 1: 5m geradeaus
   - Waypoint 2: 5m versetzt (rechts/links)

2. Routenname: `outdoor-test-short`
3. "Start Mission" klicken

**Erwartetes Verhalten:**

| Phase | Rover-Aktion | UI-Anzeige | Dauer |
|-------|-------------|------------|-------|
| 1. Rotation | Dreht sich zu WP1 | State: ROTATING | 2-5s |
| 2. Fahrt | Fährt geradeaus | State: DRIVING | 10-20s |
| 3. WP erreicht | SStoppt kurz | State: REACHED_WAYPOINT | 1s |  
| 4. Neue Rotation | Dreht zu WP2 | State: ROTATING | 2-5s |
| 5. Fahrt | Fährt zu WP2 | State: DRIVING | 10-20s |
| 6. Fertig | Stoppt | State: MISSION_COMPLETE | - |

**Während der Fahrt beobachten:**

- **Rover-Marker** bewegt sich live auf Karte
- **CTE** (Cross-Track Error) sollte klein bleiben (< 0.3m)
- **Heading** ändert sich während Rotation
- **Waypoint:** Updates "1/2" → "2/2"

**✅ Erfolg wenn:**

- Rover erreicht beide Waypoints
- CTE bleibt < 0.5m (gute Linienfolge)
- Live-Position auf Karte korrekt

---

### Test 10: GPS-Drift beobachten

**Szenario:**  Rover fährt bei leichtem Wind oder auf unebenem Boden → GPS-Drift möglich

1. **Lange Gerade Strecke** planen (15-20m)
2. "Start Mission" klicken
3. **In Web UI beobachten:**

**Telemetrie:**

- **CTE:** Sollte zwischen -0.2m und +0.2m oszillieren
- Wenn CTE > 1.0m → **Drift Alert** wird geloggt

**Adaptive PID:**

- GPS-Icon-Farbe ändert sich basierend auf HDOP/Fix Quality
- Bei schlechterem GPS: Geringere PID-Gains (sanfteres Steuern)
- Console Log zeigt:

  ```
  Adaptive PID: GPS quality = good, gain multiplier = 0.75
  ```

**Cross-Track-Error Visualisierung:**

- Wert sollte sichtbar sein in Telemetrie-Dashboard
- Bei > 0.5m: Rover korrigiert aktiv (Li/Re Räder unterschiedlich schnell)

**✅ Erfolg wenn:**

- CTE bleibt unter 0 5-1.0m
- Rover korrigiert aktiv bei Drift
- Adaptive PID passt sich an GPS-Qualität an

---

### Test 11: PID Auto-Tune

**Voraussetzungen:**

- GPS RTK Fixed
- Freie gerade Strecke (30-50m)
- Rover bereit

**Durchführung:**

1. **PID Auto-Tune** Sektion in UI aufklappen
2. **"Tuning starten"** klicken
3. **Rover fährt Test-Muster:**
   - Oszilliert um Ideallinie (Relay-Feedback Methode)
   - 2-3 Minuten Testfahrt
4. **Analyse läuft automatisch**
5. **Ergebnis:**
   - Neue Kp, Ki, Kd Werte werden vorgeschlagen
   - "Parameter übernehmen" Button wird aktiv

6. **"Parameter übernehmen"** klicken
   - Werte werden in `config.json` gespeichert
   - Rover nutzt neue PID-Parameter

**Erwartete Werte (Beispiel):**

```
Ultimate Period Tu = 2.5s
Ultimate Gain Ku = 3.2
Tuned Kp = 1.92
Tuned Ki = 0.96
Tuned Kd = 0.24
```

**✅ Erfolg wenn:**

- Tuning läuft ohne Fehler
- Neue Parameter plausibel (Kp: 1-5, Ki: 0.1-2, Kd: 0.1-1)
- Nach Übernahme: Verbesserte Linienfolge

---

## Fehlerdiagnose

### Problem: Web UI zeigt "OFFLINE"

**Ursache:** Flask-Server läuft nicht oder Hardware nicht verbunden

**Lösung:**

1. Terminal prüfen ob `app.py` läuft
2. Wenn Test-Modus: Normal (keine echte Hardware)
3. Wenn Live-Modus: RoboClaw-Verbindung prüfen

### Problem: GPS-Icon bleibt grau

**Ursache:** Kein GPS-Fix

**Lösung:**

1. NTRIP-Daemon Status prüfen: `sudo systemctl status rtk-ntrip`
2. GNSS-Modul Log prüfen: `python3 test_gnss.py`
3. Warten (kann 2-10 Min dauern für RTK Fixed)
4. Position ändern (freiere Sicht zum Himmel)

### Problem: CTE sehr hoch (> 2m)

**Ursache:** GPS-Drift, Wind, oder falsche PID-Parameter

**Lösung:**

1. GPS-Qualität prüfen (HDOP < 2.0?)
2. PID Auto-Tune durchführen
3. `drift_alert_threshold` in `navigator.py` anpassen

### Problem: Rover fährt im Kreis statt geradeaus

**Ursache:** Motoren vertauscht oder falsche Parameter

**Lösung:**

1. Motortest durchführen: Test 6 & 7
2. Wenn Spot-Turn falsch: M1/M2 Kabel vertauschen
3. wheelbase_m in `config.json` prüfen

---

## Nächste Schritte nach erfolgreichen Tests

1. ✅ **Indoor-Tests abgeschlossen** → Rover ist bereit für Outdoor
2. ✅ **Outdoor GPS-Test erfolgreich** → PID Tuning durchführen
3. ✅ **PID optimiert** → Lange Testroute fahren (waypoints_test.json)
4. ✅ **Alles funktioniert** → Systemd Service einrichten (Auto-Start beim Booten)

**Viel Erfolg! 🚀**
