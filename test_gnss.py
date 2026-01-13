"""
GNSS Hardware Test Script
Tests u-blox ZED-F9P connection and RTK fix quality
"""

import sys
import time
import json
import logging
from utils import setup_logging
from gnss_module import GNSSModule

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Test GNSS module
    """
    logger.info("="*60)
    logger.info("GNSS Module Test")
    logger.info("="*60)
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return
    
    # Initialize GNSS
    serial_config = config.get('serial_ports', {})
    ntrip_config = config.get('ntrip', {})
    kalman_config = config.get('kalman_filter', {})
    
    # Get GNSS port (with auto-detection support)
    gnss_port = serial_config.get('gnss', '/dev/ttyACM0')
    
    # Auto-detect port if configured as "auto"
    if gnss_port == "auto":
        logger.info("🔍 Auto-detecting GNSS port...")
        from port_detector import auto_detect_ports
        gnss_detected, _ = auto_detect_ports()
        if gnss_detected:
            gnss_port = gnss_detected
            logger.info(f"✅ Auto-detected GNSS port: {gnss_port}")
        else:
            logger.error("❌ Auto-detection failed! No u-blox device found.")
            logger.error("   → Check USB connection")
            return
    
    gnss = GNSSModule(
        port=gnss_port,  # Use detected or configured port
        baudrate=serial_config.get('gnss_baudrate', 115200),
        kalman_config=kalman_config
    )
    
    # Connect
    if not gnss.connect():
        logger.error("Failed to connect to GNSS")
        return
    
    logger.info("Connected to GNSS successfully")
    logger.info("Reading data... (Press Ctrl+C to stop)")
    logger.info("")
    
    try:
        update_count = 0
        
        while True:
            # Update GNSS
            if gnss.update():
                update_count += 1
                
                # Get status
                status = gnss.get_status()
                
                # Display every update
                logger.info(f"Update #{update_count}")
                logger.info(f"  Position: {status['latitude']:.6f}, {status['longitude']:.6f}")
                logger.info(f"  Altitude: {status['altitude']:.2f} m")
                logger.info(f"  Fix Quality: {status['fix_quality_str']}")
                logger.info(f"  Satellites: {status['num_satellites']}")
                logger.info(f"  HDOP: {status['hdop']:.1f}")
                logger.info(f"  Speed: {status['speed_kmh']:.1f} km/h")
                
                # RTK status
                if gnss.has_rtk_fix():
                    logger.info("  ✅ RTK FIX ACTIVE!")
                else:
                    logger.warning("  ⚠️  RTK fix not available")
                
                # Filtered position
                logger.info(f"  Filtered: {status['filtered_lat']:.6f}, {status['filtered_lon']:.6f}")
                logger.info("")
            
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    
    finally:
        gnss.disconnect()
        logger.info("GNSS disconnected")


if __name__ == '__main__':
    main()
