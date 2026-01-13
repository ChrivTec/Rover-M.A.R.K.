# 🤖 M.A.R.K. Rover - Mechanischer Aufbau & Koordinatensystem

## 📐 Rover-Abmessungen

```
Radabstand (Wheelbase):  396.503 mm
Rad-Durchmesser:         79 mm
Max RPM:                 60

Komponenten-Offsets (vom Rover-Mittelpunkt):
- GPS Antenne:  X=0mm,  Y=-340.000mm,  Z=-196.268mm
- IMU (BNO085): X=0mm,  Y=-292.235mm,  Z=-193.750mm
```

---

## 🎨 Draufsicht (von oben)

```
         VORNE (Fahrrichtung →)
              ↑ +Y
              │
    ┌─────────┼─────────┐
    │         │         │
    │         │         │
    │    ┌────⊕────┐    │  ← Rover-Mittelpunkt (0, 0, 0)
    │    │ Raspberry│    │
    │    │   Pi 5   │    │
    │    └──────────┘    │
    │         │         │
 ◄──┤ M1      │      M2 ├──► X-Achse
-X  │ Links   │   Rechts│  +X
    │ Motor   │    Motor│
    │         │         │
    │    [🧭 IMU]      │  ← Y = -292.235mm (hinten!)
    │         │         │
    │   [📡 GPS Antenne]│  ← Y = -340.000mm (ganz hinten!)
    │         │         │
    └─────────┼─────────┘
              │
              ↓ -Y
           HINTEN

Legende:
⊕ = Rover-Mittelpunkt (Koordinatenursprung)
🧭 = IMU BNO085
📡 = GPS Antenne u-blox ZED-F9P
M1 = Linker Motor (RoboClaw M1)
M2 = Rechter Motor (RoboClaw M2)
```

**Radposition:**
- **Links (M1)**:  X = -198.252mm (halber Wheelbase)
- **Rechts (M2)**: X = +198.252mm (halber Wheelbase)

---

## 🔧 Seitenansicht (von links)

```
         GPS Antenne
              📡
              ││  ← Z = -196.268mm (unter Mittelpunkt)
              ││
         ┌────┴┴────┐
         │          │
    ─────┤ Raspberry├───── ← Z = 0 (Rover-Mittelpunkt Höhe)
         │   Pi 5   │
         │          │
         │  🧭 IMU  │ ← Z = -193.750mm
         └──────────┘
              ││
         ════╬╬════    ← Räder (Boden)
            Wheel
```

---

## 📊 Koordinatensystem

### **Achsen-Definition:**
```
X-Achse: Links (-) ←→ Rechts (+)
Y-Achse: Hinten (-) ←→ Vorne (+)
Z-Achse: Unten (-) ←→ Oben (+)
```

### **Rover-Mittelpunkt (0, 0, 0):**
- Zwischen den beiden Rädern (horizontal)
- Auf Höhe der Raspberry Pi Hauptplatine
- Referenzpunkt für alle Messungen

---

## 🎯 Warum sind IMU & GPS hinten?

### **GPS Antenne (Y = -340mm, hinten):**
✅ **Freie Sicht zum Himmel** - Keine Hindernisse nach oben
✅ **Weg von Motoren** - Weniger elektrische Störungen
✅ **Stabiler Mount** - Am hinteren Ende des Chassis

### **IMU (Y = -292mm, hinten):**
✅ **Näher am Schwerpunkt** - Bessere Orientierungsmessung
✅ **Geschützt** - Im Gehäuse nahe am Pi
✅ **Kurze I2C-Kabel** - Raspberry Pi ist auch hinten

---

## 🧮 Offset-Korrektur in der Navigation

### **Problem:** 
GPS misst Position der **Antenne**, nicht des Rover-Mittelpunkts!

### **Lösung:**
Berechne Rover-Mittelpunkt aus GPS + Heading:

```python
# gnss_module.py - get_position_with_offset_correction()

# GPS gibt Position der Antenne:
gps_lat, gps_lon = (50.9333833, 6.9885841)

# Antenne ist 340mm HINTEN (-Y):
offset_y = -0.340  # Meter

# Rover zeigt nach Norden (0°):
heading = 0.0

# Berechne Verschiebung in Nord/Ost:
# Wenn Rover nach Norden zeigt:
#   - Antenne ist 340mm SÜDLICH vom Mittelpunkt
#   - Also Mittelpunkt ist 340mm NÖRDLICH der Antenne

north_offset = -offset_y * cos(heading)
             = -(-0.340) * cos(0°)
             = +0.340 * 1.0
             = +0.340m NORD

east_offset = -offset_y * sin(heading)
            = -(-0.340) * sin(0°)
            = 0.0

# Rover-Mittelpunkt:
rover_lat = gps_lat + (0.340m / 111111m)
rover_lon = gps_lon + 0.0
```

### **Beispiele verschiedener Headings:**

| Heading | Richtung | GPS Antenne | Rover-Mittelpunkt |
|---------|----------|-------------|-------------------|
| 0° | Nord ↑ | (50.9333833, 6.9885841) | **340mm nördlich** der Antenne |
| 90° | Ost → | (50.9333833, 6.9885841) | **340mm östlich** der Antenne |
| 180° | Süd ↓ | (50.9333833, 6.9885841) | **340mm südlich** der Antenne |
| 270° | West ← | (50.9333833, 6.9885841) | **340mm westlich** der Antenne |

**Die Korrektur rotiert automatisch mit dem Rover!** ✅

---

## 🚗 Radkonfiguration - Differential Drive

### **2-Rad Antrieb:**
```
      Vorne
        ↑
        │
    ┌───────┐
    │       │
M1══╣       ╠══M2
Links       Rechts
    │       │
    └───────┘
```

### **Motor-Zuordnung:**
- **M1 (Links)**: RoboClaw Motor 1, X = -198.252mm
- **M2 (Rechts)**: RoboClaw Motor 2, X = +198.252mm

### **Antriebsarten:**

#### **Geradeaus:**
```
M1: +0.3 m/s ═══►
M2: +0.3 m/s ═══►
→ Rover fährt geradeaus
```

#### **Tank-Rotation Links (CCW):**
```
M1: -0.2 m/s ◄═══  (rückwärts)
M2: +0.2 m/s ═══►  (vorwärts)
→ Rover dreht gegen Uhrzeigersinn um Mittelpunkt ⊕
```

#### **Tank-Rotation Rechts (CW):**
```
M1: +0.2 m/s ═══►  (vorwärts)
M2: -0.2 m/s ◄═══  (rückwärts)
→ Rover dreht im Uhrzeigersinn um Mittelpunkt ⊕
```

#### **Bogen Links (Line-Following):**
```
M1: +0.27 m/s ════►  (langsamer)
M2: +0.33 m/s ══════►  (schneller)
→ Rover fährt Linkskurve
```

---

## 📏 Wichtige Maße

| Parameter | Wert | Bedeutung |
|-----------|------|-----------|
| **Wheelbase** | 396.503 mm | Abstand zwischen linkem und rechtem Rad |
| **Rad-Durchmesser** | 79 mm | Wheel diameter |
| **Rad-Umfang** | 248.1 mm | π × 79mm |
| **Max Speed** | 0.247 m/s | Bei 60 RPM = (60/60) × π × 0.079 |
| **GPS → Mitte** | 340 mm | Antenne ist hinten montiert |
| **IMU → Mitte** | 292.235 mm | BNO085 ist hinten montiert |

---

## 🎯 Sensor-Positionen im Detail

### **GPS Antenne:**
```
Position: (0, -340, -196.268) mm
         │   │     └─ 196mm unter Rover-Mitte
         │   └─ 340mm hinter Rover-Mitte  
         └─ Auf Mittellinie (zentriert)

Bedeutung:
✓ Mittig zwischen den Rädern
✓ Am hinteren Ende des Rovers
✓ Höher als der Boden (für freie Sicht)
```

### **IMU (BNO085):**
```
Position: (0, -292.235, -193.750) mm
         │   │          └─ 194mm unter Rover-Mitte
         │   └─ 292mm hinter Rover-Mitte
         └─ Auf Mittellinie

Bedeutung:
✓ Näher am Rover-Mittelpunkt als GPS
✓ Noch hinten, aber 48mm vor der GPS-Antenne
✓ Fast auf gleicher Höhe wie GPS
```

---

## ✅ Zusammenfassung

**Radkonfiguration:** ✅ Klar!
- 2 Räder, differential drive
- Tank-Style Rotation
- Wheelbase: 396.5mm

**Sensor-Platzierung:** ✅ Verstanden!
- Beide auf Mittellinie (X = 0)
- Beide hinten montiert (Y negativ)
- GPS ganz hinten (-340mm)
- IMU etwas weiter vorne (-292mm)

**Navigation:** ✅ Korrigiert!
- GPS-Position wird zu Rover-Mittelpunkt korrigiert
- Korrektur berücksichtigt Heading (rotiert mit!)
- Präzise Positionierung möglich

**Dein Rover ist perfekt aufgebaut!** 🚀
