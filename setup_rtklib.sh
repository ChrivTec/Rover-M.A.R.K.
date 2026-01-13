#!/bin/bash
#
# RTKLIB str2str Installation Script
# Based on: https://forum.ardumower.de/threads/rtk-over-ntrip-mit-dem-raspberry-pi.25293/
#
# Usage: sudo bash setup_rtklib.sh
#

set -e  # Exit on error

echo "========================================"
echo "RTKLIB str2str Installation"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt update
apt upgrade -y

# Install dependencies
echo "📦 Installing build dependencies..."
apt install -y git build-essential

# Create rtklib directory
echo "📁 Creating rtklib directory..."
cd ~
mkdir -p rtklib
cd rtklib

# Clone RTKLIB repository (rtklibexplorer version - best for RTK)
echo "📥 Cloning RTKLIB repository..."
if [ -d "RTKLIB" ]; then
    echo "⚠️  RTKLIB directory already exists, pulling latest changes..."
    cd RTKLIB
    git pull
    cd ..
else
    git clone https://github.com/rtklibexplorer/RTKLIB.git
fi

# Build str2str
echo "🔨 Building str2str..."
cd RTKLIB/app/consapp/str2str/gcc
make clean
make

# Install to /usr/local/bin
echo "📥 Installing str2str to /usr/local/bin..."
cp str2str /usr/local/bin/str2str
chmod +x /usr/local/bin/str2str

# Verify installation
echo ""
echo "✅ Installation complete!"
echo ""
echo "Verifying installation:"
which str2str

if command -v str2str &> /dev/null; then
    echo "✅ str2str is installed correctly"
    echo ""
    echo "========================================"
    echo "Next Steps:"
    echo "========================================"
    echo ""
    echo "1. Test GPS connection:"
    echo "   str2str -in serial://ttyACM0:115200"
    echo "   (You should see NMEA data)"
    echo ""
    echo "2. Test NTRIP connection manually:"
    echo "   str2str -in ntrip://USER:PASS@sapos-nw-ntrip.de:2101/VRS_3_4G_NW \\"
    echo "           -p 50.9334 6.9886 0 \\"
    echo "           -n 1 \\"
    echo "           -out serial://ttyACM0:115200"
    echo ""
    echo "3. Setup systemd daemon:"
    echo "   sudo bash setup_rtk_daemon.sh"
    echo ""
else
    echo "❌ Installation failed!"
    exit 1
fi
