# 🤖 M.A.R.K. Rover Control System - Anti Gravity Prompt (MIT RTK/NTRIP)

**Projekt**: Autonomer Gartenbau-Roboter mit GNSS/RTK + IMU Navigation
**Plattform**: Raspberry Pi 5
**Sprache**: Python 3.10+
**Status**: Neu schreiben (von Grund auf)
**RTK-Setup**: Nach ardumower RTKLIB Anleitung

---

## 🎯 PROJEKT-ÜBERSICHT

Du schreibst das **komplette Backend-Steuerungssystem** für einen autonomen Rover namens M.A.R.K. Der Rover soll:

1. ✅ **RTK/NTRIP einrichten** (str2str daemon auf RPi)
2. ✅ **Routen vom Web-Interface empfangen** (JSON-Format)
3. ✅ **Autonom Waypoints abfahren** mit GPS/RTK + Kompass
4. ✅ **Präzise navigieren** mit Differenzial-Lenkung (Speed-Modulation)
5. ✅ **Live-Telemetrie senden** an Web-Dashboard
6. ✅ **Sicherheitsüberwachung** (GPS-Fix, Satelliten, Connection-Watchdog)

---

## 🏗️ HARDWARE-KONFIGURATION

```
┌─────────────────────────────────────────┐
│        Raspberry Pi 5 (Brain)           │
├─────────────────────────────────────────┤
│ USB-A:                                  │
│  ├─ /dev/ttyACM0 → RoboClaw (38400)    │
│  └─ /dev/ttyACM1 → u-blox ZED-F9P      │
│                     (115200 GNSS/RTK)  │
├─────────────────────────────────────────┤
│ I2C-Bus (/dev/i2c-1):                  │
│  └─ 0x28 → BNO085 (9-DoF Compass)      │
├─────────────────────────────────────────┤
│ Systemd Daemons:                        │
│  ├─ str2str (RTK/NTRIP streamer)       │
│  ├─ rover-control (main.py)            │
│  └─ flask-api (Web-Server)             │
└─────────────────────────────────────────┘

Hardware-Parameter:
• Rad-Durchmesser: 0.079 m
• Achsenabstand: 0.396503 m
• Max RPM: 60
• GPS-Antenne Offset: +0.34m vorwärts
• Max Speed: ~0.25 m/s
• Basis-Speed Fahrt: 0.2-0.3 m/s

RTK Configuration:
• NTRIP Server: sapos-nw-ntrip.de:2101
• Mountpoint: VRS_3_4G_NW
• Reference Position: 50.9379 N, 6.9580 E
• Altitude: 0 m (aus config.json)
```

---

## ⚡ RTK/NTRIP SETUP (SEHR WICHTIG!)

### Installation (Linux Shell):

```bash
# 1. RTKLIB von rtklibexplorer kompilieren
cd ~
mkdir rtklib && cd rtklib
git clone https://github.com/rtklibexplorer/RTKLIB.git
cd RTKLIB/app/consapp/str2str/gcc
make

# 2. Installieren in /usr/local/bin
sudo cp str2str /usr/local/bin/str2str
which str2str  # Verify

# 3. Test: GNSS-Daten auslesen
str2str -in serial://ttyACM1:115200

# Wenn NMEA-Sätze sichtbar → OK!
# Buchstabensalat → Baudrate korrekt, Verbindung funktioniert
```

### RTK Aktivieren (Manuell zum Testen):

```bash
# Mit SAPOS Niedersachsen (aus config.json):
str2str -in ntrip://nw-9112470:123ABCde@sapos-nw-ntrip.de:2101/VRS_3_4G_NW \
        -p 50.9379 6.9580 0 \
        -n 1 \
        -out serial://ttyACM1:115200

# Warten... nach 5-10 Minuten: RTK Fixed!
# Prüfen in GNSS-Module: fix_quality == 4 ("RTK Fixed")
```

### Als Systemd Daemon einstellen (PRODUKTIV):

**Datei: `/etc/systemd/system/rtk-ntrip.service`**
```ini
[Unit]
Description=RTK NTRIP Streamer (str2str)
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/local/bin/str2str \
    -in ntrip://nw-9112470:123ABCde@sapos-nw-ntrip.de:2101/VRS_3_4G_NW \
    -p 50.9379 6.9580 0 \
    -n 1 \
    -out serial://ttyACM1:115200
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Aktivieren:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable rtk-ntrip.service
sudo systemctl start rtk-ntrip.service
sudo systemctl status rtk-ntrip.service
sudo journalctl -u rtk-ntrip.service -f  # Live-Logs
```

---

## 🧠 NAVIGATION-ALGORITHMUS (CRITICAL!)

### Phase 1: HEADING-ALIGNMENT (ROTATING State)
```
Situation:
  • Rover ist an Position X
  • Nächster Waypoint ist Y
  
Aktion:
  1. Berechne Sollkurs (Bearing) von X nach Y
  2. Vergleiche mit aktuellem Heading (vom BNO085)
  3. Drehe mit Differential Drive bis Abweichung < 5°
  
Code-Logik:
  heading = imu.get_heading()                    # 0-360°
  target_bearing = navigator.get_bearing(X, Y)  # 0-360°
  error = normalize_angle(target_bearing - heading)  # -180 bis +180°
  
  if abs(error) < 5:
      state = DRIVING  # Heading aligned!
  else:
      # Differential for Rotation
      if error > 0:  # Need to turn left (CCW)
          v_left = 0.0
          v_right = 0.2  # Rotation speed
      else:  # Need to turn right (CW)
          v_left = 0.2
          v_right = 0.0
```

### Phase 2: DRIVING mit Line-Following (DRIVING State)
```
Situation:
  • Rover soll von Waypoint A zu B fahren
  • Ideale Linie: A → B (gerade Strecke)
  
Aktion:
  1. Berechne CTE (Cross-Track Error) = Abstand zur Linie
  2. PID-Regler konvertiert CTE → Speed-Modulation
  3. Fahre mit Basis-Speed + Speed-Modulation
  
Code-Logik:
  base_speed = 0.3  # m/s
  cte = calculate_cross_track_error(current_pos, line_start, line_end)
  
  # PID: Input = CTE (meters), Output = Modulation (-15% bis +15%)
  pid_output = pid.update(cte)  # Range: -0.15 to +0.15
  
  # Speed-Modulation (NOT Steering Angle!)
  v_left = base_speed * (1 + pid_output)
  v_right = base_speed * (1 - pid_output)
  
  Beispiel:
    base_speed = 0.30 m/s
    CTE = +0.12 m (Rover rechts der Linie)
    PID = -0.10  (sollte nach links lenken)
    
    v_left = 0.30 * (1 - 0.10) = 0.27 m/s ← langsamer
    v_right = 0.30 * (1 + 0.10) = 0.33 m/s ← schneller
    
    → Rechts schneller als links = lenkt nach LINKS (korrigiert)
```

### Phase 3: WAYPOINT-ERKENNUNG
```
if distance(current_pos, target_waypoint) < 0.3 m:
    motors.stop()
    state = REACHED_WAYPOINT
    waypoint_manager.advance_waypoint()  # Next WP
    state = ROTATING  # Repeat from Phase 1
```

---

## 📋 MODULE ZU IMPLEMENTIEREN

### 1️⃣ `utils.py` - Utility-Funktionen (START HIER!)
**Zweck**: Geo-Berechnungen, Logging, Konstanten

**Funktionen**:
```python
def setup_logging(level=logging.INFO) -> None:
    """Setup logging für alle Module"""
    
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance zwischen GPS-Koordinaten in Metern (Haversine-Formel)"""
    # Input: Decimal Degrees
    # Output: Meters
    
def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Berechne Peilung (0-360°) von Punkt 1 zu Punkt 2
    0° = Nord, 90° = Osten, 180° = Süden, 270° = Westen"""
    
def normalize_angle(angle: float) -> float:
    """Normalisiere Winkel auf -180 bis +180 Grad"""
    
def calculate_cross_track_error(
    lat: float, lon: float,
    lat_start: float, lon_start: float,
    lat_end: float, lon_end: float
) -> float:
    """Calculate perpendicular distance to line segment
    Positive = right of line, Negative = left of line (in meters)"""
    
def meters_to_latlon_offset(north_m: float, east_m: float, lat_ref: float) -> Tuple[float, float]:
    """Konvertiere Meter-Offset zu Lat/Lon Offset"""
```

**Dependencies**: `math`, `logging`, `typing`

---

### 2️⃣ `kalman_filter.py` - GPS-Glättung
**Zweck**: Reduziert GPS-Rauschen durch Kalman-Filter

**Klasse: `KalmanFilter`**
```python
__init__(
    state_dim: int = 4,           # [lat, lon, vel_lat, vel_lon]
    measurement_dim: int = 2,     # [lat, lon]
    process_noise: float = 0.001,
    measurement_noise: float = 0.5
)

def predict(dt: float) -> None:
    """Prediktions-Schritt (State extrapolation)
    dt: Zeit seit letztem Update (Sekunden)"""
    
def update(measurement: np.ndarray, noise: float) -> None:
    """Update-Schritt mit neuer GPS-Messung
    measurement: [lat, lon]
    noise: Measurement-Noise (abhängig von GPS-Fix-Qualität)"""
    
def get_state() -> np.ndarray:
    """Gebe aktuellen State zurück [lat, lon, vel_lat, vel_lon]"""
```

**Interne Matrices** (Standard Kalman):
- `F` (State Transition): 4x4
- `H` (Measurement): 2x4
- `Q` (Process Noise): 4x4
- `R` (Measurement Noise): 2x2
- `P` (Estimate Error): 4x4
- `K` (Kalman Gain): computed

**Dependencies**: `numpy`, `logging`

---

### 3️⃣ `gnss_module.py` - u-blox ZED-F9P Interface
**Zweck**: GNSS/RTK-Daten lesen, NMEA-Parser, Kalman-Filter

**Klasse: `GNSSModule`**
```python
__init__(
    port: str,              # "/dev/ttyACM1"
    baudrate: int,          # 115200
    kalman_config: dict,    # aus config.json
    hardware_config: dict   # Antenna offsets
)

def connect() -> bool:
    """Verbinde zu GPS-Modul über Serial"""
    
def disconnect() -> None:
    """Disconnect"""
    
def update(heading: float = None) -> bool:
    """Lese NMEA-Daten, parse, update Kalman
    heading: optionaler IMU-Heading für Antenna-Offset Correction
    return: True wenn neue Daten verarbeitet"""
    
def get_position(filtered: bool = True) -> Tuple[float, float]:
    """Gebe (lat, lon) zurück - gefiltert oder raw"""
    
def get_status() -> dict:
    """Return: {latitude, longitude, filtered_lat, filtered_lon, altitude,
                fix_quality, num_satellites, hdop, speed_kmh, connected}"""
    
def has_valid_fix() -> bool:
    """True wenn GPS fix vorhanden (>= 4 Satelliten)"""
    
def has_rtk_fix() -> bool:
    """True wenn RTK Fix (Fixed oder Float)"""
    
def get_fix_quality_str() -> str:
    """Return: 'Invalid', 'GPS', 'DGPS', 'RTK Fixed', 'RTK Float'"""
```

**NMEA-Parsing** (rtklibexplorer str2str injiziert diese):
- Parse `$GNGGA`: Position, Altitude, Fix Quality (0=Invalid, 1=GPS, 2=DGPS, 4=RTK Fixed, 5=RTK Float), Satellites, HDOP
- Parse `$GNRMC`: Speed over Ground

**RTK Fix Quality Codes**:
- 0: Invalid
- 1: GPS (Single Point)
- 2: DGPS
- 3: PPS
- 4: **RTK Fixed** ← Ziel!
- 5: **RTK Float** ← Auch gut
- 6: Estimated

**Antenna Offset Correction**:
- GPS-Antenne ist +0.34m vorne
- Von Antenne zu Rover-Center: rotiere um Heading

**Dependencies**: `serial`, `pynmea2`, `numpy`, `logging`, `kalman_filter`

---

### 4️⃣ `imu_module.py` - BNO085 Compass
**Zweck**: Heading (Kompass-Richtung) vom BNO085 I2C-Sensor

**Klasse: `IMUModule`**
```python
__init__(
    i2c_bus: int = 1,           # /dev/i2c-1
    address: int = 0x28,        # BNO085 Adresse
    ndof_mode: bool = True      # NDOF = 9-Dof Fused Mode
)

def connect() -> bool:
    """Verbinde zu BNO085 über I2C"""
    
def disconnect() -> None:
    """Close I2C"""
    
def update() -> bool:
    """Lese aktuelle Orientierungs-Daten"""
    
def get_heading() -> float:
    """Return: Heading 0-360° (0=Nord, 90=Ost, CCW positiv)"""
    
def get_roll() -> float:
    """Return: Roll -180 bis 180°"""
    
def get_pitch() -> float:
    """Return: Pitch -90 bis 90°"""
    
def get_status() -> dict:
    """Return: {heading, roll, pitch, calibration_status, connected}"""
    
def calibrate_magnetometer(duration_s: int = 30) -> bool:
    """Mag-Kalibrierung: Drehe Rover 360° für 30s"""
```

**I2C Interface**:
- Address: 0x28
- NDOF Mode: 9-Dof Sensor Fusion
- Euler Output: Heading, Roll, Pitch

**Dependencies**: `smbus2` oder `adafruit-circuitpython-bno055`, `logging`

---

### 5️⃣ `motor_module.py` - RoboClaw Dual-Motor Controller
**Zweck**: Kommunikation mit RoboClaw, Speed-Setzen

**Klasse: `MotorController`**
```python
__init__(
    port: str,              # "/dev/ttyACM0"
    baudrate: int,          # 38400
    address: int,           # 128 (0x80)
    config: dict            # Hardware-Parameter
)

def connect() -> bool:
    """Verbinde zu RoboClaw"""
    
def disconnect() -> None:
    """Close Serial"""
    
def set_velocity(left_m_s: float, right_m_s: float) -> bool:
    """Setze beide Radgeschwindigkeiten in m/s
    Konvertiert intern zu RoboClaw-Einheiten (0-32767)
    
    Konvertierung:
    v_max = (max_rpm / 60) * pi * wheel_diameter = 0.247 m/s
    roboclaw_speed = (v_m_s / v_max) * 32767
    """
    
def stop() -> bool:
    """Stop-Befehl mit Ramp auf 0"""
    
def get_status() -> dict:
    """Return: {left_current_a, right_current_a, left_temp_c,
                right_temp_c, battery_v, connected}"""
```

**RoboClaw Packet Serial Protocol**:
```
Command Format: [Address] [Command] [Data...] [Checksum]

Beispiel (M1 forward 50%):
  Address: 0x80 (128)
  Command: 0x04 (Drive M1)
  Speed: 16384 (50% of 32767)
  Bytes: 16384 = 0x4000 → [0x40] [0x00]
  Checksum: (0x80 + 0x04 + 0x40 + 0x00) & 0x7F
  
Packet: [0x80] [0x04] [0x40] [0x00] [Checksum]

Key Commands:
  0x04/0x05: Drive M1/M2 (signed 16-bit)
  0x24: Read Main Battery Voltage
  0x27: Read Temperature
  0x2B/0x2C: Read Current M1/M2
```

**Dependencies**: `serial`, `logging`

---

### 6️⃣ `pid_controller.py` - PID Regler
**Zweck**: CTE → Speed-Modulation Regelung

**Klasse: `PIDController`**
```python
__init__(
    kp: float,              # Proportional Gain
    ki: float,              # Integral Gain
    kd: float,              # Derivative Gain
    output_limit: float = 1.0  # Clamp output
)

def update(error: float, dt: float = 0.1) -> float:
    """Update mit aktuellem Fehler, return Output (clamped)
    
    Beispiel für CTE-Regelung:
    error = cte_in_meters  # z.B. +0.12 m (rechts der Linie)
    output = pid.update(error)  # z.B. -0.10 (sollte nach links lenken)
    """
    
def reset() -> None:
    """Reset alle Integrale und Derivative"""
```

**Dependencies**: `logging`

---

### 7️⃣ `waypoint_manager.py` - Route-Verwaltung
**Zweck**: JSON-Routen laden, Waypoints verwalten

**Klasse: `Waypoint`**
```python
@dataclass
class Waypoint:
    lat: float
    lon: float
    action: str = "forward"      # forward, spray, etc.
    speed_ms: float = 0.3
    duration_s: float = 0.0
```

**Klasse: `WaypointManager`**
```python
__init__()

def load_waypoints(filepath: str) -> bool:
    """Lade Route aus JSON-Datei"""
    
def get_current_waypoint() -> Optional[Waypoint]:
    """Gebe aktuellen Waypoint"""
    
def get_next_waypoint() -> Optional[Waypoint]:
    """Gebe nächsten Waypoint"""
    
def advance_waypoint() -> bool:
    """Wechsle zum nächsten, return True wenn mehr vorhanden"""
    
def get_progress() -> Tuple[int, int]:
    """Return (current_index, total_count)"""
    
def reset() -> None:
    """Starte vom ersten WP neu"""
```

**JSON Format**:
```json
{
  "id": "20260106_115200",
  "name": "Route_1",
  "waypoints": [
    {"lat": 50.9379, "lon": 6.9580, "action": "forward", "speed_ms": 0.3},
    {"lat": 50.9380, "lon": 6.9581, "action": "spray", "duration_s": 5},
    {"lat": 50.9381, "lon": 6.9582, "action": "forward", "speed_ms": 0.25}
  ]
}
```

**Dependencies**: `json`, `dataclasses`, `logging`, `typing`

---

### 8️⃣ `rover_state.py` - State Machine
**Zweck**: Zentrale Zustandsverwaltung

**Enum: `RoverState`**
```python
IDLE              # Warten auf Mission
ROTATING          # Heading-Alignment
DRIVING           # Line-Following
REACHED_WAYPOINT  # WP erreicht
MISSION_COMPLETE  # Fertig
ERROR             # Fehler (nicht kritisch)
EMERGENCY_STOP    # Kritischer Fehler
```

**Klasse: `RoverStateMachine`**
```python
__init__()

def set_state(new_state: RoverState, reason: str = "") -> None:
    """Zustandswechsel mit Grund"""
    
def get_state() -> RoverState:
    """Aktueller State"""
    
def set_error(message: str) -> None:
    """State = ERROR + Nachricht"""
    
def emergency_stop(reason: str = "") -> None:
    """State = EMERGENCY_STOP + Grund"""
    
def clear_error() -> None:
    """Reset aus ERROR/EMERGENCY_STOP zu IDLE"""
    
def is_operational() -> bool:
    """True wenn State != ERROR/EMERGENCY_STOP"""
    
def get_state_history() -> List[Tuple[RoverState, float, str]]:
    """Return letzte 20 States mit Timestamp und Grund"""
```

**Dependencies**: `enum`, `logging`, `time`

---

### 9️⃣ `navigator.py` - Navigation Engine
**Zweck**: Bearing, CTE, Line-Following Logik

**Klasse: `Navigator`**
```python
__init__(config: dict)
    # config: Lade PID-Parameter, Navigation-Parameter

def set_target(lat: float, lon: float) -> None:
    """Setze Ziel-Koordinate"""
    
def set_line_segment(lat_start: float, lon_start: float,
                     lat_end: float, lon_end: float) -> None:
    """Definiere ideale Fahrlinie"""
    
def get_bearing_to_target(lat: float, lon: float) -> float:
    """Berechne Sollkurs zu Ziel (0-360°)"""
    
def is_heading_aligned(heading: float, bearing: float, tolerance: float = 5.0) -> bool:
    """Prüfe ob |heading - bearing| < tolerance"""
    
def calculate_rotation_command(heading: float, bearing: float) -> Tuple[float, float]:
    """ROTATING Phase: Gebe (v_left, v_right) für Rotation
    
    Beispiel:
    heading = 90°, bearing = 95° (need +5° CW turn)
    return: (0.2, 0.0)  # Right motor only
    """
    
def calculate_line_following_command(
    lat: float, lon: float, heading: float, base_speed: float
) -> Tuple[float, float]:
    """DRIVING Phase: Gebe (v_left, v_right) mit Speed-Modulation
    
    Algorithm:
    1. Berechne CTE zur Line
    2. PID-Update mit CTE als Error
    3. Modulation = PID-Output (clamped auf ±15%)
    4. v_left = base_speed * (1 + modulation)
    5. v_right = base_speed * (1 - modulation)
    6. Return (v_left, v_right)
    """
    
def is_waypoint_reached(lat: float, lon: float, threshold: float = 0.3) -> bool:
    """Distanz zu Ziel < threshold?"""
    
def reset_controllers() -> None:
    """Reset alle PID-States"""
```

**Dependencies**: `config.json`, `pid_controller`, `utils`, `logging`

---

### 🔟 `connection_monitor.py` - GNSS Watchdog
**Zweck**: Überwacht GPS-Connection, Emergency-Stop bei Timeout

**Klasse: `ConnectionMonitor`**
```python
__init__(timeout_seconds: float = 35.0)

def start() -> None:
    """Starte Watchdog-Thread"""
    
def stop() -> None:
    """Stoppe Thread"""
    
def ping() -> None:
    """Signal: GPS-Update empfangen (update Timestamp)"""
    
def is_safe() -> bool:
    """True wenn letzte Update < timeout"""
    
def get_time_since_last_connection() -> float:
    """Sekunden seit letzter Update"""
```

**Verhalten**:
```
Watchdog läuft in separatem Thread:
  while running:
      if (now - last_ping) > timeout:
          logger.critical("GPS Connection Lost!")
          # Signal EMERGENCY_STOP an State Machine
      sleep(1.0)
```

**Dependencies**: `threading`, `time`, `logging`

---

### 1️⃣1️⃣ `rover_api.py` - Flask REST API
**Zweck**: Web-Interface ↔ Rover Control Integration

**Endpoints**:
```python
POST /api/rover/start_mission
    Body: {"route_file": "routes/Route_1.json"}
    Action: Load Route, set State=IDLE, start mission
    Response: {"status": "starting", "error": null}

POST /api/rover/stop
    Action: Gentle stop (State → IDLE)
    Response: {"status": "stopped", "state": "IDLE"}

POST /api/rover/emergency_stop
    Action: Hard stop (State → EMERGENCY_STOP)
    Response: {"status": "emergency", "state": "EMERGENCY_STOP"}

GET /api/rover/status
    Response: {"state": "DRIVING", "error": null, ...}

GET /api/rover/telemetry
    Response: {
        "timestamp": 1704522800.123,
        "state": "DRIVING",
        "position": {"lat": 50.9379, "lon": 6.9580},
        "heading_deg": 45.2,
        "speed_ms": 0.25,
        "current_waypoint": {"index": 2, "total": 10},
        "gnss": {
            "fix_quality": "RTK_FIXED",
            "num_satellites": 24,
            "hdop": 0.8
        },
        "motors": {
            "left_speed_ms": 0.27,
            "right_speed_ms": 0.33,
            "left_current_a": 1.2,
            "right_current_a": 1.3
        },
        "battery_v": 12.4,
        "error": null
    }
```

**Anforderungen**:
- Thread-safe Zugriff auf RoverControlSystem (Global Instance oder Queue)
- CORS enabled
- JSON Response nur, kein HTML

**Dependencies**: `flask`, `logging`, `threading`

---

### 1️⃣2️⃣ `main.py` - RoverControlSystem + Main Loop
**Zweck**: Zentrale Orchestrierung aller Module

**Klasse: `RoverControlSystem`**
```python
__init__(config_file: str)
    # Lade config.json
    # Initialisiere alle Module (GNSS, Motors, IMU, Navigator, etc.)
    # WICHTIG: RTK/NTRIP läuft bereits als systemd daemon!

def initialize_hardware() -> bool:
    """Connect GNSS, Motors, IMU, start ConnectionMonitor"""
    
def shutdown_hardware() -> None:
    """Stop alles"""
    
def check_rtk_status() -> bool:
    """Prüfe ob str2str daemon läuft (ps aux | grep str2str)
    Falls nicht: logger.warning() aber nicht stoppen"""
    
def check_safety_conditions() -> bool:
    """Prüfe: GPS-Fix, Satellites, HDOP, RTK (falls required), Connection"""
    
def update_sensors() -> None:
    """Lese IMU → GNSS → Kalman"""
    
def execute_state_machine() -> None:
    """State-basierte Logik:
    
    if IDLE:
        load first waypoint, set target, go ROTATING
    elif ROTATING:
        get bearing, if aligned: reset PID, go DRIVING
    elif DRIVING:
        if waypoint reached: go REACHED_WAYPOINT
        else: calculate_line_following → set motors
    elif REACHED_WAYPOINT:
        if advance_waypoint(): next, set target, go ROTATING
        else: go MISSION_COMPLETE
    elif MISSION_COMPLETE:
        motors.stop(), running = False
    elif ERROR/EMERGENCY_STOP:
        motors.stop()
    """
    
def log_status() -> None:
    """Log Rovers Status (Position, Heading, State, Sats, RTK Fix, etc.)"""
    
def run(waypoint_file: str) -> None:
    """Main Loop (10 Hz):
    
    while running:
        t_start = now()
        
        # 1. Sensoren
        update_sensors()
        connection_monitor.ping()
        
        # 2. Safety
        if not check_safety_conditions():
            state_machine.emergency_stop()
        
        # 3. State Machine
        execute_state_machine()
        
        # 4. Logging
        if counter % 20 == 0:
            log_status()
            check_rtk_status()  # Monitor RTK Daemon
        
        # 5. Sleep
        t_elapsed = now() - t_start
        sleep(max(0, 0.1 - t_elapsed))
    """
```

**Main Entry**:
```python
if __name__ == '__main__':
    config_file = 'config.json'
    waypoint_file = 'waypoints.json'
    
    rover = RoverControlSystem(config_file)
    rover.run(waypoint_file)
```

**Dependencies**: Alle anderen Module

---

### 1️⃣3️⃣ `config.json` - Konfigurationsdatei
**Format**:
```json
{
  "hardware": {
    "wheel_diameter_m": 0.079,
    "wheelbase_m": 0.396503,
    "max_rpm": 60,
    "encoder_counts_per_rev": 12,
    "antenna_offset_x_m": 0.0,
    "antenna_offset_y_m": 0.340,
    "antenna_offset_z_m": 0.196268,
    "imu_offset_x_m": 0.0,
    "imu_offset_y_m": 0.292235,
    "imu_offset_z_m": 0.19375
  },
  "serial_ports": {
    "gnss": "/dev/ttyACM1",
    "motor_controller": "/dev/ttyACM0",
    "gnss_baudrate": 115200,
    "motor_baudrate": 38400,
    "roboclaw_address": 128
  },
  "ntrip": {
    "server": "sapos-nw-ntrip.de",
    "port": 2101,
    "mountpoint": "VRS_3_4G_NW",
    "username": "nw-9112470",
    "password": "123ABCde",
    "ref_lat": 50.9379,
    "ref_lon": 6.9580,
    "ref_alt": 0
  },
  "navigation": {
    "max_speed_ms": 0.5,
    "min_speed_ms": 0.1,
    "max_acceleration_ms2": 0.3,
    "waypoint_reached_threshold_m": 0.3,
    "line_following_tolerance_m": 0.05,
    "rotation_speed_ms": 0.2,
    "heading_tolerance_deg": 5.0,
    "update_rate_hz": 10
  },
  "control": {
    "steering_pid": {
      "kp": 0.8,
      "ki": 0.05,
      "kd": 0.2,
      "output_limit": 0.15
    },
    "cross_track_pid": {
      "kp": 2.0,
      "ki": 0.1,
      "kd": 0.5,
      "output_limit": 0.5
    }
  },
  "kalman_filter": {
    "process_noise": 0.001,
    "measurement_noise_rtk_fixed": 0.01,
    "measurement_noise_rtk_float": 0.05,
    "measurement_noise_gps": 0.5
  },
  "safety": {
    "min_satellites": 6,
    "max_hdop": 5.0,
    "require_rtk": true,
    "emergency_stop_enabled": true,
    "max_connection_loss_s": 35.0
  }
}
```

---

## 🔧 IMPLEMENTIERUNGS-STRATEGIE

### Setup-Reihenfolge (KRITISCH):
1. ✅ **RTK/NTRIP Setup** (siehe Kapitel oben) - VOR allem anderen!
   ```bash
   # Test: str2str läuft und injiziert RTK-Daten
   str2str -in serial://ttyACM1:115200  # Sollte NMEA mit Fix Quality 4 zeigen
   ```

2. ✅ `utils.py` - Alle Hilfsfunktionen
3. ✅ `kalman_filter.py` - Kalman Filter
4. ✅ `pid_controller.py` - PID Regler
5. ✅ `gnss_module.py` - GPS Daten (mit RTK)
6. ✅ `imu_module.py` - Kompass
7. ✅ `motor_module.py` - Motor Control
8. ✅ `waypoint_manager.py` - Route Loading
9. ✅ `rover_state.py` - State Machine
10. ✅ `navigator.py` - Navigation Logic
11. ✅ `connection_monitor.py` - Watchdog
12. ✅ `rover_api.py` - Flask API
13. ✅ `main.py` - Main Control System
14. ✅ `config.json` - Configuration

### Code-Standards:
- **Type-Hints** überall (`from typing import ...`)
- **Docstrings** für jede Klasse/Methode
- **Error-Handling** mit Try-Except (spezifisch)
- **Logging** mit `logging`-Modul (kein print!)
- **No Globals**: Nur Instanzen/Config

### Testing:
```python
# test_utils.py - Unit Tests für Geo-Funktionen
def test_haversine():
    dist = haversine_distance(50.9379, 6.9580, 50.9380, 6.9581)
    assert 100 < dist < 150  # ~111m pro degree

def test_bearing():
    bearing = calculate_bearing(50.9379, 6.9580, 50.9380, 6.9581)
    assert 0 <= bearing < 360

def test_cte():
    cte = calculate_cross_track_error(...)
    # Verify sign (left/right) und magnitude
```

---

## 🚀 EXPECTED OUTCOMES

Nach vollständiger Implementierung:
- [ ] RTK/NTRIP Daemon läuft, injiziert Korrekturdaten
- [ ] `python3 main.py` startet ohne Fehler
- [ ] GNSS verbindet, empfängt NMEA mit RTK Fixed (fix_quality=4)
- [ ] BNO085 gibt Heading 0-360° aus
- [ ] Motors reagieren auf `set_velocity()`
- [ ] Web-Interface sendet Route → RoverAPI
- [ ] State Machine: IDLE → ROTATING → DRIVING → REACHED → MISSION_COMPLETE
- [ ] Speed-Modulation funktioniert (links/rechts Speed unterschiedlich je nach CTE)
- [ ] Waypoint-Erkennung bei 0.3m Distanz
- [ ] Live-Telemetry auf Dashboard
- [ ] GNSS-Watchdog triggert Emergency-Stop bei 35s Timeout

---

## 🐛 HÄUFIGE FEHLER

1. **RTK nicht aktiviert**: str2str daemon nicht laufen → `systemctl status rtk-ntrip.service`
2. **Fix Quality = 1 statt 4**: RTK-Korrekturdaten nicht injiziert → prüfe NTRIP Credentials
3. **NMEA Parse Error**: `try-except` um pynmea2.parse()
4. **I2C Timeout**: Prüfe `i2cdetect -y 1`, Address 0x28
5. **Serial Checksum**: RoboClaw Checksum = (sum of bytes) & 0x7F
6. **Speed Saturation**: Clamp PID-Output auf ±output_limit
7. **Angle Normalization**: Normalize zu -180...+180 vor Vergleich
8. **CTE Sign**: Positive = right of line, Negative = left
9. **Thread-Safety**: RoverControl + Flask in separaten Threads → Locks nötig
10. **Kalman Divergence**: Noise-Parameter überprüfen

---

## 📞 DEBUG COMMANDS

```bash
# 1. RTK Status prüfen
sudo systemctl status rtk-ntrip.service
sudo journalctl -u rtk-ntrip.service -f

# 2. GNSS Live-Check mit RTK
cat /dev/ttyACM1 | grep "GGA"  # Sollte Fix Quality=4 zeigen

# 3. I2C Scan
i2cdetect -y 1

# 4. RoboClaw Serial
minicom -D /dev/ttyACM0 -b 38400

# 5. RoverControl Logs
python3 main.py 2>&1 | tee rover.log

# 6. Einzelne Module testen
python3 -c "from gnss_module import GNSSModule; m = GNSSModule(...); m.connect()"
```

---

## 🎯 ABNAHME-KRITERIEN

**Phase 0 - RTK Ready** (MUSS ZUERST):
- str2str daemon läuft
- GNSS empfängt RTK-Daten (GGA Sätze mit Fix Quality=4)
- NTRIP Credentials funktionieren

**Phase 1 - Hardware Ready**:
- GNSS zeigt RTK-Daten
- BNO085 gibt Heading
- Motors drehen sich
- Config.json geladen

**Phase 2 - Navigation Ready**:
- State Machine durchläuft IDLE → ROTATING → DRIVING
- Waypoints werden geladen und abgearbeitet
- Speed-Modulation funktioniert (CTE-Regelung sichtbar)
- Watchdog triggert bei Connection-Loss

**Phase 3 - Integration Ready**:
- Web-Interface sendet Routen
- RoverAPI Endpoints antworten
- Live-Telemetry im Dashboard
- End-to-End Test erfolgreich

---

**Status**: Ready für Anti Gravity 🚀

Kopiere diesen kompletten Prompt direkt in Anti Gravity!

**WICHTIG**: Stelle sicher, dass RTK/NTRIP zuerst funktioniert, bevor du mit main.py startest!
