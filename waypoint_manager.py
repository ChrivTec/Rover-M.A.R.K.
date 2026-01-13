"""
Waypoint Manager for M.A.R.K. Rover
Handles route loading and waypoint navigation
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Waypoint:
    """
    Waypoint data class
    
    Attributes:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        action: Action to perform ("forward", "spray", etc.)
        speed_ms: Desired speed in m/s
        duration_s: Duration for timed actions (e.g., spray duration)
    """
    lat: float
    lon: float
    action: str = "forward"
    speed_ms: float = 0.3
    duration_s: float = 0.0


class WaypointManager:
    """
    Manage waypoints and route navigation
    """
    
    def __init__(self):
        """
        Initialize Waypoint Manager
        """
        self.waypoints: List[Waypoint] = []
        self.current_index = 0
        self.route_id = ""
        self.route_name = ""
        
        logger.info("Waypoint Manager initialized")
    
    def load_waypoints(self, filepath: str) -> bool:
        """
        Load route from JSON file
        
        Args:
            filepath: Path to JSON route file
        
        Returns:
            True if loading successful
        
        Expected JSON format:
        {
            "id": "20260106_115200",
            "name": "Route_1",
            "waypoints": [
                {"lat": 50.9379, "lon": 6.9580, "action": "forward", "speed_ms": 0.3},
                {"lat": 50.9380, "lon": 6.9581, "action": "spray", "duration_s": 5}
            ]
        }
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.route_id = data.get('id', '')
            self.route_name = data.get('name', '')
            
            self.waypoints = []
            for wp_data in data.get('waypoints', []):
                waypoint = Waypoint(
                    lat=wp_data['lat'],
                    lon=wp_data['lon'],
                    action=wp_data.get('action', 'forward'),
                    speed_ms=wp_data.get('speed_ms', 0.3),
                    duration_s=wp_data.get('duration_s', 0.0)
                )
                self.waypoints.append(waypoint)
            
            self.current_index = 0
            
            logger.info(f"Loaded route '{self.route_name}' with {len(self.waypoints)} waypoints from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load waypoints from {filepath}: {e}")
            return False
    
    def get_current_waypoint(self) -> Optional[Waypoint]:
        """
        Get current waypoint
        
        Returns:
            Current waypoint or None if no waypoints
        """
        if 0 <= self.current_index < len(self.waypoints):
            return self.waypoints[self.current_index]
        return None
    
    def get_next_waypoint(self) -> Optional[Waypoint]:
        """
        Get next waypoint without advancing
        
        Returns:
            Next waypoint or None if at end
        """
        next_index = self.current_index + 1
        if next_index < len(self.waypoints):
            return self.waypoints[next_index]
        return None
    
    def advance_waypoint(self) -> bool:
        """
        Move to next waypoint
        
        Returns:
            True if more waypoints available, False if route complete
        """
        self.current_index += 1
        
        if self.current_index < len(self.waypoints):
            logger.info(f"Advanced to waypoint {self.current_index + 1}/{len(self.waypoints)}")
            return True
        else:
            logger.info("Route complete - all waypoints reached")
            return False
    
    def get_progress(self) -> Tuple[int, int]:
        """
        Get current progress
        
        Returns:
            Tuple of (current_index, total_count)
        """
        return self.current_index, len(self.waypoints)
    
    def reset(self) -> None:
        """
        Reset to first waypoint
        """
        self.current_index = 0
        logger.info("Waypoint manager reset to start")
    
    def has_waypoints(self) -> bool:
        """
        Check if waypoints are loaded
        
        Returns:
            True if waypoints are loaded
        """
        return len(self.waypoints) > 0
