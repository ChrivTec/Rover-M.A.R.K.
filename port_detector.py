"""
Serial Port Auto-Detection Helper
Automatically detects GNSS and Motor Controller ports
"""

import serial.tools.list_ports
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


def detect_gnss_port() -> Optional[str]:
    """
    Auto-detect u-blox GNSS receiver port
    
    Returns:
        Port device path or None if not found
    """
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        desc = port.description.lower()
        manu = str(port.manufacturer).lower() if port.manufacturer else ""
        
        # u-blox ZED-F9P detection
        if any(keyword in desc or keyword in manu for keyword in 
               ['u-blox', 'ublox', 'zed', 'f9p', 'gnss', 'gps']):
            logger.info(f"✓ GNSS Auto-erkannt: {port.device} ({port.description})")
            return port.device
    
    logger.warning("⚠ GNSS Port nicht automatisch erkannt")
    return None


def detect_motor_controller_port(exclude_port: Optional[str] = None) -> Optional[str]:
    """
    Auto-detect RoboClaw motor controller port
    
    Args:
        exclude_port: Port to exclude (e.g., already identified GNSS port)
    
    Returns:
        Port device path or None if not found
    """
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if exclude_port and port.device == exclude_port:
            continue
        
        desc = port.description.lower()
        
        # RoboClaw / Generic USB Serial detection
        if any(keyword in desc for keyword in 
               ['roboclaw', 'usb', 'serial', 'ch340', 'ftdi', 'cp210']):
            logger.info(f"✓ Motor Controller Auto-erkannt: {port.device} ({port.description})")
            return port.device
    
    logger.warning("⚠ Motor Controller Port nicht automatisch erkannt")
    return None


def auto_detect_ports() -> Tuple[Optional[str], Optional[str]]:
    """
    Auto-detect both GNSS and Motor Controller ports
    
    Returns:
        Tuple of (gnss_port, motor_port)
    """
    logger.info("🔍 Starte automatische Port-Erkennung...")
    
    # Detect GNSS first
    gnss_port = detect_gnss_port()
    
    # Detect Motor Controller (exclude GNSS port)
    motor_port = detect_motor_controller_port(exclude_port=gnss_port)
    
    if gnss_port and motor_port:
        logger.info("✅ Beide Ports automatisch erkannt!")
    elif not gnss_port and not motor_port:
        logger.error("❌ Keine Ports automatisch erkannt!")
        logger.error("   → Schließe Hardware an und probiere erneut")
    elif not gnss_port:
        logger.warning("⚠ GNSS Port fehlt!")
    else:
        logger.warning("⚠ Motor Controller Port fehlt!")
    
    return gnss_port, motor_port


def list_all_serial_ports() -> List[dict]:
    """
    List all available serial ports
    
    Returns:
        List of port info dictionaries
    """
    ports = serial.tools.list_ports.comports()
    
    port_list = []
    logger.info("📋 Verfügbare Serial Ports:")
    for i, port in enumerate(ports):
        info = {
            'index': i,
            'device': port.device,
            'description': port.description,
            'manufacturer': port.manufacturer,
            'vid': port.vid,
            'pid': port.pid
        }
        port_list.append(info)
        logger.info(f"  [{i}] {port.device} - {port.description}")
    
    return port_list


def test_serial_connection(port: str, baudrate: int, timeout: float = 2.0) -> bool:
    """
    Test serial connection to port
    
    Args:
        port: Serial port device path
        baudrate: Baud rate to test
        timeout: Connection timeout
    
    Returns:
        True if connection successful
    """
    try:
        import serial
        ser = serial.Serial(port, baudrate, timeout=timeout)
        
        # Try to read some data (for GNSS, should see NMEA)
        data = ser.read(100)
        ser.close()
        
        if data:
            logger.info(f"✓ Port {port} @ {baudrate} baud: Daten empfangen ({len(data)} bytes)")
            return True
        else:
            logger.warning(f"⚠ Port {port} @ {baudrate} baud: Keine Daten empfangen")
            return True  # Still count as successful connection
            
    except Exception as e:
        logger.error(f"✗ Port {port} @ {baudrate} baud: Verbindung fehlgeschlagen ({e})")
        return False


def get_port_with_fallback(
    config_port: Optional[str],
    auto_detect_func,
    port_name: str,
    exclude_port: Optional[str] = None
) -> Optional[str]:
    """
    Get port with auto-detection fallback
    
    Args:
        config_port: Port from config.json (may be None or "auto")
        auto_detect_func: Function to call for auto-detection
        port_name: Human-readable port name (for logging)
        exclude_port: Port to exclude from auto-detection
    
    Returns:
        Port device path or None
    """
    # If config has specific port, use it
    if config_port and config_port != "auto":
        logger.info(f"📌 {port_name}: Verwende Port aus config.json: {config_port}")
        return config_port
    
    # Auto-detect
    logger.info(f"🔍 {port_name}: Automatische Erkennung...")
    if exclude_port:
        detected_port = auto_detect_func(exclude_port=exclude_port)
    else:
        detected_port = auto_detect_func()
    
    if detected_port:
        logger.info(f"✅ {port_name}: Auto-erkannt auf {detected_port}")
        return detected_port
    else:
        logger.error(f"❌ {port_name}: Nicht gefunden!")
        logger.error(f"   → Überprüfe Hardware-Verbindung")
        logger.error(f"   → Verfügbare Ports mit 'python3 setup_ports.py' anzeigen")
        return None


def validate_port_configuration(gnss_port: Optional[str], motor_port: Optional[str]) -> bool:
    """
    Validate that ports are configured and different
    
    Args:
        gnss_port: GNSS port
        motor_port: Motor controller port
    
    Returns:
        True if valid configuration
    """
    if not gnss_port:
        logger.error("❌ GNSS Port nicht konfiguriert!")
        return False
    
    if not motor_port:
        logger.error("❌ Motor Controller Port nicht konfiguriert!")
        return False
    
    if gnss_port == motor_port:
        logger.error(f"❌ GNSS und Motor Controller auf gleichem Port: {gnss_port}")
        logger.error("   → Ports müssen unterschiedlich sein!")
        return False
    
    logger.info(f"✅ Port-Konfiguration valide:")
    logger.info(f"   GNSS:  {gnss_port}")
    logger.info(f"   Motor: {motor_port}")
    return True
