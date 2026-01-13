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
    -in ntrip://nw-9112470:123ABCde@sapos-nw-ntrip.de:2101/VRS_3_4G_NW \\
    -p 50.9333833 6.9885841 0 \\
    -n 1 \\
    -out serial://ttyACM1:115200
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
cat > /etc/systemd/system/rover-control.service << EOF
[Unit]
Description=M.A.R.K. Rover Control System
After=network.target rtk-ntrip.service
Requires=rtk-ntrip.service

[Service]
Type=simple
User=root
WorkingDirectory=$ROVER_DIR
ExecStart=/usr/bin/python3 main.py
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
