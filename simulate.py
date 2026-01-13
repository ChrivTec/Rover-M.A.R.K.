"""
Dry-Run Simulation for M.A.R.K. Rover
Tests navigation logic without hardware
"""

import json
import logging
import time
from typing import List, Tuple
from utils import setup_logging, haversine_distance, calculate_bearing
from navigator import Navigator
from waypoint_manager import WaypointManager
from rover_state import RoverStateMachine, RoverState

logger = logging.getLogger(__name__)


class SimulatedRover:
    """
    Simulates rover movement for testing navigation logic
    """
    
    def __init__(self, config_file: str, start_lat: float, start_lon: float):
        """
        Initialize simulated rover
        
        Args:
            config_file: Path to config.json
            start_lat: Starting latitude
            start_lon: Starting longitude
        """
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        # Current state
        self.lat = start_lat
        self.lon = start_lon
        self.heading = 0.0  # degrees
        
        # Motion
        self.v_left = 0.0
        self.v_right = 0.0
        
        # Hardware config
        hw = self.config.get('hardware', {})
        self.wheelbase = hw.get('wheelbase_m', 0.396503)
        
        # Initialize modules
        self.waypoint_manager = WaypointManager()
        self.state_machine = RoverStateMachine()
        self.navigator = Navigator(self.config)
        
        logger.info(f"Simulated Rover initialized at ({start_lat:.6f}, {start_lon:.6f})")
    
    def set_velocity(self, left_m_s: float, right_m_s: float) -> None:
        """
        Set motor velocities (simulated)
        
        Args:
            left_m_s: Left motor velocity
            right_m_s: Right motor velocity
        """
        self.v_left = left_m_s
        self.v_right = right_m_s
        logger.debug(f"Motors: L={left_m_s:.3f}, R={right_m_s:.3f}")
    
    def update_physics(self, dt: float) -> None:
        """
        Update rover position based on differential drive kinematics
        
        Args:
            dt: Time step in seconds
        """
        # Average velocity
        v_avg = (self.v_left + self.v_right) / 2.0
        
        # Angular velocity (differential drive)
        omega = (self.v_right - self.v_left) / self.wheelbase
        
        # Update heading
        self.heading += omega * dt * (180.0 / 3.14159)  # rad/s to deg/s
        self.heading = self.heading % 360.0
        
        # Update position (simple forward kinematics)
        if abs(v_avg) > 0.001:
            # Distance traveled
            distance = v_avg * dt
            
            # Convert heading to radians
            heading_rad = self.heading * (3.14159 / 180.0)
            
            # Update lat/lon (approximate)
            # 1 degree latitude ≈ 111,320 meters
            # 1 degree longitude ≈ 111,320 * cos(lat) meters
            import math
            dlat = (distance * math.cos(heading_rad)) / 111320.0
            dlon = (distance * math.sin(heading_rad)) / (111320.0 * math.cos(self.lat * math.pi / 180.0))
            
            self.lat += dlat
            self.lon += dlon
    
    def run_simulation(self, waypoint_file: str, speed_factor: float = 10.0) -> None:
        """
        Run navigation simulation
        
        Args:
            waypoint_file: Path to waypoints JSON
            speed_factor: Speed multiplier for simulation (10x = 10x faster)
        """
        logger.info("="*60)
        logger.info("M.A.R.K. Rover - SIMULATION MODE")
        logger.info("="*60)
        
        # Load waypoints
        if not self.waypoint_manager.load_waypoints(waypoint_file):
            logger.error(f"Failed to load waypoints from {waypoint_file}")
            return
        
        logger.info(f"Loaded {len(self.waypoint_manager.waypoints)} waypoints")
        logger.info("")
        
        # Calculate total distance
        total_distance = 0.0
        coords = [(wp.lat, wp.lon) for wp in self.waypoint_manager.waypoints]
        for i in range(len(coords) - 1):
            dist = haversine_distance(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
            total_distance += dist
        
        logger.info(f"Total route distance: {total_distance:.1f}m")
        logger.info("")
        
        # Start simulation
        self.state_machine.set_state(RoverState.IDLE, "Simulation ready")
        
        loop_rate = 10  # Hz
        dt = 1.0 / loop_rate
        dt_sim = dt * speed_factor  # Simulated time
        
        iteration = 0
        max_iterations = 10000  # Safety limit
        
        logger.info(f"Starting simulation at {loop_rate}Hz (speed: {speed_factor}x)")
        logger.info("="*60)
        
        while iteration < max_iterations:
            iteration += 1
            
            # State machine logic
            current_state = self.state_machine.get_state()
            
            if current_state == RoverState.IDLE:
                # Load first waypoint
                if self.waypoint_manager.has_waypoints():
                    wp = self.waypoint_manager.get_current_waypoint()
                    self.navigator.set_target(wp.lat, wp.lon)
                    self.navigator.set_line_segment(self.lat, self.lon, wp.lat, wp.lon)
                    self.navigator.reset_controllers()
                    self.state_machine.set_state(RoverState.ROTATING, "Starting mission")
                    logger.info(f"Navigating to waypoint 1/{len(self.waypoint_manager.waypoints)}")
            
            elif current_state == RoverState.ROTATING:
                # Align heading
                bearing = self.navigator.get_bearing_to_target(self.lat, self.lon)
                
                if self.navigator.is_heading_aligned(self.heading, bearing):
                    logger.info(f"Heading aligned ({self.heading:.1f}° → {bearing:.1f}°)")
                    self.state_machine.set_state(RoverState.DRIVING, "Heading aligned")
                    self.navigator.reset_controllers()
                else:
                    v_left, v_right = self.navigator.calculate_rotation_command(self.heading, bearing)
                    self.set_velocity(v_left, v_right)
            
            elif current_state == RoverState.DRIVING:
                # Check if reached
                if self.navigator.is_waypoint_reached(self.lat, self.lon):
                    distance = haversine_distance(self.lat, self.lon, 
                                                 self.navigator.target_lat, self.navigator.target_lon)
                    logger.info(f"Waypoint reached! (distance: {distance:.2f}m)")
                    self.set_velocity(0, 0)
                    self.state_machine.set_state(RoverState.REACHED_WAYPOINT, "Waypoint reached")
                else:
                    # Line following
                    wp = self.waypoint_manager.get_current_waypoint()
                    base_speed = wp.speed_ms if wp else 0.3
                    v_left, v_right = self.navigator.calculate_line_following_command(
                        self.lat, self.lon, self.heading, base_speed
                    )
                    self.set_velocity(v_left, v_right)
            
            elif current_state == RoverState.REACHED_WAYPOINT:
                # Advance to next waypoint
                if self.waypoint_manager.advance_waypoint():
                    wp = self.waypoint_manager.get_current_waypoint()
                    self.navigator.set_target(wp.lat, wp.lon)
                    self.navigator.set_line_segment(self.lat, self.lon, wp.lat, wp.lon)
                    self.navigator.reset_controllers()
                    
                    idx, total = self.waypoint_manager.get_progress()
                    logger.info(f"Next waypoint: {idx + 1}/{total}")
                    self.state_machine.set_state(RoverState.ROTATING, "Next waypoint")
                else:
                    logger.info("MISSION COMPLETE!")
                    self.state_machine.set_state(RoverState.MISSION_COMPLETE, "All waypoints reached")
                    break
            
            elif current_state == RoverState.MISSION_COMPLETE:
                break
            
            # Update physics
            self.update_physics(dt_sim)
            
            # Periodic logging
            if iteration % 10 == 0:
                distance_to_target = haversine_distance(
                    self.lat, self.lon,
                    self.navigator.target_lat, self.navigator.target_lon
                ) if self.navigator.target_lat else 0
                
                logger.info(f"[{iteration:4d}] State: {current_state.value:15s} | "
                          f"Pos: ({self.lat:.6f}, {self.lon:.6f}) | "
                          f"Heading: {self.heading:6.1f}° | "
                          f"Distance: {distance_to_target:5.2f}m | "
                          f"Motors: L={self.v_left:+.2f}, R={self.v_right:+.2f}")
            
            # Sleep (real time)
            time.sleep(dt / speed_factor)
        
        logger.info("="*60)
        logger.info("Simulation complete")
        logger.info(f"Final position: ({self.lat:.6f}, {self.lon:.6f})")
        logger.info(f"Final heading: {self.heading:.1f}°")


def main():
    """
    Main entry point for simulation
    """
    setup_logging(level=logging.INFO)
    
    # Configuration
    config_file = 'config.json'
    waypoint_file = 'waypoints_test.json'
    
    # Starting position (first waypoint from route)
    start_lat = 50.933458098664744
    start_lon = 6.988535821437837
    
    # Create simulated rover
    rover = SimulatedRover(config_file, start_lat, start_lon)
    
    # Run simulation (10x speed)
    rover.run_simulation(waypoint_file, speed_factor=10.0)


if __name__ == '__main__':
    main()
