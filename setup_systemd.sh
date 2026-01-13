#!/bin/bash
# Setup script for M.A.R.K. Rover systemd services
# Run with: sudo bash setup_systemd.sh

set -e

echo "=========================================="
echo "M.A.R.K. Rover Systemd Service Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "ERROR: This script must be run as root (sudo)"
  exit 1
fi

# Get current directory (rover code location)
ROVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Rover directory: $ROVER_DIR"
echo ""

# Parse config.json for NTRIP settings using python
# We use a small python script to extract the values safely
echo "Reading NTRIP configuration from config.json..."
NTRIP_URL=$(python3 -c "import json; f=open('$ROVER_DIR/config.json'); c=json.load(f); n=c['ntrip']; print(f'ntrip://{n['username']}:{n['password']}@{n['server']}:{n['port']}/{n['mountpoint']}')")
REF_LAT=$(python3 -c "import json; f=open('$ROVER_DIR/config.json'); c=json.load(f); print(c['ntrip']['ref_lat'])")
REF_LON=$(python3 -c "import json; f=open('$ROVER_DIR/config.json'); c=json.load(f); print(c['ntrip']['ref_lon'])")
REF_ALT=$(python3 -c "import json; f=open('$ROVER_DIR/config.json'); c=json.load(f); print(c['ntrip'].get('ref_alt', 0))")
GNSS_PORT=$(python3 -c "import json; f=open('$ROVER_DIR/config.json'); c=json.load(f); print(c['serial_ports']['gnss'].replace('/dev/', ''))")
GNSS_BAUD=$(python3 -c "import json; f=open('$ROVER_DIR/config.json'); c=json.load(f); print(c['serial_ports']['gnss_baudrate'])")

echo "  URL: $NTRIP_URL"
echo "  Ref: $REF_LAT, $REF_LON, $REF_ALT"
echo "  Out: serial://$GNSS_PORT:$GNSS_BAUD"
echo ""

# Create RTK/NTRIP service
echo "Creating rtk-ntrip.service..."
cat > /etc/systemd/system/rtk-ntrip.service << EOF
[Unit]
Description=RTK NTRIP Streamer (str2str)
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/usr/local/bin/str2str \\
    -in $NTRIP_URL \\
    -p $REF_LAT $REF_LON $REF_ALT \\
    -n 1 \\
    -out serial://$GNSS_PORT:$GNSS_BAUD
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✓ rtk-ntrip.service created"
echo ""

# Create Rover Control service
echo "Creating rover-control.service..."
# Check for virtual environment
PYTHON_EXEC="/usr/bin/python3"
if [ -d "$ROVER_DIR/venv" ]; then
    PYTHON_EXEC="$ROVER_DIR/venv/bin/python3"
    echo "  Using virtual environment: $PYTHON_EXEC"
fi

cat > /etc/systemd/system/rover-control.service << EOF
[Unit]
Description=M.A.R.K. Rover Control System
After=network.target rtk-ntrip.service
Requires=rtk-ntrip.service

[Service]
Type=simple
User=root
WorkingDirectory=$ROVER_DIR
ExecStart=$PYTHON_EXEC main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✓ rover-control.service created"
echo ""

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload
echo "✓ Daemon reloaded"
echo ""

# Enable services
echo "Enabling services..."
systemctl enable rtk-ntrip.service
systemctl enable rover-control.service
echo "✓ Services enabled (will start on boot)"
echo ""

# Display status
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Service status:"
echo "  RTK/NTRIP:  systemctl status rtk-ntrip.service"
echo "  Rover:      systemctl status rover-control.service"
echo ""
echo "Start services:"
echo "  sudo systemctl start rtk-ntrip.service"
echo "  sudo systemctl start rover-control.service"
echo ""
echo "View logs:"
echo "  sudo journalctl -u rtk-ntrip.service -f"
echo "  sudo journalctl -u rover-control.service -f"
echo ""
echo "IMPORTANT:"
echo "  1. Start rtk-ntrip.service first and wait for RTK fix"
echo "  2. Then start rover-control.service"
echo ""
