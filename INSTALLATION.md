# 🚀 M.A.R.K. Rover - Schnellinstallation

## Option 1: Automatische Installation (Empfohlen)

### Schritt 1: Code auf Raspberry Pi kopieren
```bash
# Via USB-Stick, Git oder SCP
cd ~
# Entpacke/Clone die Dateien nach ~/rover-steuerung
```

### Schritt 2: Installation starten
```bash
cd ~/rover-steuerung
bash install.sh
```

Das Skript führt automatisch durch:
- ✅ System-Update
- ✅ Dependencies installieren
- ✅ I2C aktivieren  
- ✅ RTKLIB kompilieren
- ✅ Python venv erstellen
- ✅ Python-Packages installieren
- ✅ Berechtigungen setzen
- ✅ Optional: Systemd Services

### Schritt 3: Nach Installation - Neustart
```bash
sudo reboot
```

### Schritt 4: Serial Ports konfigurieren
```bash
cd ~/rover-steuerung
source venv/bin/activate
python3 setup_ports.py
```

Dies erkennt automatisch:
- 🛰️ GPS/GNSS (u-blox ZED-F9P)
- 🤖 Motor Controller (RoboClaw)

Und aktualisiert `config.json` automatisch!

### Schritt 5: Hardware testen
```bash
source venv/bin/activate

# GPS/RTK testen
python3 test_gnss.py

# IMU testen
python3 test_imu.py

# Motoren testen (VORSICHT!)
python3 test_motors.py
```

### Schritt 6: RTK aktivieren
```bash
# RTK/NTRIP Service starten
sudo systemctl start rtk-ntrip.service

# RTK Fix überwachen (sollte nach 5-10 Min auf "RTK Fixed" wechseln)
sudo journalctl -u rtk-ntrip.service -f
```

### Schritt 7: Rover starten
```bash
source venv/bin/activate
python3 main.py
```

---

## Option 2: Manuelle Installation

Siehe `README.md` für detaillierte Schritt-für-Schritt-Anleitung.

---

## 🔧 Troubleshooting

### Problem: "Permission denied" bei Serial Ports
```bash
sudo usermod -aG dialout $USER
# Logout/Login erforderlich!
```

### Problem: I2C Device nicht gefunden
```bash
# I2C aktivieren
sudo raspi-config
# Interface Options → I2C → Enable

# Neustart
sudo reboot

# Scannen
sudo i2cdetect -y 1
# BNO085 sollte bei 0x4A oder 0x4B erscheinen
```

### Problem: RTK Fix nicht erreicht
```bash
# Service-Status prüfen
sudo systemctl status rtk-ntrip.service

# Logs anschauen
sudo journalctl -u rtk-ntrip.service -n 50

# Manuell testen
str2str -in serial://ttyACM1:115200

# NTRIP Credentials in config.json prüfen
```

### Problem: Falsche Serial Ports
```bash
# Automatische Erkennung
python3 setup_ports.py

# ODER manuell in config.json:
{
  "serial_ports": {
    "gnss": "/dev/ttyACM1",              ← Anpassen!
    "motor_controller": "/dev/ttyACM0"   ← Anpassen!
  }
}
```

---

## ✅ Installations-Checkliste

- [ ] `install.sh` ausgeführt
- [ ] Raspberry Pi neugestartet
- [ ] `setup_ports.py` ausgeführt
- [ ] `test_gnss.py` erfolgreich (zeigt GPS-Position)
- [ ] `test_imu.py` erfolgreich (zeigt Heading)
- [ ] `test_motors.py` erfolgreich (Motoren drehen sich)
- [ ] RTK Service läuft (`systemctl status rtk-ntrip.service`)
- [ ] RTK Fixed erreicht (nach 5-10 Min)
- [ ] `waypoints.json` mit eigenen Koordinaten erstellt
- [ ] `main.py` startet ohne Fehler

---

## 📞 Support

Bei Problemen:
1. Logs prüfen: `sudo journalctl -u rover-control.service -n 100`
2. GPS-Status: `python3 test_gnss.py`
3. System-Status: `python3 -c "from main import *; print('OK')"`

Viel Erfolg! 🚀
