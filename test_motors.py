"""
Motor Hardware Test Script
Tests RoboClaw motor controller connection and commands
"""

import sys
import time
import json
import logging
from utils import setup_logging
from motor_module import MotorController

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Test motor controller
    """
    logger.info("="*60)
    logger.info("Motor Controller Test (RoboClaw 2x15A)")
    logger.info("="*60)
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return
    
    # Initialize motors
    serial_config = config.get('serial_ports', {})
    hardware_config = config.get('hardware', {})
    
    motors = MotorController(
        port=serial_config.get('motor_controller', '/dev/ttyACM0'),
        baudrate=serial_config.get('motor_baudrate', 38400),
        address=serial_config.get('roboclaw_address', 128),
        config=hardware_config
    )
    
    # Connect
    if not motors.connect():
        logger.error("Failed to connect to RoboClaw")
        return
    
    logger.info("Connected to RoboClaw successfully")
    logger.info("")
    
    try:
        # Read status
        logger.info("Reading status...")
        status = motors.get_status()
        logger.info(f"  Battery: {status.get('battery_v', 'N/A')} V")
        logger.info(f"  Left Current: {status.get('left_current_a', 'N/A')} A")
        logger.info(f"  Right Current: {status.get('right_current_a', 'N/A')} A")
        logger.info(f"  Left Temp: {status.get('left_temp_c', 'N/A')} °C")
        logger.info(f"  Right Temp: {status.get('right_temp_c', 'N/A')} °C")
        logger.info("")
        
        # Interactive test
        logger.info("Motor Test Commands:")
        logger.info("  1 - Forward test (both motors 0.2 m/s for 2s)")
        logger.info("  2 - Backward test (both motors -0.2 m/s for 2s)")
        logger.info("  3 - Rotate left test (right motor only)")
        logger.info("  4 - Rotate right test (left motor only)")
        logger.info("  5 - Differential test (left/right at different speeds)")
        logger.info("  6 - SPOT-TURN LEFT (M1 backward, M2 forward)")
        logger.info("  7 - SPOT-TURN RIGHT (M1 forward, M2 backward)")
        logger.info("  8 - Slow spot-turn left (±0.1 m/s)")
        logger.info("  9 - M1 (LEFT) forward only")
        logger.info("  0 - M2 (RIGHT) backward only")
        logger.info("  s - Stop motors")
        logger.info("  q - Quit")
        logger.info("")
        
        while True:
            cmd = input("Enter command: ").strip().lower()
            
            if cmd == 'q':
                break
            
            elif cmd == 's':
                logger.info("Stopping motors...")
                motors.stop()
                logger.info("Motors stopped")
            
            elif cmd == '1':
                logger.info("Forward test: 0.2 m/s for 2s")
                motors.set_velocity(0.2, 0.2)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '2':
                logger.info("Backward test: -0.2 m/s for 2s")
                motors.set_velocity(-0.2, -0.2)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '3':
                logger.info("Rotate left: right motor 0.2 m/s for 2s")
                motors.set_velocity(0.0, 0.2)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '4':
                logger.info("Rotate right: left motor 0.2 m/s for 2s")
                motors.set_velocity(0.2, 0.0)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '5':
                logger.info("Differential test: L=0.15, R=0.25 m/s for 2s")
                motors.set_velocity(0.15, 0.25)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '6':
                logger.info("🔄 SPOT-TURN LEFT: M1=-0.2, M2=+0.2 for 2s")
                logger.info("   Expected: LEFT wheel backward, RIGHT wheel forward")
                logger.info("   Result: Rover rotates COUNTER-CLOCKWISE on spot")
                motors.set_velocity(-0.2, 0.2)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '7':
                logger.info("🔄 SPOT-TURN RIGHT: M1=+0.2, M2=-0.2 for 2s")
                logger.info("   Expected: LEFT wheel forward, RIGHT wheel backward")
                logger.info("   Result: Rover rotates CLOCKWISE on spot")
                motors.set_velocity(0.2, -0.2)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '8':
                logger.info("🔄 SLOW SPOT-TURN LEFT: M1=-0.1, M2=+0.1 for 3s")
                motors.set_velocity(-0.1, 0.1)
                time.sleep(3.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '9':
                logger.info("⚙️  M1 (LEFT) FORWARD: M1=+0.2, M2=0 for 2s")
                motors.set_velocity(0.2, 0.0)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            elif cmd == '0':
                logger.info("⚙️  M2 (RIGHT) BACKWARD: M1=0, M2=-0.2 for 2s")
                motors.set_velocity(0.0, -0.2)
                time.sleep(2.0)
                motors.stop()
                logger.info("Test complete")
            
            else:
                logger.warning("Unknown command")
            
            logger.info("")
            
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    
    finally:
        motors.stop()
        motors.disconnect()
        logger.info("Motors stopped and disconnected")


if __name__ == '__main__':
    main()
