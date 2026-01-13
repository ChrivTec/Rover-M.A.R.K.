# 🚀 M.A.R.K. Rover - Quick Start Guide

## Für den ersten Test (HEUTE)

### 1. Simulation auf Windows-PC testen

```bash
cd c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung
python simulate.py
```

**Was passiert:**

- Rover simuliert die Route aus deinem Web-Interface
- Zeigt alle Navigation-Entscheidungen
- Testet ob Tank-Drive-Logic funktioniert

**Erwartete Ausgabe:**

```
Loaded 11 waypoints
Total route distance: 45.2m
[  10] State: ROTATING | Pos: (50.933458, 6.988536) | Heading: 12.3°
...
MISSION COMPLETE!
```

---

### 2. USB-Stick vorbereiten

**Einfach kopieren:**

```
Quelle: C:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung
Ziel:   E:\mark-rover\  (dein USB-Stick)
```

**Wichtig:** Prüfe dass diese Dateien dabei sind:

- ✅ `config.json` (Adresse 131)
- ✅ `motor_module.py` (neue Version)
- ✅ `test_motors.py` (mit Tests 6-10)
- ✅ `waypoints_test.json` (deine Route)

---

## Auf dem Raspberry Pi 5 (MORGEN)

### Schnell-Installation

```bash
# 1. USB-Stick kopieren
cd ~
cp -r /mnt/usb/mark-rover ~/rover-steuerung
cd ~/rover-steuerung

# 2. Python-Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Permissions
sudo usermod -a -G dialout $USER
sudo reboot

# 4. Nach Reboot - Motortest!
cd ~/rover-steuerung
source venv/bin/activate
python3 test_motors.py
```

### Motortest - Die wichtigen Tests

```
Connected to RoboClaw successfully
Battery: 12.0 V  ← Muss angezeigt werden!

Enter command: 1  ← Beide Räder vorwärts
Enter command: s  ← Stopp
Enter command: 6  ← SPOT-TURN LINKS (kritisch!)
Enter command: 7  ← SPOT-TURN RECHTS (kritisch!)
Enter command: q  ← Beenden
```

**Erfolg = Alle 4 Tests funktionieren!**

---

## Dateien-Übersicht

### Neue/Geänderte Dateien (seit gestern)

| Datei | Was ist neu? |
|-------|--------------|
| `config.json` | Adresse 128 → **131** ✅ |
| `motor_module.py` | Motor-Befehle komplett neu ✅ |
| `test_motors.py` | Tests 6-10 hinzugefügt ✅ |
| `waypoints_test.json` | Deine Route konvertiert ✅ |
| `simulate.py` | Navigation ohne Hardware testen ✅ |
| `USB_INSTALLATION.md` | Komplette Anleitung ✅ |

### Wichtige Dokumentation

- **USB_INSTALLATION.md** - Komplette Installations-Anleitung
- **walkthrough.md** - Motortest-Details & Fehlerdiagnose
- **recommendations.md** - Verbesserungsvorschläge (GPS-Drift etc.)

---

## Fragen beantwortet

### ❓ "Ist das Web-Interface schon eingefügt?"

**Nein** - Das Web-Interface ist noch nicht im Projekt vorhanden.

**Was ich gemacht habe:**

- ✅ Deine Route-JSON konvertiert → `waypoints_test.json`
- ✅ Simulation erstellt → `simulate.py` (testet Navigation ohne Hardware)

**Web-Interface kommt später** - Erstmal müssen die Motoren laufen!

### ❓ "Simulation durchlaufen lassen?"

**Ja, kannst du machen:**

```bash
cd c:\Users\Luis\OneDrive\MARK\rover-steuerung07.01.26\rover-steuerung
python simulate.py
```

Das testet die Navigation-Logic mit deiner Route (11 Waypoints, ~45 Meter).

### ❓ "Hast du noch Fragen?"

**Ja, ein paar Klarstellungen:**

1. **Web-Interface:** Soll ich das noch bauen ODER reicht dir erstmal der Motortest?
   - Web-Interface = Flask-App mit Karten-Ansicht, Live-Tracking etc.
   - Motortest = test_motors.py (bereits fertig)

2. **Batterie-Überwachung:** Willst du das jetzt schon oder erst nach GPS-Tests?
   - Aktuell: Nur Spannungs-Anzeige
   - Verbesserung: Automatische Warnung bei Low-Voltage

3. **GPS-Tests:** Hast du das GNSS-Modul (ZED-F9P) bereits am Raspberry Pi angeschlossen?
   - Brauchen wir für morgen (GPS-Drift-Optimierung)

---

## To-Do für HEUTE (Windows PC)

- [ ] Simulation testen: `python simulate.py`
- [ ] USB-Stick vorbereiten (Projekt-Ordner kopieren)
- [ ] USB-Stick-Dateien prüfen (config.json Adresse 131?)

## To-Do für MORGEN (Raspberry Pi)

- [ ] USB-Stick an Raspberry Pi anschließen
- [ ] Projekt kopieren & Python-Setup
- [ ] **Motortest durchführen** (Tests 1, 6, 7)
- [ ] Bei Erfolg: GPS-Modul testen
- [ ] Live-Testfahrt planen

---

## Hilfe gebraucht?

**Vollständige Anleitung:** Siehe `USB_INSTALLATION.md`

**Motortest-Probleme:** Siehe `walkthrough.md` → Abschnitt "Fehlerdiagnose"

**Weitere Ideen:** Siehe `recommendations.md`

**Viel Erfolg! 🎉**
