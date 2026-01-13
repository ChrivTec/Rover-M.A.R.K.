# Upload & Test-Anleitung - M.A.R.K. Rover RTK Integration

## 🎯 Ziel

Aktualisierte Dateien auf den Raspberry Pi übertragen und ersten Outdoor-Test mit RTK durchführen.

---

## 📦 Zu übertragende Dateien

### Geänderte Dateien

1. ✅ `config.json` - Serial Ports korrigiert + RTK Safety
2. ✅ `app.py` - RTK Status, simulierte Werte = 0
3. ✅ `main.py` - Emergency RTK Recovery

---

## 🚀 Methode 1: Git Pull (Empfohlen, wenn Git eingerichtet)

### Auf Windows PC

```bash
cd c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung

git status
git add config.json app.py main.py
git commit -m "RTK Integration: Serial Ports, Safety Checks, Emergency Recovery"
git push
```

### Auf Raspberry Pi

```bash
cd ~/mark-rover
git pull

# Prüfe ob Dateien aktualisiert wurden
git status
git log -1
```

---

## 🚀 Methode 2: SCP (Direkte Übertragung)

### Von Windows PowerShell

```powershell
# Setze Pfade
$LOCAL = "c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung"
$REMOTE = "stein@raspberrypi:~/mark-rover/"

# Übertrage Dateien
scp "$LOCAL\config.json" $REMOTE
scp "$LOCAL\app.py" $REMOTE
scp "$LOCAL\main.py" $REMOTE

# Verifiziere
ssh stein@raspberrypi "cd ~/mark-rover && ls -lh config.json app.py main.py"
```

---

## 🚀 Methode 3: USB-Stick (Offline-Methode)

### 1. Dateien auf USB kopieren (Windows)

```powershell
# USB Stick = D:\
copy c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung\config.json D:\
copy c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung\app.py D:\
copy c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung\main.py D:\
```

### 2. USB in Raspberry Pi einstecken

### 3. Dateien kopieren (Raspberry Pi)

```bash
# USB mountet automatisch unter /media/stein/
USB_PATH="/media/stein/$(ls /media/stein/ | head -1)"

# Kopiere Dateien
cp "$USB_PATH/config.json" ~/mark-rover/
cp "$USB_PATH/app.py" ~/mark-rover/
cp "$USB_PATH/main.py" ~/mark-rover/

# Verifiziere
ls -lh ~/mark-rover/config.json ~/mark-rover/app.py ~/mark-rover/main.py
```

---

## ✅ Verification Tests (auf Raspberry Pi)

### Test 1: Config Validierung

```bash
cd ~/mark-rover

# Prüfe Serial Ports
python3 -c "import json; config=json.load(open('config.json')); print('GNSS:', config['serial_ports']['gnss']); print('Motor:', config['serial_ports']['motor_controller'])"
```

**Erwartete Ausgabe:**

```
GNSS: /dev/ttyACM1
Motor: /dev/ttyACM0
```

---

### Test 2: Routes Directory erstellen

```bash
# Erstelle Routes Verzeichnis
mkdir -p ~/mark-routes
chmod 755 ~/mark-routes

# Verifiziere
ls -ld ~/mark-routes
```

**Erwartete Ausgabe:**

```
drwxr-xr-x 2 stein stein 4096 Jan  9 10:50 /home/stein/mark-routes
```

---

### Test 3: GNSS Test

```bash
cd ~/mark-rover
python3 test_gnss.py
```

**Erwartete Ausgabe:**

```
Fix Quality: RTK Float (oder RTK Fixed)
Satellites: 12
HDOP: 1.2
✅ RTK FIX ACTIVE!
```

**Stoppen:** `Ctrl+C`

---

### Test 4: RTK Service Status

```bash
# Prüfe ob RTK NTRIP Service läuft
sudo systemctl status rtk-ntrip

# Live-Logs (optional)
sudo journalctl -u rtk-ntrip -f
```

**Erwartete Ausgabe:**

```
● rtk-ntrip.service - RTK NTRIP Streamer (str2str)
     Active: active (running) since ...
```

---

### Test 5: Web-Interface Start

```bash
cd ~/mark-rover
python3 app.py
```

**Erwartete Ausgabe:**

```
Starting web server on http://0.0.0.0:5000
```

**Im Browser öffnen:** `http://<raspberry-ip>:5000`

**Prüfe:**

- [ ] Dashboard zeigt "Test Mode" (simulierte Werte = 0, rot markiert)
- [ ] Kein Hardware verbunden → Erwartungsgemäß

**Stoppen:** `Ctrl+C`

---

## 🎯 Outdoor-Test Vorbereitung

### Checkliste VOR dem Test

- [ ] Batterie voll geladen (>12V)
- [ ] Alle USB-Kabel verbunden:
  - GPS auf `/dev/ttyACM1`
  - Motor Controller auf `/dev/ttyACM0`
- [ ] RTK Service läuft (`systemctl status rtk-ntrip`)
- [ ] GPS hat RTK Float oder Fixed (`python3 rtk_diagnostics.py`)
- [ ] Rover ist draußen (freie Sicht zum Himmel)

---

### Test 6: Hardware-Test (mit Motoren)

⚠️ **VORSICHT:** Rover hebt ab!

```bash
cd ~/mark-rover

# Motor Test (sehr kurz)
python3 test_motors.py
```

**Erwartete Ausgabe:**

```
Connected to Motor Controller
Battery: 12.4V
Testing motors... (Press Ctrl+C to stop)
```

**Motoren sollten kurz drehen!**

**Stoppen:** `Ctrl+C`

---

### Test 7: Integration Test (Optional)

```bash
cd ~/mark-rover

# Starte Web-Interface im Live-Mode
python3 app.py
```

**Im Browser:** `http://<raspberry-ip>:5000`

**Prüfe:**

- [ ] Dashboard zeigt echte Werte (nicht 0)
- [ ] GPS zeigt RTK Float/Fixed Status
- [ ] RTK Badge ist blau (Float) oder grün (Fixed)
- [ ] Genauigkeit: ±10cm oder ±2cm
- [ ] Satellites: ~12
- [ ] Battery Voltage: ~12V

---

## 🗺️ Erste Route planen

### 1. Route-Editor öffnen

**Im Browser:** `http://<raspberry-ip>:5000/new_job`

### 2. Route erstellen

1. **Klicke auf Karte** um Waypoints zu setzen
2. **3-5 Waypoints** in kleinem Bereich (5-10m)
3. **Namen geben:** "Test Route 1"
4. **Speichern** klicken

**Prüfe:**

- Route wird in `~/mark-routes/` gespeichert
- Keine Permission Errors

### 3. Route laden

**Zurück zum Dashboard:** `http://<raspberry-ip>:5000`

1. **Klicke "Load Route"**
2. **Wähle "Test Route 1"**
3. **Prüfe RTK Status:** Sollte RTK Float/Fixed sein
4. **NOCH NICHT STARTEN!** (Erst bei echtem Outdoor-Test)

---

## 🚀 Erster Autonomer Test (Outdoor)

### Vorbereitung

1. **Rover outdoor aufstellen**
2. **Web-Interface öffnen**
3. **Warten bis RTK Float/Fixed** (kann 2-15 Min dauern)
4. **Route geladen** (siehe oben)

### Test durchführen

1. **Stelle dich neben den Rover** (für Emergency Stop)
2. **Klicke "START" im Web-Interface**

**Erwartetes Verhalten:**

- Rover dreht sich zum ersten Waypoint
- Fährt langsam los (max 0.3 m/s)
- Folgt der geplanten Route
- Stoppt bei jedem Waypoint kurz
- Mission Complete nach letztem Waypoint

**Bei Problemen:**

- **Emergency Stop** Taste drücken (rotes Icon)
- Oder: `Ctrl+C` im Terminal
- Rover stoppt sofort

---

## 📊 Nach dem Test

### Logs prüfen

```bash
# Letzte Logs anschauen
journalctl -u rtk-ntrip -n 100

# App Logs (wenn im Terminal gestartet)
# Sind bereits sichtbar
```

### Probleme dokumentieren

- RTK Status während Fahrt?
- Waypoint-Genauigkeit?
- Geschwindigkeit OK?
- Kurvenverhalten?

---

## 🎉 Erfolgs-Metriken

**Test gilt als erfolgreich wenn:**

- [x] GPS zeigt RTK Float oder Fixed
- [ ] Rover fährt alle Waypoints ab
- [ ] Genauigkeit: Stoppt innerhalb 30cm vom Waypoint
- [ ] Keine Emergency Stops durch RTK Verlust
- [ ] Rover folgt grob der geplanten Linie

---

## ⚠️ Troubleshooting

| Problem | Lösung |
|---------|--------|
| `Permission denied` beim Speichern | `chmod 755 ~/mark-routes` |
| GPS zeigt nur GPS Fix | Warten auf RTK (5-15 Min) |
| Start verweigert | Prüfe RTK Status (muss Float/Fixed sein) |
| Motor dreht nicht | Port vertauscht? Test mit `test_motors.py` |
| RTK verloren während Fahrt | Normal in Innenräumen - Outdoor testen |

---

## 📝 Nächste Schritte

**Nach erfolgreichem Test:**

1. ✅ Längere Route testen (20-50m)
2. ✅ PID-Parameter tunen für besseres Line-Following
3. ✅ Verschiedene Geschwindigkeiten testen
4. ✅ RTK Fixed erreichen (länger warten)

**→ Produktiv-Einsatz im Garten bereit!** 🌱

---

## 🆘 Support

**Wenn etwas nicht funktioniert:**

- Logs speichern und schicken
- Screenshots vom Web-Interface
- Beschreibung was genau nicht geht

**Viel Erfolg beim ersten autonomen Lauf!** 🚀
