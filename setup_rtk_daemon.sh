#!/bin/bash
#
# RTK NTRIP Daemon Setup Script
# Creates systemd service for automatic RTK corrections via NTRIP
#
# Usage: sudo bash setup_rtk_daemon.sh
#

set -e

echo "========================================"
echo "RTK NTRIP Daemon Setup"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Check if str2str is installed
if ! command -v str2str &> /dev/null; then
    echo "❌ str2str not found! Please run setup_rtklib.sh first"
    exit 1
fi

# Check if config.json exists
CONFIG_FILE="config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ config.json not found in current directory"
    echo "Please run this script from the rover-steuerung directory"
    exit 1
fi

# Parse config.json for NTRIP credentials
echo "📖 Reading NTRIP configuration from config.json..."

# Extract NTRIP parameters using Python
NTRIP_SERVER=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['server'])" 2>/dev/null || echo "")
NTRIP_PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['port'])" 2>/dev/null || echo "")
NTRIP_MOUNTPOINT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['mountpoint'])" 2>/dev/null || echo "")
NTRIP_USER=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['username'])" 2>/dev/null || echo "")
NTRIP_PASS=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['password'])" 2>/dev/null || echo "")
REF_LAT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['ref_lat'])" 2>/dev/null || echo "")
REF_LON=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['ref_lon'])" 2>/dev/null || echo "")
REF_ALT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['ntrip']['ref_alt'])" 2>/dev/null || echo "")
GNSS_PORT=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['serial_ports']['gnss'])" 2>/dev/null || echo "/dev/ttyACM0")
GNSS_BAUD=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['serial_ports']['gnss_baudrate'])" 2>/dev/null || echo "115200")

# Validate parameters
if [ -z "$NTRIP_SERVER" ] || [ -z "$NTRIP_USER" ] || [ -z "$NTRIP_PASS" ]; then
    echo "❌ Missing NTRIP configuration in config.json"
    exit 1
fi

echo "✅ NTRIP Configuration:"
echo "   Server: $NTRIP_SERVER:$NTRIP_PORT"
echo "   Mountpoint: $NTRIP_MOUNTPOINT"
echo "   Username: $NTRIP_USER"
echo "   Reference Position: $REF_LAT, $REF_LON, ${REF_ALT}m"
echo "   GPS Port: $GNSS_PORT @ $GNSS_BAUD baud"
echo ""

# Extract only the device name from full path (e.g., /dev/ttyACM0 -> ttyACM0)
GNSS_DEVICE=$(basename "$GNSS_PORT")

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/rtk-ntrip.service"

echo "📝 Creating systemd service: $SERVICE_FILE"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=RTK NTRIP Streamer (str2str)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/local/bin/str2str \\
    -in ntrip://${NTRIP_USER}:${NTRIP_PASS}@${NTRIP_SERVER}:${NTRIP_PORT}/${NTRIP_MOUNTPOINT} \\
    -p ${REF_LAT} ${REF_LON} ${REF_ALT} \\
    -n 1 \\
    -out serial://${GNSS_DEVICE}:${GNSS_BAUD}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"
echo ""

# Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "✅ Enabling rtk-ntrip service..."
systemctl enable rtk-ntrip.service

echo ""
echo "========================================"
echo "✅ RTK NTRIP Daemon Setup Complete!"
echo "========================================"
echo ""
echo "Service Commands:"
echo "  Start:   sudo systemctl start rtk-ntrip"
echo "  Stop:    sudo systemctl stop rtk-ntrip"
echo "  Status:  sudo systemctl status rtk-ntrip"
echo "  Logs:    sudo journalctl -u rtk-ntrip -f"
echo ""
echo "⚠️  Note: The service is enabled but NOT started yet."
echo ""
read -p "Do you want to start the service now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting rtk-ntrip service..."
    systemctl start rtk-ntrip.service
    sleep 2
    echo ""
    echo "Status:"
    systemctl status rtk-ntrip.service --no-pager
    echo ""
    echo "✅ Service started! RTK corrections are now streaming to GPS."
    echo "   Monitor with: python3 rtk_diagnostics.py"
    echo "   Wait 10-15 minutes for RTK Fixed status"
else
    echo "⏸️  Service not started. Start manually when ready:"
    echo "   sudo systemctl start rtk-ntrip"
fi
echo ""
