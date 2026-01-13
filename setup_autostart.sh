#!/bin/bash
#
# Web-Interface Auto-Start Setup
# Erstellt systemd service für automatischen Start beim Hochfahren
#

set -e

echo "============================================================"
echo "M.A.R.K. Rover - Web-Interface Auto-Start Setup"
echo "============================================================"
echo ""

# Projekt-Verzeichnis
ROVER_DIR="$HOME/mark-rover"

if [ ! -d "$ROVER_DIR" ]; then
    echo "❌ ERROR: Rover directory not found: $ROVER_DIR"
    exit 1
fi

echo "📂 Rover Directory: $ROVER_DIR"
echo ""

# Erstelle systemd service
echo "📝 Creating systemd service..."

sudo tee /etc/systemd/system/mark-rover.service > /dev/null <<EOF
[Unit]
Description=M.A.R.K. Rover Web Interface
After=network-online.target rtk-ntrip.service
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$ROVER_DIR
ExecStart=/usr/bin/python3 $ROVER_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created: /etc/systemd/system/mark-rover.service"
echo ""

# Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling service for auto-start..."
sudo systemctl enable mark-rover

# Start service
echo "🚀 Starting service..."
sudo systemctl start mark-rover

# Wait a moment
sleep 2

# Check status
echo ""
echo "============================================================"
echo "Service Status"
echo "============================================================"
sudo systemctl status mark-rover --no-pager || true

echo ""
echo "============================================================"
echo "✅ Web-Interface Auto-Start Configured!"
echo "============================================================"
echo ""
echo "Service: mark-rover.service"
echo "Status: $(sudo systemctl is-active mark-rover)"
echo "Enabled: $(sudo systemctl is-enabled mark-rover)"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start mark-rover"
echo "  Stop:    sudo systemctl stop mark-rover"
echo "  Restart: sudo systemctl restart mark-rover"
echo "  Logs:    sudo journalctl -u mark-rover -f"
echo ""
echo "🌐 Web-Interface accessible at: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
