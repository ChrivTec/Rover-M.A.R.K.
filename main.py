"""
M.A.R.K. Rover Control System - Main Module
Autonomous navigation with GNSS/RTK + IMU
"""

import json
import logging
import time
import sys
import subprocess
from typing import Optional

# Import all modules
from utils import setup_logging
from config_validator import validate_config
from port_detector import auto_detect_ports, validate_port_configuration
from gnss_module import GNSSModule
from imu_module import IMUModule
from motor_module import MotorController
from waypoint_manager import WaypointManager, Waypoint
from rover_state import RoverStateMachine, RoverState
from navigator import Navigator
from connection_monitor import ConnectionMonitor
from rover_api import RoverAPI

logger = logging.getLogger(__name__)


class RoverControlSystem:
    """
    Main rover control system
    
    Orchestrates all modules and implements autonomous navigation logic
    """
    
    def __init__(self, config_file: str):
        """
        Initialize Rover Control System
        
        Args:
            config_file: Path to config.json
        """
        logger.info("="*60)
        logger.info("M.A.R.K. Rover Control System - Initialisierung")
        logger.info("="*60)
        
        # Validate and load configuration
        logger.info("📋 Validiere Konfiguration...")
        valid, self.config = validate_config(config_file)
        
        if not valid:
            logger.error("❌ Config-Validierung fehlgeschlagen!")
            logger.error("   → Prüfe config.json auf Fehler")
            logger.error("   → Details siehe Log-Ausgabe oben")
            sys.exit(1)
        
        logger.info("✅ Konfiguration erfolgreich geladen")
        
        # Initialize modules (hardware not connected yet)
        self.gnss: Optional[GNSSModule] = None
        self.imu: Optional[IMUModule] = None
        self.motors: Optional[MotorController] = None
        self.waypoint_manager = WaypointManager()
        self.state_machine = RoverStateMachine()
        self.navigator = Navigator(self.config)
        self.connection_monitor: Optional[ConnectionMonitor] = None
        
        # Control loop
        self.running = False
        self.loop_counter = 0
        
        logger.info("Rover Control System initialized")
    
    def initialize_hardware(self) -> bool:
        """
        Initialize and connect all hardware modules
        
        Returns:
            True if all hardware initialized successfully
        """
        logger.info("")
        logger.info("="*60)
        logger.info("⚙️  Hardware-Initialisierung")
        logger.info("="*60)
        
        # Get config sections
        serial_config = self.config.get('serial_ports', {})
        hardware_config = self.config.get('hardware', {})
        kalman_config = self.config.get('kalman_filter', {})
        
        # Auto-detect ports if needed
        gnss_port_config = serial_config.get('gnss')
        motor_port_config = serial_config.get('motor_controller')
        
        if not gnss_port_config or not motor_port_config or \
           gnss_port_config == "auto" or motor_port_config == "auto":
            logger.info("🔍 Automatische Port-Erkennung...")
            gnss_detected, motor_detected = auto_detect_ports()
            
            # Use detected ports as fallback
            gnss_port = gnss_port_config if gnss_port_config and gnss_port_config != "auto" else gnss_detected
            motor_port = motor_port_config if motor_port_config and motor_port_config != "auto" else motor_detected
        else:
            gnss_port = gnss_port_config
            motor_port = motor_port_config
        
        # Validate port configuration
        if not validate_port_configuration(gnss_port, motor_port):
            logger.error("❌ Port-Konfiguration ungültig!")
            logger.error("   → Führe aus: python3 setup_ports.py")
            return False
        
        try:
            # Initialize GNSS
            logger.info("")
            logger.info("📡 Verbinde GNSS...")
            self.gnss = GNSSModule(
                port=gnss_port,
                baudrate=serial_config.get('gnss_baudrate', 115200),
                kalman_config=kalman_config,
                hardware_config=hardware_config
            )
            if not self.gnss.connect():
                logger.error("❌ GNSS-Verbindung fehlgeschlagen!")
                logger.error(f"   → Port: {gnss_port}")
                logger.error("   → Überprüfe USB-Verbindung")
                logger.error("   → Test mit: python3 test_gnss.py")
                return False
            logger.info("✅ GNSS verbunden")
            
            # Initialize IMU
            logger.info("")
            logger.info("🧭 Verbinde IMU...")
            self.imu = IMUModule(
                i2c_bus=1,
                address=0x4A,
                ndof_mode=True
            )
            if not self.imu.connect():
                logger.error("❌ IMU-Verbindung fehlgeschlagen!")
                logger.error("   → I2C Adresse 0x4A")
                logger.error("   → Überprüfe I2C-Verkabelung (SDA, SCL, 3.3V, GND)")
                logger.error("   → I2C aktiviert? sudo raspi-config")
                logger.error("   → Test mit: sudo i2cdetect -y 1")
                logger.error("   → Test mit: python3 test_imu.py")
                return False
            logger.info("✅ IMU verbunden")
            
            # Initialize Motors
            logger.info("")
            logger.info("🤖 Verbinde Motor Controller...")
            self.motors = MotorController(
                port=motor_port,
                baudrate=serial_config.get('motor_baudrate', 38400),
                address=serial_config.get('roboclaw_address', 128),
                config=hardware_config
            )
            if not self.motors.connect():
                logger.error("❌ Motor Controller-Verbindung fehlgeschlagen!")
                logger.error(f"   → Port: {motor_port}")
                logger.error("   → Baudrate: 38400")
                logger.error("   → Adresse: 128 (0x80)")
                logger.error("   → Überprüfe USB-Verbindung")
                logger.error("   → Prüfe RoboClaw Einstellungen mit BasicMicro Motion Studio")
                logger.error("   → Test mit: python3 test_motors.py")
                return False
            logger.info("✅ Motor Controller verbunden")
            
            # Initialize Connection Monitor
            logger.info("")
            logger.info("🛡️  Starte GPS-Watchdog...")
            timeout = self.config.get('safety', {}).get('max_connection_loss_s', 30.0)
            self.connection_monitor = ConnectionMonitor(timeout_seconds=timeout)
            self.connection_monitor.start(emergency_callback=self._connection_lost_callback)
            logger.info(f"✅ Watchdog aktiv (Timeout: {timeout}s)")
            
            logger.info("")
            logger.info("="*60)
            logger.info("✅ Alle Hardware-Module erfolgreich initialisiert!")
            logger.info("="*60)
            return True
            
        except Exception as e:
            logger.error(f"Hardware initialization error: {e}")
            return False
    
    def shutdown_hardware(self) -> None:
        """
        Disconnect all hardware modules
        """
        logger.info("Shutting down hardware...")
        
        if self.connection_monitor:
            self.connection_monitor.stop()
        
        if self.motors:
            self.motors.stop()
            self.motors.disconnect()
        
        if self.gnss:
            self.gnss.disconnect()
        
        if self.imu:
            self.imu.disconnect()
        
        logger.info("Hardware shutdown complete")
    
    def check_rtk_status(self) -> bool:
        """
        Check if RTK/NTRIP daemon is running
        
        Returns:
            True if str2str is running
        """
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'rtk-ntrip.service'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip() == 'active':
                return True
            else:
                logger.warning("RTK/NTRIP daemon (str2str) is not running!")
                logger.warning("Start with: sudo systemctl start rtk-ntrip.service")
                return False
                
        except Exception as e:
            logger.warning(f"Could not check RTK daemon status: {e}")
            return False
    
    def check_safety_conditions(self) -> bool:
        """
        Check safety conditions (GPS fix, satellites, HDOP, RTK)
        
        Returns:
            True if all safety conditions met
        """
        if not self.gnss:
            return False
        
        safety_config = self.config.get('safety', {})
        
        # Check GPS fix
        if not self.gnss.has_valid_fix():
            logger.warning("No valid GPS fix")
            return False
        
        # Check satellites
        min_sats = safety_config.get('min_satellites', 6)
        if self.gnss.num_satellites < min_sats:
            logger.warning(f"Insufficient satellites: {self.gnss.num_satellites} < {min_sats}")
            return False
        
        # Check HDOP
        max_hdop = safety_config.get('max_hdop', 5.0)
        if self.gnss.hdop > max_hdop:
            logger.warning(f"HDOP too high: {self.gnss.hdop} > {max_hdop}")
            return False
        
        # Check RTK Quality (if configured)
        min_rtk_quality = safety_config.get('min_rtk_quality', None)
        if min_rtk_quality is not None:
            current_quality = self.gnss.fix_quality
            if current_quality < min_rtk_quality:
                quality_str = self.gnss.get_fix_quality_str()
                logger.warning(f"RTK quality insufficient: {quality_str} (quality {current_quality} < {min_rtk_quality})")
                
                # Emergency RTK Recovery: Stop if RTK lost during driving
                if safety_config.get('rtk_loss_stop_enabled', True):
                    current_state = self.state_machine.get_state()
                    if current_state in [RoverState.DRIVING, RoverState.ROTATING]:
                        logger.critical("⚠️ RTK VERLOREN WÄHREND FAHRT! Emergency Stop!")
                        self.state_machine.emergency_stop(f"RTK verloren: {quality_str}")
                
                return False
        
        # Legacy RTK check (backwards compatibility)
        require_rtk = safety_config.get('require_rtk', True)
        if require_rtk and min_rtk_quality is None:
            if not self.gnss.has_rtk_fix():
                logger.warning(f"RTK fix required but not available (quality: {self.gnss.get_fix_quality_str()})")
                return False
        
        return True
    
    def update_sensors(self) -> None:
        """
        Update all sensors in correct order
        
        Order: IMU → GNSS (uses heading for antenna offset)
        """
        # Update IMU
        if self.imu:
            self.imu.update()
        
        # Update GNSS with current heading for antenna offset correction
        if self.gnss and self.imu:
            heading = self.imu.get_heading()
            self.gnss.update(heading)
    
    def execute_state_machine(self) -> None:
        """
        Execute state machine logic based on current state
        """
        current_state = self.state_machine.get_state()
        
        if current_state == RoverState.IDLE:
            self._handle_idle()
        
        elif current_state == RoverState.ROTATING:
            self._handle_rotating()
        
        elif current_state == RoverState.DRIVING:
            self._handle_driving()
        
        elif current_state == RoverState.REACHED_WAYPOINT:
            self._handle_reached_waypoint()
        
        elif current_state == RoverState.MISSION_COMPLETE:
            self._handle_mission_complete()
        
        elif current_state in [RoverState.ERROR, RoverState.EMERGENCY_STOP]:
            self._handle_error_stop()
    
    def _handle_idle(self) -> None:
        """
        Handle IDLE state: Load first waypoint and start mission
        """
        if not self.waypoint_manager.has_waypoints():
            return
        
        waypoint = self.waypoint_manager.get_current_waypoint()
        if waypoint:
            # Set target and line segment
            lat, lon = self.gnss.get_position(filtered=True)
            self.navigator.set_target(waypoint.lat, waypoint.lon)
            self.navigator.set_line_segment(lat, lon, waypoint.lat, waypoint.lon)
            self.navigator.reset_controllers()
            
            logger.info(f"Starting mission to waypoint 1/{len(self.waypoint_manager.waypoints)}")
            self.state_machine.set_state(RoverState.ROTATING, "Starting mission")
    
    def _handle_rotating(self) -> None:
        """
        Handle ROTATING state: Align heading to target bearing
        """
        lat, lon = self.gnss.get_position(filtered=True)
        heading = self.imu.get_heading()
        bearing = self.navigator.get_bearing_to_target(lat, lon)
        
        # Adapt PID to GPS quality
        self.navigator.adapt_pid_to_gps_quality(
            self.gnss.get_fix_quality_str(),
            self.gnss.hdop
        )
        
        if self.navigator.is_heading_aligned(heading, bearing):
            # Heading aligned, start driving
            logger.info("Heading aligned, starting driving")
            self.navigator.reset_controllers()
            self.state_machine.set_state(RoverState.DRIVING, "Heading aligned")
        else:
            # Calculate rotation command
            v_left, v_right = self.navigator.calculate_rotation_command(heading, bearing)
            self.motors.set_velocity(v_left, v_right)
    
    def _handle_driving(self) -> None:
        """
        Handle DRIVING state: Follow line to waypoint
        """
        lat, lon = self.gnss.get_position(filtered=True)
        heading = self.imu.get_heading()
        
        # Adapt PID to GPS quality (adaptive drift correction)
        self.navigator.adapt_pid_to_gps_quality(
            self.gnss.get_fix_quality_str(),
            self.gnss.hdop
        )
        
        # Check if waypoint reached
        if self.navigator.is_waypoint_reached(lat, lon):
            logger.info("Waypoint reached!")
            self.motors.stop()
            self.state_machine.set_state(RoverState.REACHED_WAYPOINT, "Waypoint reached")
            return
        
        # Get current waypoint for speed
        waypoint = self.waypoint_manager.get_current_waypoint()
        base_speed = waypoint.speed_ms if waypoint else 0.3
        
        # Calculate line-following command
        v_left, v_right = self.navigator.calculate_line_following_command(
            lat, lon, heading, base_speed
        )
        self.motors.set_velocity(v_left, v_right)
    
    def _handle_reached_waypoint(self) -> None:
        """
        Handle REACHED_WAYPOINT state: Advance to next waypoint or complete
        """
        if self.waypoint_manager.advance_waypoint():
            # More waypoints available
            waypoint = self.waypoint_manager.get_current_waypoint()
            if waypoint:
                lat, lon = self.gnss.get_position(filtered=True)
                self.navigator.set_target(waypoint.lat, waypoint.lon)
                self.navigator.set_line_segment(lat, lon, waypoint.lat, waypoint.lon)
                self.navigator.reset_controllers()
                
                idx, total = self.waypoint_manager.get_progress()
                logger.info(f"Next waypoint: {idx + 1}/{total}")
                self.state_machine.set_state(RoverState.ROTATING, "Next waypoint")
        else:
            # Mission complete
            logger.info("Mission complete!")
            self.state_machine.set_state(RoverState.MISSION_COMPLETE, "All waypoints reached")
    
    def _handle_mission_complete(self) -> None:
        """
        Handle MISSION_COMPLETE state: Stop rover
        """
        self.motors.stop()
        self.running = False
    
    def _handle_error_stop(self) -> None:
        """
        Handle ERROR/EMERGENCY_STOP states: Motors stopped
        """
        self.motors.stop()
    
    def _connection_lost_callback(self, reason: str) -> None:
        """
        Callback for connection monitor timeout
        
        Args:
            reason: Timeout reason
        """
        logger.critical(f"Connection lost callback: {reason}")
        self.state_machine.emergency_stop(reason)
    
    def log_status(self) -> None:
        """
        Log comprehensive rover status
        """
        if not self.gnss or not self.imu:
            return
        
        lat, lon = self.gnss.get_position(filtered=True)
        heading = self.imu.get_heading()
        state = self.state_machine.get_state()
        
        logger.info(f"State: {state.value} | "
                   f"Pos: {lat:.6f}, {lon:.6f} | "
                   f"Heading: {heading:.1f}° | "
                   f"Fix: {self.gnss.get_fix_quality_str()} | "
                   f"Sats: {self.gnss.num_satellites} | "
                   f"HDOP: {self.gnss.hdop:.1f}")
    
    def run(self, waypoint_file: str) -> None:
        """
        Main control loop (10 Hz)
        
        Args:
            waypoint_file: Path to waypoints JSON file
        """
        logger.info("="*60)
        logger.info("M.A.R.K. Rover Control System Starting")
        logger.info("="*60)
        
        # Check RTK daemon status
        self.check_rtk_status()
        
        # Initialize hardware
        if not self.initialize_hardware():
            logger.error("Hardware initialization failed")
            return
        
        # Load waypoints
        if not self.waypoint_manager.load_waypoints(waypoint_file):
            logger.error(f"Failed to load waypoints from {waypoint_file}")
            self.shutdown_hardware()
            return
        
        # Main loop
        self.running = True
        self.loop_counter = 0
        loop_rate = self.config.get('navigation', {}).get('update_rate_hz', 10)
        loop_period = 1.0 / loop_rate
        
        logger.info(f"Starting main loop at {loop_rate} Hz")
        logger.info("="*60)
        
        try:
            while self.running:
                t_start = time.time()
                
                # 1. Update sensors
                self.update_sensors()
                
                # 2. Ping connection monitor
                if self.connection_monitor:
                    self.connection_monitor.ping()
                
                # 3. Check safety conditions
                if not self.check_safety_conditions():
                    if self.state_machine.is_operational():
                        logger.warning("Safety conditions not met")
                        # Don't emergency stop immediately, just log warning
                
                # 4. Execute state machine
                self.execute_state_machine()
                
                # 5. Periodic logging and RTK check
                self.loop_counter += 1
                if self.loop_counter % 20 == 0:  # Every 2 seconds at 10Hz
                    self.log_status()
                    
                if self.loop_counter % 100 == 0:  # Every 10 seconds
                    self.check_rtk_status()
                
                # 6. Sleep to maintain loop rate
                t_elapsed = time.time() - t_start
                sleep_time = max(0, loop_period - t_elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
        
        finally:
            logger.info("Shutting down...")
            self.shutdown_hardware()
            logger.info("Shutdown complete")
    
    # API interface methods
    
    def load_mission(self, route_file: str) -> bool:
        """
        Load mission from route file (called by API)
        
        Args:
            route_file: Path to route JSON
        
        Returns:
            True if loaded successfully
        """
        success = self.waypoint_manager.load_waypoints(route_file)
        if success:
            self.state_machine.set_state(RoverState.IDLE, "Mission loaded")
        return success
    
    def gentle_stop(self) -> None:
        """
        Gentle stop - return to IDLE (called by API)
        """
        self.motors.stop()
        self.state_machine.set_state(RoverState.IDLE, "Stopped by user")
    
    def emergency_stop(self, reason: str = "API emergency stop") -> None:
        """
        Emergency stop (called by API)
        
        Args:
            reason: Reason for emergency stop
        """
        self.state_machine.emergency_stop(reason)
        self.motors.stop()
    
    def set_motor_speeds(self, left_speed: float, right_speed: float) -> None:
        """
        Set motor speeds directly (for manual control)
        
        Args:
            left_speed: Left motor speed (-1.0 to 1.0)
            right_speed: Right motor speed (-1.0 to 1.0)
        """
        if self.motors:
            # Convert normalized speed to velocity
            max_vel = self.motors.max_velocity if hasattr(self.motors, 'max_velocity') else 0.25
            left_vel = left_speed * max_vel
            right_vel = right_speed * max_vel
            self.motors.set_velocity(left_vel, right_vel)
    
    def get_status(self) -> dict:
        """
        Get basic status (called by API)
        
        Returns:
            Status dictionary
        """
        return {
            'state': self.state_machine.get_state().value,
            'error': self.state_machine.error_message,
            'operational': self.state_machine.is_operational()
        }
    
    def get_telemetry(self) -> dict:
        """
        Get full telemetry (called by API)
        
        Returns:
            Comprehensive telemetry dictionary
        """
        lat, lon = self.gnss.get_position(filtered=True) if self.gnss else (0.0, 0.0)
        heading = self.imu.get_heading() if self.imu else 0.0
        
        idx, total = self.waypoint_manager.get_progress()
        
        motor_status = self.motors.get_status() if self.motors else {}
        
        return {
            'timestamp': time.time(),
            'state': self.state_machine.get_state().value,
            'position': {
                'lat': lat,
                'lon': lon
            },
            'heading_deg': heading,
            'speed_ms': 0.0,  # TODO: Calculate from GPS velocity
            'current_waypoint': {
                'index': idx,
                'total': total
            },
            'gnss': {
                'fix_quality': self.gnss.get_fix_quality_str() if self.gnss else 'Unknown',
                'num_satellites': self.gnss.num_satellites if self.gnss else 0,
                'hdop': self.gnss.hdop if self.gnss else 99.9
            },
            'motors': {
                'left_speed_ms': 0.0,  # TODO: Track motor speeds
                'right_speed_ms': 0.0,
                'left_current_a': motor_status.get('left_current_a'),
                'right_current_a': motor_status.get('right_current_a')
            },
            'battery_v': motor_status.get('battery_v'),
            'cross_track_error_m': self.navigator.current_cte if self.navigator else 0.0,
            'error': self.state_machine.error_message
        }


def main():
    """
    Main entry point
    """
    # Setup logging
    setup_logging(level=logging.INFO)
    
    # Configuration and waypoint files
    config_file = 'config.json'
    waypoint_file = 'waypoints.json'
    
    # Create rover control system
    rover = RoverControlSystem(config_file)
    
    # Start API server in background
    api = RoverAPI(rover, host='0.0.0.0', port=5000)
    api.start()
    
    # Run main control loop
    rover.run(waypoint_file)


if __name__ == '__main__':
    main()
