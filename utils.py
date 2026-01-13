"""
Utility functions for M.A.R.K. Rover Control System
Provides geo-calculations, logging setup, and helper functions
"""

import math
import logging
from typing import Tuple


def setup_logging(level: int = logging.INFO) -> None:
    """
    Setup logging configuration for all modules
    
    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    
    Args:
        lat1: Latitude of point 1 (decimal degrees)
        lon1: Longitude of point 1 (decimal degrees)
        lat2: Latitude of point 2 (decimal degrees)
        lon2: Longitude of point 2 (decimal degrees)
    
    Returns:
        Distance in meters
    """
    # Earth radius in meters
    R = 6371000.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (math.sin(delta_lat / 2.0) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2.0) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing from point 1 to point 2
    
    Args:
        lat1: Latitude of point 1 (decimal degrees)
        lon1: Longitude of point 1 (decimal degrees)
        lat2: Latitude of point 2 (decimal degrees)
        lon2: Longitude of point 2 (decimal degrees)
    
    Returns:
        Bearing in degrees (0-360°, 0=North, 90=East, 180=South, 270=West)
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    # Calculate bearing
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
    
    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360°
    bearing_deg = (bearing_deg + 360.0) % 360.0
    
    return bearing_deg


def normalize_angle(angle: float) -> float:
    """
    Normalize angle to range -180 to +180 degrees
    
    Args:
        angle: Angle in degrees
    
    Returns:
        Normalized angle in range [-180, +180]
    """
    # Normalize to -180 to +180
    while angle > 180.0:
        angle -= 360.0
    while angle < -180.0:
        angle += 360.0
    return angle


def calculate_cross_track_error(
    lat: float, lon: float,
    lat_start: float, lon_start: float,
    lat_end: float, lon_end: float
) -> float:
    """
    Calculate perpendicular distance from current position to line segment
    
    This calculates the Cross-Track Error (CTE) which is the shortest distance
    from the current position to the ideal line between start and end points.
    
    Args:
        lat: Current latitude (decimal degrees)
        lon: Current longitude (decimal degrees)
        lat_start: Line start latitude (decimal degrees)
        lon_start: Line start longitude (decimal degrees)
        lat_end: Line end latitude (decimal degrees)
        lon_end: Line end longitude (decimal degrees)
    
    Returns:
        Cross-track error in meters
        Positive = right of line (when traveling from start to end)
        Negative = left of line
    """
    # Earth radius in meters
    R = 6371000.0
    
    # Convert all coordinates to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lat_start_rad = math.radians(lat_start)
    lon_start_rad = math.radians(lon_start)
    lat_end_rad = math.radians(lat_end)
    lon_end_rad = math.radians(lon_end)
    
    # Calculate distance from start to current position
    delta_lon_start = lon_rad - lon_start_rad
    
    # Calculate bearing from start to end (track bearing)
    y = math.sin(lon_end_rad - lon_start_rad) * math.cos(lat_end_rad)
    x = (math.cos(lat_start_rad) * math.sin(lat_end_rad) -
         math.sin(lat_start_rad) * math.cos(lat_end_rad) * 
         math.cos(lon_end_rad - lon_start_rad))
    track_bearing = math.atan2(y, x)
    
    # Calculate bearing from start to current position
    y_current = math.sin(delta_lon_start) * math.cos(lat_rad)
    x_current = (math.cos(lat_start_rad) * math.sin(lat_rad) -
                 math.sin(lat_start_rad) * math.cos(lat_rad) * 
                 math.cos(delta_lon_start))
    current_bearing = math.atan2(y_current, x_current)
    
    # Calculate distance from start to current position
    delta_lat = lat_rad - lat_start_rad
    a = (math.sin(delta_lat / 2.0) ** 2 +
         math.cos(lat_start_rad) * math.cos(lat_rad) *
         math.sin(delta_lon_start / 2.0) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_start_to_current = R * c
    
    # Calculate cross-track error
    # XTE = distance * sin(bearing difference)
    bearing_diff = current_bearing - track_bearing
    cross_track_error = distance_start_to_current * math.sin(bearing_diff)
    
    return cross_track_error


def meters_to_latlon_offset(north_m: float, east_m: float, lat_ref: float) -> Tuple[float, float]:
    """
    Convert meter offsets to latitude/longitude offsets
    
    Args:
        north_m: Northward offset in meters
        east_m: Eastward offset in meters
        lat_ref: Reference latitude for longitude scaling (decimal degrees)
    
    Returns:
        Tuple of (lat_offset, lon_offset) in decimal degrees
    """
    # Approximate conversion (works well for small distances)
    # 1 degree latitude ≈ 111,111 meters
    # 1 degree longitude ≈ 111,111 * cos(latitude) meters
    
    lat_offset = north_m / 111111.0
    lon_offset = east_m / (111111.0 * math.cos(math.radians(lat_ref)))
    
    return lat_offset, lon_offset
