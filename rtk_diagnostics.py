#!/usr/bin/env python3
"""
RTK GPS Diagnostics Tool
Automatically detects u-blox ZED-F9P port and monitors RTK fix status
"""

import serial
import serial.tools.list_ports
import time
import sys
import argparse
from datetime import datetime
from typing import Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def find_ublox_port() -> Optional[str]:
    """
    Auto-detect u-blox GPS module on serial ports
    Returns: Port name (e.g., '/dev/ttyACM0') or None
    """
    print(f"{Colors.OKCYAN}🔍 Searching for u-blox GPS module...{Colors.ENDC}")
    
    ports = serial.tools.list_ports.comports()
    
    # First: Try to find u-blox by VID (1546)
    for port in ports:
        if port.vid == 0x1546 or 'u-blox' in port.description.lower():
            print(f"{Colors.OKGREEN}✅ Found u-blox at: {port.device}{Colors.ENDC}")
            print(f"   Description: {port.description}")
            return port.device
    
    # Second: List all ACM/USB ports as candidates
    candidates = [p for p in ports if 'ACM' in p.device or 'USB' in p.device]
    
    if candidates:
        print(f"{Colors.WARNING}⚠️  u-blox not auto-detected. Available ports:{Colors.ENDC}")
        for i, port in enumerate(candidates):
            print(f"   {i+1}. {port.device} - {port.description}")
        
        try:
            choice = int(input(f"\n{Colors.BOLD}Select port number (or 0 to cancel): {Colors.ENDC}"))
            if 1 <= choice <= len(candidates):
                return candidates[choice-1].device
        except (ValueError, KeyboardInterrupt):
            pass
    
    print(f"{Colors.FAIL}❌ No suitable port found!{Colors.ENDC}")
    return None


def parse_gga(sentence: str) -> dict:
    """
    Parse $GNGGA NMEA sentence
    Returns: dict with parsed data
    """
    data = {
        'fix_quality': 0,
        'num_satellites': 0,
        'hdop': 99.9,
        'latitude': 0.0,
        'longitude': 0.0,
        'altitude': 0.0
    }
    
    try:
        parts = sentence.split(',')
        if len(parts) < 15:
            return data
        
        # Fix quality (index 6)
        if parts[6]:
            data['fix_quality'] = int(parts[6])
        
        # Number of satellites (index 7)
        if parts[7]:
            data['num_satellites'] = int(parts[7])
        
        # HDOP (index 8)
        if parts[8]:
            data['hdop'] = float(parts[8])
        
        # Latitude (index 2-3)
        if parts[2] and parts[3]:
            lat_str = parts[2]
            lat_dir = parts[3]
            lat_deg = float(lat_str[:2])
            lat_min = float(lat_str[2:])
            data['latitude'] = lat_deg + (lat_min / 60.0)
            if lat_dir == 'S':
                data['latitude'] = -data['latitude']
        
        # Longitude (index 4-5)
        if parts[4] and parts[5]:
            lon_str = parts[4]
            lon_dir = parts[5]
            lon_deg = float(lon_str[:3])
            lon_min = float(lon_str[3:])
            data['longitude'] = lon_deg + (lon_min / 60.0)
            if lon_dir == 'W':
                data['longitude'] = -data['longitude']
        
        # Altitude (index 9)
        if parts[9]:
            data['altitude'] = float(parts[9])
        
    except (ValueError, IndexError):
        pass
    
    return data


def get_fix_quality_string(fix: int) -> Tuple[str, str]:
    """
    Convert fix quality code to human-readable string and color
    Returns: (string, color_code)
    """
    quality_map = {
        0: ('Invalid', Colors.FAIL),
        1: ('GPS Standard', Colors.WARNING),
        2: ('DGPS', Colors.OKCYAN),
        3: ('PPS', Colors.OKCYAN),
        4: ('RTK Fixed', Colors.OKGREEN),
        5: ('RTK Float', Colors.OKBLUE),
        6: ('Estimated', Colors.WARNING)
    }
    return quality_map.get(fix, ('Unknown', Colors.FAIL))


def monitor_gps(port: str, baudrate: int = 115200, duration: Optional[int] = None):
    """
    Monitor GPS data from serial port
    
    Args:
        port: Serial port device
        baudrate: Baud rate (default 115200)
        duration: Max duration in seconds (None = infinite)
    """
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}RTK GPS Monitor{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    print(f"Port: {port}")
    print(f"Baudrate: {baudrate}")
    print(f"Duration: {'infinite' if duration is None else f'{duration}s'}")
    print(f"\n{Colors.BOLD}Press Ctrl+C to stop{Colors.ENDC}\n")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1.0)
        print(f"{Colors.OKGREEN}✅ Connected to GPS module{Colors.ENDC}\n")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Failed to connect: {e}{Colors.ENDC}")
        return
    
    start_time = time.time()
    update_count = 0
    last_fix = None
    
    try:
        while True:
            # Check duration
            if duration and (time.time() - start_time) > duration:
                print(f"\n{Colors.WARNING}⏱️  Duration limit reached{Colors.ENDC}")
                break
            
            # Read line
            try:
                line = ser.readline().decode('ascii', errors='ignore').strip()
            except:
                continue
            
            if not line or not line.startswith('$'):
                continue
            
            # Parse GGA sentences
            if '$GNGGA' in line or '$GPGGA' in line:
                data = parse_gga(line)
                
                if data['fix_quality'] > 0:
                    update_count += 1
                    
                    # Get fix quality info
                    fix_str, fix_color = get_fix_quality_string(data['fix_quality'])
                    
                    # Detect fix change
                    if last_fix != data['fix_quality']:
                        if last_fix is not None:
                            print(f"\n{Colors.BOLD}🔄 FIX CHANGED: {get_fix_quality_string(last_fix)[0]} → {fix_str}{Colors.ENDC}\n")
                        last_fix = data['fix_quality']
                    
                    # Print status
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"{Colors.BOLD}[{timestamp}] Update #{update_count}{Colors.ENDC}")
                    print(f"  Position:   {data['latitude']:.7f}°, {data['longitude']:.7f}°")
                    print(f"  Altitude:   {data['altitude']:.2f} m")
                    print(f"  Fix Quality: {fix_color}{fix_str} ({data['fix_quality']}){Colors.ENDC}")
                    print(f"  Satellites: {data['num_satellites']}")
                    print(f"  HDOP:       {data['hdop']:.1f}")
                    
                    # RTK status indicator
                    if data['fix_quality'] == 4:
                        print(f"  {Colors.OKGREEN}✅ RTK FIXED - Centimeter accuracy!{Colors.ENDC}")
                    elif data['fix_quality'] == 5:
                        print(f"  {Colors.OKBLUE}🔵 RTK FLOAT - Good accuracy (~10cm){Colors.ENDC}")
                    elif data['fix_quality'] > 0:
                        print(f"  {Colors.WARNING}⚠️  Waiting for RTK corrections...{Colors.ENDC}")
                    
                    print()
    
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⏹️  Stopped by user{Colors.ENDC}")
    
    finally:
        ser.close()
        print(f"\n{Colors.OKCYAN}Disconnected from GPS{Colors.ENDC}")
        print(f"Total updates: {update_count}")
        print(f"Duration: {time.time() - start_time:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        description='RTK GPS Diagnostics Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect port and monitor
  python3 rtk_diagnostics.py
  
  # Use specific port
  python3 rtk_diagnostics.py --port /dev/ttyACM0
  
  # Monitor for 5 minutes
  python3 rtk_diagnostics.py --duration 300
        """
    )
    
    parser.add_argument(
        '--port', '-p',
        type=str,
        default=None,
        help='Serial port (auto-detect if not specified)'
    )
    
    parser.add_argument(
        '--baudrate', '-b',
        type=int,
        default=115200,
        help='Baud rate (default: 115200)'
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=int,
        default=None,
        help='Monitoring duration in seconds (default: infinite)'
    )
    
    args = parser.parse_args()
    
    # Find port
    port = args.port
    if not port:
        port = find_ublox_port()
        if not port:
            sys.exit(1)
    
    # Monitor
    monitor_gps(port, args.baudrate, args.duration)


if __name__ == '__main__':
    main()
