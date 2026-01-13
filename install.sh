#!/bin/bash
# M.A.R.K. Rover - Automatisches Installationsskript
# Führt komplette Installation auf Raspberry Pi 5 durch
# Verwendung: bash install.sh

set -e  # Bei Fehler abbrechen

echo "=========================================="
echo "M.A.R.K. Rover - Automatische Installation"
echo "=========================================="
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funktionen
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${YELLOW}→${NC} $1"; }

# Root-Check
if [ "$EUID" -eq 0 ]; then 
   print_error "Bitte NICHT als root ausführen! (kein sudo)"
   echo "Verwende: bash install.sh"
   exit 1
fi

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installation Directory: $INSTALL_DIR"
echo ""

# ============================================
# 1. System Update
# ============================================
print_info "System-Update durchführen..."
sudo apt update
sudo apt upgrade -y
print_success "System aktualisiert"
echo ""

# ============================================
# 2. System-Dependencies installieren
# ============================================
print_info "System-Dependencies installieren..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    build-essential \
    i2c-tools \
    minicom
print_success "System-Dependencies installiert"
echo ""

# ============================================
# 3. I2C aktivieren
# ============================================
print_info "I2C aktivieren..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
    print_success "I2C aktiviert (Neustart erforderlich!)"
else
    print_success "I2C bereits aktiviert"
fi

# I2C Kernel-Module laden
sudo modprobe i2c-dev || true
echo ""

# ============================================
# 4. RTKLIB (str2str) installieren
# ============================================
print_info "RTKLIB (str2str) installieren..."
if [ -f "/usr/local/bin/str2str" ]; then
    print_success "str2str bereits installiert"
else
    print_info "RTKLIB herunterladen und kompilieren..."
    cd /tmp
    rm -rf RTKLIB
    git clone https://github.com/rtklibexplorer/RTKLIB.git
    cd RTKLIB/app/consapp/str2str/gcc
    make
    sudo cp str2str /usr/local/bin/str2str
    sudo chmod +x /usr/local/bin/str2str
    cd "$INSTALL_DIR"
    print_success "str2str installiert"
fi
echo ""

# ============================================
# 5. Python Virtual Environment erstellen
# ============================================
print_info "Python Virtual Environment erstellen..."
cd "$INSTALL_DIR"
if [ -d "venv" ]; then
    print_info "venv existiert bereits, überspringen..."
else
    python3 -m venv venv
    print_success "Virtual Environment erstellt"
fi
echo ""

# ============================================
# 6. Python-Dependencies installieren
# ============================================
print_info "Python-Dependencies installieren..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Python-Packages installiert"
echo ""

# ============================================
# 7. Serial Port Berechtigungen
# ============================================
print_info "Serial Port Berechtigungen setzen..."
sudo usermod -aG dialout $USER
print_success "User zu dialout-Gruppe hinzugefügt"
print_info "WICHTIG: Logout/Login erforderlich für Serial-Zugriff!"
echo ""

# ============================================
# 8. Systemd Services installieren (optional)
# ============================================
echo ""
read -p "Möchtest du die systemd Services installieren? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Systemd Services installieren..."
    sudo bash setup_systemd.sh
    print_success "Services installiert"
else
    print_info "Systemd Services übersprungen"
fi
echo ""

# ============================================
# 9. USB-Geräte anzeigen
# ============================================
print_info "USB Serial Devices:"
ls -l /dev/ttyACM* 2>/dev/null || echo "  Keine /dev/ttyACM* Geräte gefunden"
ls -l /dev/ttyUSB* 2>/dev/null || echo "  Keine /dev/ttyUSB* Geräte gefunden"
echo ""

# ============================================
# 10. I2C-Geräte scannen
# ============================================
print_info "I2C-Geräte scannen (Bus 1):"
sudo i2cdetect -y 1 || print_error "I2C Scan fehlgeschlagen (evtl. kein Device verbunden)"
echo ""

# ============================================
# Installation abgeschlossen
# ============================================
echo ""
echo "=========================================="
echo -e "${GREEN}Installation abgeschlossen!${NC}"
echo "=========================================="
echo ""
echo "NÄCHSTE SCHRITTE:"
echo ""
echo "1. NEUSTART durchführen (für I2C):"
echo "   sudo reboot"
echo ""
echo "2. Nach Neustart: Hardware testen"
echo "   cd $INSTALL_DIR"
echo "   source venv/bin/activate"
echo "   python3 test_gnss.py    # GPS/RTK testen"
echo "   python3 test_imu.py     # BNO085 testen"
echo "   python3 test_motors.py  # RoboClaw testen"
echo ""
echo "3. RTK/NTRIP Daemon starten:"
echo "   sudo systemctl start rtk-ntrip.service"
echo "   sudo journalctl -u rtk-ntrip.service -f"
echo ""
echo "4. Rover starten:"
echo "   python3 main.py"
echo ""
echo "Siehe README.md für weitere Details!"
echo ""
