#!/bin/bash
#
# RTK Port Auto-Detection & Service Update Script
# Findet automatisch den u-blox GPS Port und aktualisiert den RTK Service
#

set -e

echo "============================================================"
echo "RTK Port Auto-Detection & Service Update"
echo "============================================================"
echo ""

# Funktion: Finde u-blox GPS Modul
find_ublox_port() {
    echo "🔍 Searching for u-blox GPS module..."
    
    for port in /dev/ttyACM*; do
        if [ -e "$port" ]; then
            # Prüfe ob u-blox
            vendor=$(udevadm info --name=$port --query=property | grep ID_VENDOR_ID | cut -d'=' -f2)
            if [ "$vendor" = "1546" ]; then
                echo "✅ Found u-blox GPS at: $port"
                echo "$port"
                return 0
            fi
        fi
    done
    
    # Fallback: Suche nach "u-blox" im Device Namen
    for port in /dev/ttyACM*; do
        if [ -e "$port" ]; then
            info=$(udevadm info --name=$port --query=property | grep -i "u-blox" || true)
            if [ -n "$info" ]; then
                echo "✅ Found u-blox GPS at: $port (fallback method)"
                echo "$port"
                return 0
            fi
        fi
    done
    
    echo "❌ ERROR: No u-blox GPS module found!"
    echo "   → Check USB connection"
    echo "   → Available ports:"
    ls -la /dev/ttyACM* 2>/dev/null || echo "   (none)"
    return 1
}

# Finde GPS Port
GPS_PORT=$(find_ublox_port)
if [ -z "$GPS_PORT" ]; then
    exit 1
fi

# Extrahiere Port-Name (z.B. ttyACM0 aus /dev/ttyACM0)
PORT_NAME=$(basename $GPS_PORT)

echo ""
echo "============================================================"
echo "Updating RTK Service Configuration"
echo "============================================================"
echo ""
echo "GPS Port: /dev/$PORT_NAME"
echo ""

# Hole NTRIP Credentials aus config.json (falls vorhanden)
CONFIG_FILE="$HOME/mark-rover/config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo "📋 Reading NTRIP config from config.json..."
    NTRIP_SERVER=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['ntrip']['server'])" 2>/dev/null || echo "sapos-nw-ntrip.de")
    NTRIP_PORT=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['ntrip']['port'])" 2>/dev/null || echo "2101")
    NTRIP_MOUNTPOINT=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['ntrip']['mountpoint'])" 2>/dev/null || echo "VRS_3_4G_NW")
    NTRIP_USER=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['ntrip']['username'])" 2>/dev/null || echo "nw-9112470")
    NTRIP_PASS=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['ntrip']['password'])" 2>/dev/null || echo "123ABCde")
    POSITION_LAT=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['hardware']['antenna_position_lat'])" 2>/dev/null || echo "50.9334")
    POSITION_LON=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['hardware']['antenna_position_lon'])" 2>/dev/null || echo "6.9886")
else
    echo "⚠️  Config file not found, using defaults..."
    NTRIP_SERVER="sapos-nw-ntrip.de"
    NTRIP_PORT="2101"
    NTRIP_MOUNTPOINT="VRS_3_4G_NW"
    NTRIP_USER="nw-9112470"
    NTRIP_PASS="123ABCde"
    POSITION_LAT="50.9334"
    POSITION_LON="6.9886"
fi

echo "  Server: $NTRIP_SERVER:$NTRIP_PORT"
echo "  Mountpoint: $NTRIP_MOUNTPOINT"
echo "  Position: $POSITION_LAT, $POSITION_LON"
echo ""

# Erstelle Service File
echo "📝 Creating systemd service file..."

sudo tee /etc/systemd/system/rtk-ntrip.service > /dev/null <<EOF
[Unit]
Description=RTK NTRIP Streamer (str2str)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/str2str -in ntrip://${NTRIP_USER}:${NTRIP_PASS}@${NTRIP_SERVER}:${NTRIP_PORT}/${NTRIP_MOUNTPOINT} -p ${POSITION_LAT} ${POSITION_LON} 0 -n 1 -out serial://${PORT_NAME}:115200
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"
echo ""

# Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Restart service
echo "🔄 Restarting RTK service..."
sudo systemctl restart rtk-ntrip

# Enable service
echo "✅ Enabling RTK service for auto-start..."
sudo systemctl enable rtk-ntrip

# Check status
echo ""
echo "============================================================"
echo "Service Status"
echo "============================================================"
sudo systemctl status rtk-ntrip --no-pager

echo ""
echo "============================================================"
echo "✅ RTK Service Updated Successfully!"
echo "============================================================"
echo ""
echo "GPS Port: /dev/$PORT_NAME"
echo "Service: rtk-ntrip.service"
echo "Status: $(sudo systemctl is-active rtk-ntrip)"
echo ""
echo "Monitor live: sudo journalctl -u rtk-ntrip -f"
echo ""
