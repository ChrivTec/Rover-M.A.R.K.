# M.A.R.K. Rover Control System

Autonomous garden rover with GNSS/RTK + IMU navigation and differential drive control.

## 🎯 Features

- ✅ **RTK/NTRIP GPS** - Centimeter-level accuracy using SAPOS Niedersachsen
- ✅ **9-DoF IMU** - BNO085 compass for heading
- ✅ **Autonomous Navigation** - Waypoint-based with line-following
- ✅ **Differential Drive** - Speed modulation for precise steering
- ✅ **REST API** - Web interface integration
- ✅ **Safety Monitoring** - GPS watchdog, RTK quality checks

## 📋 Hardware Requirements

| Component | Model | Connection |
|-----------|-------|------------|
| Computer | Raspberry Pi 5 | - |
| GNSS Receiver | u-blox ZED-F9P | USB → `/dev/ttyACM1` @ 115200 |
| IMU | Adafruit BNO085 | I2C bus 1, addr 0x4A |
| Motor Controller | RoboClaw 2x15A | USB → `/dev/ttyACM0` @ 38400 |
| Motors | 2x DC motors | Connected to RoboClaw M1/M2 |

## 🚀 Quick Start

### 1. Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and build tools
sudo apt install python3 python3-pip python3-venv git build-essential -y

# Install I2C tools
sudo apt install i2c-tools -y

# Enable I2C
sudo raspi-config
# → Interface Options → I2C → Enable
```

### 2. Install RTKLIB (str2str)

```bash
# Clone and compile RTKLIB
cd ~
mkdir rtklib && cd rtklib
git clone https://github.com/rtklibexplorer/RTKLIB.git
cd RTKLIB/app/consapp/str2str/gcc
make

# Install to system
sudo cp str2str /usr/local/bin/str2str
which str2str  # Verify installation
```

### 3. Clone Rover Code

```bash
cd ~
git clone <your-repo-url> rover-steuerung
cd rover-steuerung
```

### 4. Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 5. Configure Settings

Edit `config.json`:
- Update NTRIP credentials if needed
- Verify serial port mappings (`/dev/ttyACM0`, `/dev/ttyACM1`)
- Adjust PID parameters for your rover

### 6. Test Hardware

```bash
# Activate virtual environment
source venv/bin/activate

# Test GNSS (should show RTK fix after 5-10 minutes)
python3 test_gnss.py

# Test IMU
python3 test_imu.py

# Test Motors (CAREFUL - motors will move!)
python3 test_motors.py
```

### 7. Setup RTK/NTRIP Daemon

```bash
# Install systemd services
sudo bash setup_systemd.sh

# Start RTK daemon
sudo systemctl start rtk-ntrip.service

# Check status
sudo systemctl status rtk-ntrip.service

# Monitor RTK fix (should reach "RTK Fixed" after 5-10 minutes)
sudo journalctl -u rtk-ntrip.service -f
```

### 8. Run Rover

```bash
# Manual mode (for testing)
source venv/bin/activate
python3 main.py

# OR: Service mode (automatic startup)
sudo systemctl start rover-control.service
sudo journalctl -u rover-control.service -f
```

## 🗺️ Creating Routes

Create `waypoints.json`:

```json
{
  "id": "route_001",
  "name": "My Route",
  "waypoints": [
    {
      "lat": 50.9379,
      "lon": 6.9580,
      "action": "forward",
      "speed_ms": 0.3
    },
    {
      "lat": 50.9380,
      "lon": 6.9581,
      "action": "forward",
      "speed_ms": 0.25
    }
  ]
}
```

Use RTK GPS to record waypoints in your garden!

## 🔧 Configuration

### PID Tuning

Edit `config.json` → `control` → `cross_track_pid`:

```json
{
  "kp": 2.0,    // Proportional gain (increase for faster correction)
  "ki": 0.1,    // Integral gain (reduce oscillation)
  "kd": 0.5,    // Derivative gain (damping)
  "output_limit": 0.5  // Max speed modulation (±50%)
}
```

### Safety Limits

Edit `config.json` → `safety`:

```json
{
  "min_satellites": 6,
  "max_hdop": 5.0,
  "require_rtk": true,  // Set to false for GPS-only testing
  "max_connection_loss_s": 35.0
}
```

## 🌐 Web API

The rover exposes a REST API on port 5000:

### Start Mission
```bash
curl -X POST http://raspberrypi:5000/api/rover/start_mission \
  -H "Content-Type: application/json" \
  -d '{"route_file": "waypoints.json"}'
```

### Get Telemetry
```bash
curl http://raspberrypi:5000/api/rover/telemetry
```

### Emergency Stop
```bash
curl -X POST http://raspberrypi:5000/api/rover/emergency_stop
```

## 🐛 Troubleshooting

### RTK Fix Not Achieved

**Symptoms:** GPS fix quality stays at "GPS" (1) instead of "RTK Fixed" (4)

**Solutions:**
1. Check NTRIP credentials in `config.json`
2. Verify str2str daemon is running: `systemctl status rtk-ntrip.service`
3. Check GNSS antenna has clear sky view
4. Wait longer (can take 5-15 minutes)
5. Monitor logs: `sudo journalctl -u rtk-ntrip.service -f`

### Serial Port Not Found

**Symptoms:** `Failed to connect to GNSS` or `Failed to connect to RoboClaw`

**Solutions:**
1. Check USB connections: `ls -l /dev/ttyACM*`
2. Update `config.json` with correct ports
3. Verify permissions: `sudo usermod -aG dialout $USER` (logout/login required)

### IMU Not Responding

**Symptoms:** `Failed to connect to IMU`

**Solutions:**
1. Check I2C connection: `i2cdetect -y 1`
2. Should see device at address 0x4A (or 0x4B)
3. Verify I2C is enabled: `sudo raspi-config`
4. Check wiring (SDA, SCL, 3.3V, GND)

### Motors Not Moving

**Symptoms:** RoboClaw connects but motors don't move

**Solutions:**
1. Check battery voltage (should be 12V+)
2. Verify motor wiring to M1/M2
3. Check RoboClaw settings (address 128, baudrate 38400)
4. Test with `test_motors.py`

### Rover Not Following Line

**Symptoms:** Rover wanders off course

**Solutions:**
1. Tune PID parameters (start with lower Kp)
2. Ensure RTK Fixed quality (not just GPS)
3. Check IMU heading accuracy
4. Reduce base speed
5. Increase `output_limit` for more aggressive steering

## 📊 State Machine

The rover operates in these states:

```
IDLE → ROTATING → DRIVING → REACHED_WAYPOINT ─┐
  ↑                                            │
  └────────────────────────────────────────────┘

ERROR / EMERGENCY_STOP (motors stopped)
```

- **IDLE**: Waiting for mission start
- **ROTATING**: Aligning heading to target bearing (±5°)
- **DRIVING**: Following line with CTE correction
- **REACHED_WAYPOINT**: Waypoint reached (<0.3m), advance to next
- **MISSION_COMPLETE**: All waypoints reached
- **ERROR**: Non-critical error (can be cleared)
- **EMERGENCY_STOP**: Critical error (GPS timeout, etc.)

## 🧪 Testing

### Unit Tests
```bash
pytest test_utils.py -v
```

### Hardware Tests
```bash
# Individual component tests
python3 test_gnss.py    # GPS/RTK
python3 test_imu.py     # Compass
python3 test_motors.py  # Motor controller
```

## 📝 File Structure

```
rover-steuerung/
├── config.json              # Configuration
├── waypoints.json           # Route waypoints
├── requirements.txt         # Python dependencies
├── main.py                  # Main control system
├── rover_api.py             # Flask REST API
├── utils.py                 # Geo calculations
├── kalman_filter.py         # GPS smoothing
├── pid_controller.py        # PID controller
├── gnss_module.py           # GPS/RTK interface
├── imu_module.py            # BNO085 IMU
├── motor_module.py          # RoboClaw interface
├── waypoint_manager.py      # Route management
├── rover_state.py           # State machine
├── navigator.py             # Navigation engine
├── connection_monitor.py    # GPS watchdog
├── test_*.py                # Test scripts
├── setup_systemd.sh         # Service installer
└── README.md                # This file
```

## ⚙️ systemd Services

### RTK/NTRIP Service
```bash
sudo systemctl start rtk-ntrip.service   # Start
sudo systemctl stop rtk-ntrip.service    # Stop
sudo systemctl status rtk-ntrip.service  # Status
sudo systemctl enable rtk-ntrip.service  # Auto-start on boot
```

### Rover Control Service
```bash
sudo systemctl start rover-control.service
sudo systemctl stop rover-control.service
sudo systemctl status rover-control.service
```

### View Logs
```bash
sudo journalctl -u rtk-ntrip.service -f      # RTK logs
sudo journalctl -u rover-control.service -f  # Rover logs
```

## 🔒 Safety Features

- **GPS Watchdog**: Emergency stop after 35s without GPS update
- **RTK Quality Check**: Requires RTK Fixed (configurable)
- **Satellite Check**: Minimum 6 satellites
- **HDOP Check**: Maximum 5.0
- **Emergency Stop API**: Web button for immediate stop

## 📚 Navigation Algorithm

### Phase 1: Heading Alignment (ROTATING)
1. Calculate bearing to target waypoint
2. Compare with current IMU heading
3. Rotate using differential drive (one motor stopped)
4. Continue until aligned (±5°)

### Phase 2: Line Following (DRIVING)
1. Calculate Cross-Track Error (CTE) to ideal line
2. PID converts CTE → speed modulation
3. Apply differential speeds:
   - `v_left = base_speed × (1 - modulation)`
   - `v_right = base_speed × (1 + modulation)`
4. Result: Rover steers back to line

### Phase 3: Waypoint Detection
- Distance to target < 0.3m → waypoint reached
- Advance to next waypoint or complete mission

## 📄 License

MIT License - See LICENSE file

## 👤 Author

M.A.R.K. Rover Project

## 🙏 Acknowledgements

- RTKLIB by rtklibexplorer
- Adafruit CircuitPython libraries
- SAPOS Niedersachsen RTK network
