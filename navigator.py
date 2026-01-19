"""
Navigator for M.A.R.K. Rover
Core navigation logic: bearing calculation, line-following, PID control
"""

import logging
import math
from typing import Tuple, Optional
from utils import (
    calculate_bearing,
    normalize_angle,
    calculate_cross_track_error,
    haversine_distance
)
from pid_controller import PIDController

logger = logging.getLogger(__name__)


class Navigator:
    """
    Navigation engine for autonomous rover control
    
    Implements:
    - Heading alignment (ROTATING phase)
    - Line-following with CTE correction (DRIVING phase)
    - Waypoint detection
    """
    
    def __init__(self, config: dict):
        """
        Initialize Navigator
        
        Args:
            config: Configuration dictionary with navigation and control params
        """
        self.config = config
        
        # Navigation parameters
        nav_config = config.get('navigation', {})
        self.waypoint_threshold = nav_config.get('waypoint_reached_threshold_m', 0.3)
        self.rotation_speed = nav_config.get('rotation_speed_ms', 0.2)
        self.heading_tolerance = nav_config.get('heading_tolerance_deg', 5.0)
        
        # Target coordinates
        self.target_lat = None
        self.target_lon = None
        
        # Line segment for line-following
        self.line_start_lat = None
        self.line_start_lon = None
        self.line_end_lat = None
        self.line_end_lon = None
        
        # PID controller for cross-track error
        pid_config = config.get('control', {}).get('cross_track_pid', {})
        self.base_kp = pid_config.get('kp', 2.0)
        self.base_ki = pid_config.get('ki', 0.1)
        self.base_kd = pid_config.get('kd', 0.5)
        
        self.pid = PIDController(
            kp=self.base_kp,
            ki=self.base_ki,
            kd=self.base_kd,
            output_limit=pid_config.get('output_limit', 0.5)
        )
        
        # GPS drift monitoring
        self.current_cte = 0.0
        self.max_cte = 0.0
        self.drift_alert_threshold = 1.0  # Alert if CTE > 1.0m
        
        # Adaptive PID enabled
        self.adaptive_pid_enabled = True
        self.current_gps_quality = 'unknown'
        
        logger.info("Navigator initialized with Adaptive PID")
        logger.info(f"Waypoint threshold: {self.waypoint_threshold}m")
        logger.info(f"Heading tolerance: {self.heading_tolerance}°")
        logger.info(f"Drift alert threshold: {self.drift_alert_threshold}m")
    
    def set_target(self, lat: float, lon: float) -> None:
        """
        Set target waypoint coordinates
        
        Args:
            lat: Target latitude
            lon: Target longitude
        """
        self.target_lat = lat
        self.target_lon = lon
        logger.info(f"Target set: {lat:.6f}, {lon:.6f}")
    
    def set_line_segment(
        self,
        lat_start: float,
        lon_start: float,
        lat_end: float,
        lon_end: float
    ) -> None:
        """
        Define ideal line segment for line-following
        
        Args:
            lat_start: Line start latitude
            lon_start: Line start longitude
            lat_end: Line end latitude
            lon_end: Line end longitude
        """
        self.line_start_lat = lat_start
        self.line_start_lon = lon_start
        self.line_end_lat = lat_end
        self.line_end_lon = lon_end
        
        distance = haversine_distance(lat_start, lon_start, lat_end, lon_end)
        logger.info(f"Line segment set: {distance:.1f}m")
    
    def get_bearing_to_target(self, lat: float, lon: float) -> float:
        """
        Calculate bearing from current position to target
        
        Args:
            lat: Current latitude
            lon: Current longitude
        
        Returns:
            Bearing in degrees (0-360°)
        """
        if self.target_lat is None or self.target_lon is None:
            logger.warning("Target not set")
            return 0.0
        
        bearing = calculate_bearing(lat, lon, self.target_lat, self.target_lon)
        return bearing
    
    def is_heading_aligned(
        self,
        heading: float,
        bearing: float,
        tolerance: Optional[float] = None
    ) -> bool:
        """
        Check if heading is aligned with target bearing
        
        Args:
            heading: Current heading (0-360°)
            bearing: Target bearing (0-360°)
            tolerance: Alignment tolerance in degrees (default: from config)
        
        Returns:
            True if aligned within tolerance
        """
        if tolerance is None:
            tolerance = self.heading_tolerance
        
        # Calculate angular difference
        error = normalize_angle(bearing - heading)
        
        return abs(error) < tolerance
    
    def calculate_rotation_command(
        self,
        heading: float,
        bearing: float
    ) -> Tuple[float, float]:
        """
        Calculate motor velocities for heading alignment (ROTATING phase)
        
        Tank-style rotation: One wheel forward, other backward
        Rotates around rover center point instead of around one wheel
        
        Args:
            heading: Current heading (0-360°)
            bearing: Target bearing (0-360°)
        
        Returns:
            Tuple of (v_left, v_right) in m/s
        """
        # Calculate heading error (-180 to +180)
        error = normalize_angle(bearing - heading)
        
        # Determine rotation direction
        # Tank-style: One wheel forward (+), other backward (-)
        if error > 0:
            # Error > 0 means Target is Right of Current (e.g. Current=0, Target=90 -> Error=90)
            # Need to turn RIGHT (CW)
            # Left wheel forward, right wheel backward
            v_left = +self.rotation_speed
            v_right = -self.rotation_speed
            logger.debug(f"Rotating RIGHT (CW): error={error:.1f}°, v_left={v_left}, v_right={v_right}")
        else:
            # Error < 0 means Target is Left of Current
            # Need to turn LEFT (CCW)
            # Left wheel backward, right wheel forward
            v_left = -self.rotation_speed
            v_right = +self.rotation_speed
            logger.debug(f"Rotating LEFT (CCW): error={error:.1f}°, v_left={v_left}, v_right={v_right}")
        
        return v_left, v_right
    
    def calculate_line_following_command(
        self,
        lat: float,
        lon: float,
        heading: float,
        base_speed: float
    ) -> Tuple[float, float]:
        """
        Calculate motor velocities for line-following (DRIVING phase)
        
        Algorithm:
        1. Calculate Cross-Track Error (CTE) - perpendicular distance to line
        2. PID converts CTE → speed modulation
        3. Apply differential speeds based on modulation
        
        Args:
            lat: Current latitude
            lon: Current longitude
            heading: Current heading (not used in CTE calculation)
            base_speed: Base driving speed in m/s
        
        Returns:
            Tuple of (v_left, v_right) in m/s
        
        Example:
            CTE = +0.12m (right of line)
            PID output = -0.10 (negative = need to turn left)
            v_left = 0.30 * (1 - 0.10) = 0.27 m/s (slower)
            v_right = 0.30 * (1 + 0.10) = 0.33 m/s (faster)
            → Right faster than left = turns left (corrects)
        """
        if self.line_start_lat is None or self.line_end_lat is None:
            logger.warning("Line segment not set")
            return base_speed, base_speed
        
        # Calculate Cross-Track Error
        cte = calculate_cross_track_error(
            lat, lon,
            self.line_start_lat, self.line_start_lon,
            self.line_end_lat, self.line_end_lon
        )
        
        # Update CTE monitoring
        self.current_cte = cte
        if abs(cte) > abs(self.max_cte):
            self.max_cte = cte
        
        # Check for GPS drift alert
        if abs(cte) > self.drift_alert_threshold:
            logger.warning(f"GPS DRIFT ALERT: CTE = {cte:.2f}m (threshold: {self.drift_alert_threshold}m)")
        
        # PID update: convert CTE to speed modulation
        # Positive CTE = right of line → negative output = turn left
        # Negative CTE = left of line → positive output = turn right
        modulation = self.pid.update(cte, dt=0.1)
        
        # Apply speed modulation to create differential steering
        # CRITICAL: Sign convention for differential drive
        # - Positive modulation: right turns faster (turn right)
        # - Negative modulation: left turns faster (turn left)
        v_left = base_speed * (1.0 - modulation)
        v_right = base_speed * (1.0 + modulation)
        
        logger.debug(f"CTE: {cte:+.3f}m, Modulation: {modulation:+.3f}, "
                    f"v_left: {v_left:.3f}, v_right: {v_right:.3f}")
        
        return v_left, v_right
    
    def is_waypoint_reached(
        self,
        lat: float,
        lon: float,
        threshold: Optional[float] = None
    ) -> bool:
        """
        Check if waypoint is reached
        
        Args:
            lat: Current latitude
            lon: Current longitude
            threshold: Distance threshold in meters (default: from config)
        
        Returns:
            True if distance to target < threshold
        """
        if self.target_lat is None or self.target_lon is None:
            return False
        
        if threshold is None:
            threshold = self.waypoint_threshold
        
        distance = haversine_distance(lat, lon, self.target_lat, self.target_lon)
        
        return distance < threshold
    
    def reset_controllers(self) -> None:
        """
        Reset all controllers (PID states)
        
        Call this when starting navigation to a new waypoint
        """
        self.pid.reset()
        self.max_cte = 0.0
        logger.debug("Controllers reset")
    
    def adapt_pid_to_gps_quality(self, fix_quality: str, hdop: float) -> None:
        """
        Adapt PID gains based on GPS quality
        
        Better GPS = higher gains (more aggressive correction)
        Worse GPS = lower gains (smoother, less jittery)
        
        Args:
            fix_quality: GPS fix quality string (e.g., 'RTK Fixed')
            hdop: Horizontal Dilution of Precision
        """
        if not self.adaptive_pid_enabled:
            return
        
        # Determine gain multiplier based on GPS quality
        if fix_quality == 'RTK Fixed' and hdop < 2.0:
            gain_multiplier = 1.0  # Full gains
            quality = 'excellent'
        elif fix_quality == 'RTK Float' or (fix_quality == 'RTK Fixed' and hdop < 5.0):
            gain_multiplier = 0.75  # Reduced gains
            quality = 'good'
        elif hdop < 10.0:
            gain_multiplier = 0.5  # Heavily reduced gains
            quality = 'fair'
        else:
            gain_multiplier = 0.3  # Very conservative
            quality = 'poor'
        
        # Update PID gains if quality changed
        if quality != self.current_gps_quality:
            new_kp = self.base_kp * gain_multiplier
            new_ki = self.base_ki * gain_multiplier
            new_kd = self.base_kd * gain_multiplier
            
            self.pid.set_gains(kp=new_kp, ki=new_ki, kd=new_kd)
            self.current_gps_quality = quality
            
            logger.info(f"Adaptive PID: GPS quality = {quality}, "
                       f"gain multiplier = {gain_multiplier:.2f}")
    
    def get_status(self) -> dict:
        """
        Get navigator status
        
        Returns:
            Dictionary with current navigation state
        """
        return {
            'target': {
                'lat': self.target_lat,
                'lon': self.target_lon
            },
            'line_segment': {
                'start_lat': self.line_start_lat,
                'start_lon': self.line_start_lon,
                'end_lat': self.line_end_lat,
                'end_lon': self.line_end_lon
            },
            'pid_state': self.pid.get_state(),
            'gps_quality': self.current_gps_quality,
            'current_cte_m': self.current_cte,
            'max_cte_m': self.max_cte,
            'adaptive_pid_enabled': self.adaptive_pid_enabled
        }
