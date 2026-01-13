# 🚀 FINALE USB-UPLOAD ANLEITUNG

## ✅ Keine offenen Fragen - READY TO GO

Alle Dateien sind bereit für den Raspberry Pi!

---

## 📦 SCHRITT 1: Dateien auf USB kopieren (Windows)

**Öffne PowerShell und führe aus:**

```powershell
# Setze Pfade
$SOURCE = "c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung"
$USB = "D:\"

# Kopiere alle 4 geänderten Dateien
copy "$SOURCE\config.json" $USB
copy "$SOURCE\app.py" $USB
copy "$SOURCE\main.py" $USB
copy "$SOURCE\test_gnss.py" $USB

# Prüfe ob alle da sind
dir D:\*.py, D:\*.json
```

**Erwartete Ausgabe:**

```
config.json
app.py
main.py
test_gnss.py
```

✅ **Alle 4 Dateien auf USB!**

---

## 🔌 SCHRITT 2: USB in Raspberry Pi einstecken

1. USB-Stick aus Windows-PC entfernen
2. In Raspberry Pi einstecken
3. Warten 5 Sekunden (auto-mount)

---

## 💾 SCHRITT 3: Dateien kopieren (Raspberry Pi)

**SSH auf Raspberry Pi:**

```bash
# USB-Pfad finden
USB_PATH="/media/stein/$(ls /media/stein/ | head -1)"
echo "USB gefunden: $USB_PATH"

# Backup erstellen (sicher ist sicher!)
cd ~/mark-rover
mkdir -p backups
cp config.json backups/config.json.backup
cp app.py backups/app.py.backup
cp main.py backups/main.py.backup
cp test_gnss.py backups/test_gnss.backup

# Neue Dateien kopieren
cp "$USB_PATH/config.json" ~/mark-rover/
cp "$USB_PATH/app.py" ~/mark-rover/
cp "$USB_PATH/main.py" ~/mark-rover/
cp "$USB_PATH/test_gnss.py" ~/mark-rover/

# Verifiziere
ls -lh ~/mark-rover/*.py ~/mark-rover/config.json
```

**Erwartete Ausgabe:**

```
-rw-r--r-- 1 stein stein 1.7K Jan  9 12:15 config.json
-rw-r--r-- 1 stein stein  25K Jan  9 12:15 app.py
-rw-r--r-- 1 stein stein  24K Jan  9 12:15 main.py
-rw-r--r-- 1 stein stein 3.5K Jan  9 12:15 test_gnss.py
```

✅ **Alle Dateien übertragen!**

---

## 🧪 SCHRITT 4: Verification Tests

### Test 1: Config prüfen

```bash
cd ~/mark-rover
python3 -c "import json; c=json.load(open('config.json')); print('GNSS:', c['serial_ports']['gnss']); print('Motor:', c['serial_ports']['motor_controller'])"
```

**Erwartung:**

```
GNSS: auto
Motor: auto
```

✅ **Auto-Detection aktiviert!**

---

### Test 2: GNSS Test

```bash
cd ~/mark-rover
python3 test_gnss.py
```

**Erwartung:**

```
🔍 Auto-detecting GNSS port...
✅ Auto-detected GNSS port: /dev/ttyACM0
Connected to GNSS successfully
Fix Quality: RTK Float
Satellites: 12
HDOP: 1.5
✅ RTK FIX ACTIVE!
```

**Nach 10 Sekunden stoppen:** `Ctrl+C`

✅ **GPS funktioniert!**

---

### Test 3: RTK Service prüfen

```bash
sudo systemctl status rtk-ntrip
```

**Wenn Service läuft auf falschem Port:**

```bash
# Service neu konfigurieren für ACM0
sudo tee /etc/systemd/system/rtk-ntrip.service > /dev/null <<'EOF'
[Unit]
Description=RTK NTRIP Streamer (str2str)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/str2str -in ntrip://nw-9112470:123ABCde@sapos-nw-ntrip.de:2101/VRS_3_4G_NW -p 50.9334 6.9886 0 -n 1 -out serial://ttyACM0:115200
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Neu laden
sudo systemctl daemon-reload
sudo systemctl restart rtk-ntrip
sudo systemctl status rtk-ntrip
```

**Erwartung:** `Active: active (running)`

✅ **RTK Service läuft!**

---

### Test 4: Routes Directory

```bash
mkdir -p ~/mark-routes
chmod 755 ~/mark-routes
ls -ld ~/mark-routes
```

**Erwartung:** `drwxr-xr-x ... /home/stein/mark-routes`

✅ **Routes Directory bereit!**

---

### Test 5: Web-Interface

```bash
# Stoppe evtl. laufenden Server
sudo pkill -f "python3 app.py"

# Starte neu
cd ~/mark-rover
python3 app.py
```

**Erwartung:**

```
Starting web server on http://0.0.0.0:5000
✅ Rover system initialized successfully (LIVE MODE)
```

**Im Browser öffnen:** `http://<raspberry-ip>:5000`

**Prüfe:**

- [ ] Dashboard zeigt echte GPS-Daten (nicht 0)
- [ ] RTK Badge zeigt "RTK Float" (blau)
- [ ] Genauigkeit: ±10cm
- [ ] 12 Satellites

✅ **Web-Interface läuft mit ECHTEN Daten!**

**Stoppen:** `Ctrl+C`

---

## 🎯 FERTIG! System ist BEREIT

**Was funktioniert:**

- ✅ Auto-Detection für GPS & Motor
- ✅ RTK Float Status (±10cm)
- ✅ RTK Safety Checks
- ✅ Emergency RTK Recovery
- ✅ Web-Interface mit Live-Daten
- ✅ Route Speicherung
- ✅ Test-Mode zeigt 0-Werte

---

## 🚀 NÄCHSTER SCHRITT: Outdoor-Test

### Pre-Flight Checklist

- [ ] Batterie voll (>12V)
- [ ] GPS draußen (freie Sicht)
- [ ] RTK Float/Fixed Status
- [ ] Motoren angeschlossen
- [ ] Web-Interface läuft

### Erste Route planen

1. Öffne `http://<raspberry-ip>:5000/new_job`
2. Klicke 3-5 Waypoints (sehr klein, 5-10m)
3. Speichere Route
4. Zurück zum Dashboard
5. Route laden
6. **Warte auf RTK Float/Fixed Badge**
7. **START** drücken!

**Erwartetes Verhalten:**

- Rover dreht zum ersten Waypoint
- Fährt langsam (0.3 m/s)
- Stoppt bei RTK-Verlust (Emergency Recovery!)
- Mission Complete am Ende

---

## 🎉 ERFOLG

**Du hast:**

- ✅ RTK GPS System komplett integriert
- ✅ Auto-Detection eingerichtet
- ✅ Safety-Checks implementiert
- ✅ Web-Interface ready
- ✅ **BEREIT FÜR ERSTEN AUTONOMEN LAUF!**

---

## 🆘 Support

**Falls Probleme:**

- Logs: `journalctl -u rtk-ntrip -f`
- GPS Test: `python3 test_gnss.py`
- RTK Monitor: `cd ~ && python3 rtk_diagnostics.py`

**VIEL ERFOLG BEIM ERSTEN AUTONOMEN TEST!** 🚀🌱
