#!/usr/bin/env python3
"""
Serial Port Setup Helper
Erkennt automatisch USB Serial Devices und hilft bei Port-Konfiguration
"""

import os
import json
import serial
import serial.tools.list_ports

def detect_serial_ports():
    """Erkenne alle verfügbaren Serial Ports"""
    print("Suche nach Serial Ports...")
    print("-" * 60)
    
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("Keine Serial Ports gefunden!")
        return []
    
    devices = []
    for i, port in enumerate(ports):
        print(f"\n[{i}] {port.device}")
        print(f"    Beschreibung: {port.description}")
        print(f"    Hersteller:   {port.manufacturer}")
        print(f"    VID:PID:      {port.vid}:{port.pid}" if port.vid else "    VID:PID:      N/A")
        
        devices.append({
            'device': port.device,
            'description': port.description,
            'manufacturer': port.manufacturer
        })
    
    return devices


def test_port(port, baudrate):
    """Teste Verbindung zu einem Port"""
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        ser.close()
        return True
    except:
        return False


def identify_devices(devices):
    """Versuche automatisch Geräte zu identifizieren"""
    print("\n" + "=" * 60)
    print("AUTOMATISCHE GERÄTE-ERKENNUNG")
    print("=" * 60)
    
    gnss_port = None
    motor_port = None
    
    for dev in devices:
        desc = dev['description'].lower()
        manu = str(dev['manufacturer']).lower() if dev['manufacturer'] else ""
        
        # u-blox ZED-F9P Erkennung
        if 'u-blox' in desc or 'ublox' in desc or 'zed' in desc or 'gnss' in desc:
            print(f"\n✓ GNSS gefunden: {dev['device']}")
            print(f"  → {dev['description']}")
            gnss_port = dev['device']
        
        # RoboClaw / Generic USB Serial
        elif 'usb' in desc or 'serial' in desc or 'ch340' in desc or 'ftdi' in desc:
            if not gnss_port or dev['device'] != gnss_port:
                print(f"\n✓ Motor Controller gefunden: {dev['device']}")
                print(f"  → {dev['description']}")
                motor_port = dev['device']
    
    return gnss_port, motor_port


def update_config(gnss_port, motor_port):
    """Aktualisiere config.json mit erkannten Ports"""
    config_file = 'config.json'
    
    if not os.path.exists(config_file):
        print(f"\nFehler: {config_file} nicht gefunden!")
        return False
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Aktualisiere Ports
    if gnss_port:
        config['serial_ports']['gnss'] = gnss_port
    if motor_port:
        config['serial_ports']['motor_controller'] = motor_port
    
    # Backup erstellen
    backup_file = 'config.json.backup'
    with open(backup_file, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"\nBackup erstellt: {backup_file}")
    
    # Neue Config speichern
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ config.json aktualisiert:")
    print(f"  GNSS:  {gnss_port}")
    print(f"  Motor: {motor_port}")
    
    return True


def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("M.A.R.K. Rover - Serial Port Setup")
    print("=" * 60)
    print()
    
    # Erkenne Ports
    devices = detect_serial_ports()
    
    if not devices:
        print("\nKeine Serial Devices gefunden!")
        print("Stelle sicher, dass USB-Geräte angeschlossen sind.")
        return
    
    # Identifiziere Geräte
    gnss_port, motor_port = identify_devices(devices)
    
    # Manuelle Auswahl wenn nötig
    print("\n" + "=" * 60)
    print("PORT-KONFIGURATION")
    print("=" * 60)
    
    if not gnss_port:
        print("\n⚠ GNSS Port nicht automatisch erkannt")
        print("Wähle manuell:")
        for i, dev in enumerate(devices):
            print(f"  [{i}] {dev['device']} - {dev['description']}")
        idx = int(input("GNSS Port Index: "))
        gnss_port = devices[idx]['device']
    
    if not motor_port:
        print("\n⚠ Motor Controller Port nicht automatisch erkannt")
        print("Wähle manuell:")
        for i, dev in enumerate(devices):
            if dev['device'] != gnss_port:
                print(f"  [{i}] {dev['device']} - {dev['description']}")
        idx = int(input("Motor Port Index: "))
        motor_port = devices[idx]['device']
    
    # Test Verbindungen
    print("\n" + "=" * 60)
    print("VERBINDUNGS-TEST")
    print("=" * 60)
    
    print(f"\nTeste GNSS ({gnss_port} @ 115200)...")
    if test_port(gnss_port, 115200):
        print("  ✓ Verbindung erfolgreich")
    else:
        print("  ✗ Verbindung fehlgeschlagen")
    
    print(f"\nTeste Motor Controller ({motor_port} @ 38400)...")
    if test_port(motor_port, 38400):
        print("  ✓ Verbindung erfolgreich")
    else:
        print("  ✗ Verbindung fehlgeschlagen")
    
    # Config aktualisieren
    print("\n" + "=" * 60)
    update = input("\nconfig.json mit diesen Ports aktualisieren? (y/n): ")
    
    if update.lower() == 'y':
        update_config(gnss_port, motor_port)
        print("\n✓ Setup abgeschlossen!")
    else:
        print("\nAbgebrochen - config.json nicht geändert")
    
    print()


if __name__ == '__main__':
    main()
