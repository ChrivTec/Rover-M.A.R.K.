"""
Configuration Validator for M.A.R.K. Rover
Validates config.json for errors and missing values
"""

import json
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Validates configuration file for rover system
    """
    
    def __init__(self, config_file: str = 'config.json'):
        """
        Initialize validator
        
        Args:
            config_file: Path to config.json
        """
        self.config_file = config_file
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> Tuple[bool, dict]:
        """
        Validate configuration file
        
        Returns:
            Tuple of (is_valid, config_dict)
        """
        self.errors = []
        self.warnings = []
        
        # Load config
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            self.errors.append(f"❌ Config-Datei nicht gefunden: {self.config_file}")
            return False, {}
        except json.JSONDecodeError as e:
            self.errors.append(f"❌ JSON-Fehler in {self.config_file}: {e}")
            return False, {}
        
        # Validate sections
        self._validate_hardware(config)
        self._validate_serial_ports(config)
        self._validate_ntrip(config)
        self._validate_navigation(config)
        self._validate_control(config)
        self._validate_kalman(config)
        self._validate_safety(config)
        
        # Report results
        if self.errors:
            logger.error("❌ Config-Validierung fehlgeschlagen!")
            for error in self.errors:
                logger.error(f"  {error}")
            return False, config
        
        if self.warnings:
            logger.warning("⚠️  Config-Warnungen:")
            for warning in self.warnings:
                logger.warning(f"  {warning}")
        
        logger.info("✅ Config-Validierung erfolgreich")
        return True, config
    
    def _validate_hardware(self, config: dict) -> None:
        """Validate hardware section"""
        if 'hardware' not in config:
            self.errors.append("❌ Sektion 'hardware' fehlt in config.json")
            return
        
        hw = config['hardware']
        required = ['wheel_diameter_m', 'wheelbase_m', 'max_rpm']
        
        for key in required:
            if key not in hw:
                self.errors.append(f"❌ hardware.{key} fehlt")
            elif not isinstance(hw[key], (int, float)) or hw[key] <= 0:
                self.errors.append(f"❌ hardware.{key} muss positive Zahl sein (ist: {hw[key]})")
        
        # Plausibility checks
        if 'wheel_diameter_m' in hw and hw['wheel_diameter_m'] > 0.5:
            self.warnings.append(f"⚠️  Rad-Durchmesser sehr groß: {hw['wheel_diameter_m']}m")
        
        if 'max_rpm' in hw and hw['max_rpm'] > 200:
            self.warnings.append(f"⚠️  Max RPM sehr hoch: {hw['max_rpm']}")
    
    def _validate_serial_ports(self, config: dict) -> None:
        """Validate serial ports section"""
        if 'serial_ports' not in config:
            self.errors.append("❌ Sektion 'serial_ports' fehlt")
            return
        
        sp = config['serial_ports']
        
        # Check baudrates
        if 'gnss_baudrate' in sp and sp['gnss_baudrate'] != 115200:
            self.warnings.append(f"⚠️  GNSS Baudrate nicht standard (sollte 115200 sein): {sp['gnss_baudrate']}")
        
        if 'motor_baudrate' in sp and sp['motor_baudrate'] != 38400:
            self.warnings.append(f"⚠️  Motor Baudrate nicht standard (sollte 38400 sein): {sp['motor_baudrate']}")
        
        # RoboClaw address
        if 'roboclaw_address' in sp:
            addr = sp['roboclaw_address']
            if addr < 128 or addr > 135:
                self.warnings.append(f"⚠️  RoboClaw Adresse außerhalb Standard-Range (128-135): {addr}")
    
    def _validate_ntrip(self, config: dict) -> None:
        """Validate NTRIP section"""
        if 'ntrip' not in config:
            self.errors.append("❌ Sektion 'ntrip' fehlt")
            return
        
        ntrip = config['ntrip']
        required = ['server', 'port', 'mountpoint', 'username', 'password', 'ref_lat', 'ref_lon']
        
        for key in required:
            if key not in ntrip:
                self.errors.append(f"❌ ntrip.{key} fehlt")
            elif isinstance(ntrip[key], str) and not ntrip[key]:
                self.errors.append(f"❌ ntrip.{key} ist leer")
        
        # Validate coordinates
        if 'ref_lat' in ntrip:
            lat = ntrip['ref_lat']
            if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
                self.errors.append(f"❌ ntrip.ref_lat ungültig (muss -90 bis +90 sein): {lat}")
        
        if 'ref_lon' in ntrip:
            lon = ntrip['ref_lon']
            if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
                self.errors.append(f"❌ ntrip.ref_lon ungültig (muss -180 bis +180 sein): {lon}")
        
        # Check if coordinates are default (should be changed)
        if ntrip.get('ref_lat') == 50.9379 and ntrip.get('ref_lon') == 6.9580:
            self.warnings.append("⚠️  NTRIP Koordinaten sind Standard-Werte - bitte an deinen Standort anpassen!")
    
    def _validate_navigation(self, config: dict) -> None:
        """Validate navigation section"""
        if 'navigation' not in config:
            self.errors.append("❌ Sektion 'navigation' fehlt")
            return
        
        nav = config['navigation']
        
        # Speed checks
        if 'max_speed_ms' in nav and nav['max_speed_ms'] <= 0:
            self.errors.append(f"❌ navigation.max_speed_ms muss positiv sein: {nav['max_speed_ms']}")
        
        if 'max_speed_ms' in nav and nav['max_speed_ms'] > 2.0:
            self.warnings.append(f"⚠️  Max Speed sehr hoch ({nav['max_speed_ms']} m/s = {nav['max_speed_ms']*3.6:.1f} km/h)")
        
        # Thresholds
        if 'waypoint_reached_threshold_m' in nav:
            thresh = nav['waypoint_reached_threshold_m']
            if thresh < 0.1:
                self.warnings.append(f"⚠️  Waypoint Threshold sehr klein ({thresh}m) - könnte zu Problemen führen")
            elif thresh > 1.0:
                self.warnings.append(f"⚠️  Waypoint Threshold sehr groß ({thresh}m) - könnte ungenau sein")
    
    def _validate_control(self, config: dict) -> None:
        """Validate control/PID section"""
        if 'control' not in config:
            self.errors.append("❌ Sektion 'control' fehlt")
            return
        
        ctrl = config['control']
        
        # Check PID configs
        for pid_name in ['steering_pid', 'cross_track_pid']:
            if pid_name not in ctrl:
                self.errors.append(f"❌ control.{pid_name} fehlt")
                continue
            
            pid = ctrl[pid_name]
            for param in ['kp', 'ki', 'kd', 'output_limit']:
                if param not in pid:
                    self.errors.append(f"❌ control.{pid_name}.{param} fehlt")
                elif not isinstance(pid[param], (int, float)):
                    self.errors.append(f"❌ control.{pid_name}.{param} muss Zahl sein")
            
            # Warn about extreme values
            if 'kp' in pid and pid['kp'] > 10:
                self.warnings.append(f"⚠️  {pid_name}.kp sehr hoch ({pid['kp']}) - könnte oszillieren")
    
    def _validate_kalman(self, config: dict) -> None:
        """Validate Kalman filter section"""
        if 'kalman_filter' not in config:
            self.errors.append("❌ Sektion 'kalman_filter' fehlt")
            return
        
        kf = config['kalman_filter']
        required = ['process_noise', 'measurement_noise_rtk_fixed', 
                   'measurement_noise_rtk_float', 'measurement_noise_gps']
        
        for key in required:
            if key not in kf:
                self.errors.append(f"❌ kalman_filter.{key} fehlt")
            elif not isinstance(kf[key], (int, float)) or kf[key] <= 0:
                self.errors.append(f"❌ kalman_filter.{key} muss positive Zahl sein")
    
    def _validate_safety(self, config: dict) -> None:
        """Validate safety section"""
        if 'safety' not in config:
            self.errors.append("❌ Sektion 'safety' fehlt")
            return
        
        safety = config['safety']
        
        # Satellite check
        if 'min_satellites' in safety:
            min_sats = safety['min_satellites']
            if min_sats < 4:
                self.errors.append(f"❌ safety.min_satellites zu niedrig (min 4): {min_sats}")
            elif min_sats > 12:
                self.warnings.append(f"⚠️  safety.min_satellites sehr hoch ({min_sats}) - könnte RTK verzögern")
        
        # HDOP check
        if 'max_hdop' in safety:
            hdop = safety['max_hdop']
            if hdop > 10:
                self.warnings.append(f"⚠️  safety.max_hdop sehr hoch ({hdop}) - GPS-Qualität könnte schlecht sein")
        
        # RTK requirement
        if 'require_rtk' in safety and not safety['require_rtk']:
            self.warnings.append("⚠️  safety.require_rtk = false - Rover fährt ohne RTK (ungenau!)")
        
        # Connection timeout
        if 'max_connection_loss_s' in safety:
            timeout = safety['max_connection_loss_s']
            if timeout < 10:
                self.warnings.append(f"⚠️  GPS Timeout sehr kurz ({timeout}s) - könnte zu häufigen Stops führen")
            elif timeout > 60:
                self.warnings.append(f"⚠️  GPS Timeout sehr lang ({timeout}s) - Sicherheitsrisiko!")
    
    def get_errors(self) -> List[str]:
        """Get all errors"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Get all warnings"""
        return self.warnings


def validate_config(config_file: str = 'config.json') -> Tuple[bool, dict]:
    """
    Validate configuration file
    
    Args:
        config_file: Path to config.json
    
    Returns:
        Tuple of (is_valid, config_dict)
    """
    validator = ConfigValidator(config_file)
    return validator.validate()


if __name__ == '__main__':
    # Test validation
    import sys
    from utils import setup_logging
    
    setup_logging()
    
    valid, config = validate_config()
    
    if not valid:
        print("\n❌ Fehler in config.json gefunden!")
        sys.exit(1)
    else:
        print("\n✅ config.json ist valide!")
        sys.exit(0)
