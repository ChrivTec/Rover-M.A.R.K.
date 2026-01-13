"""
IMU Hardware Test Script
Tests BNO085 connection and heading output
"""

import sys
import time
import logging
from utils import setup_logging
from imu_module import IMUModule

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Test IMU module
    """
    logger.info("="*60)
    logger.info("IMU Module Test (BNO085)")
    logger.info("="*60)
    
    # Initialize IMU
    imu = IMUModule(
        i2c_bus=1,
        address=0x4A,
        ndof_mode=True
    )
    
    # Connect
    if not imu.connect():
        logger.error("Failed to connect to IMU")
        logger.error("Make sure BNO085 is connected on I2C bus 1, address 0x4A")
        logger.error("Check with: i2cdetect -y 1")
        return
    
    logger.info("Connected to IMU successfully")
    logger.info("Reading orientation data... (Press Ctrl+C to stop)")
    logger.info("")
    
    try:
        update_count = 0
        
        while True:
            # Update IMU
            if imu.update():
                update_count += 1
                
                # Get orientation
                heading = imu.get_heading()
                roll = imu.get_roll()
                pitch = imu.get_pitch()
                
                # Display
                if update_count % 10 == 0:  # Every 10th update
                    logger.info(f"Update #{update_count}")
                    logger.info(f"  Heading: {heading:6.1f}° (0=North, 90=East)")
                    logger.info(f"  Roll:    {roll:6.1f}°")
                    logger.info(f"  Pitch:   {pitch:6.1f}°")
                    
                    # Visual compass direction
                    direction = get_compass_direction(heading)
                    logger.info(f"  Direction: {direction}")
                    logger.info("")
            
            time.sleep(0.1)  # 10 Hz
            
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    
    finally:
        imu.disconnect()
        logger.info("IMU disconnected")


def get_compass_direction(heading: float) -> str:
    """
    Convert heading to compass direction
    
    Args:
        heading: Heading in degrees (0-360)
    
    Returns:
        Compass direction string
    """
    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]
    
    idx = int((heading + 11.25) / 22.5) % 16
    return directions[idx]


if __name__ == '__main__':
    main()
