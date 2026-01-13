"""
Unit tests for utils.py geo-calculation functions
Run with: pytest test_utils.py -v
"""

import pytest
import math
from utils import (
    haversine_distance,
    calculate_bearing,
    normalize_angle,
    calculate_cross_track_error,
    meters_to_latlon_offset
)


class TestHaversineDistance:
    """Test haversine distance calculation"""
    
    def test_same_point(self):
        """Distance between same point should be 0"""
        dist = haversine_distance(50.9379, 6.9580, 50.9379, 6.9580)
        assert abs(dist) < 0.1  # < 10cm
    
    def test_known_distance(self):
        """Test with known coordinates"""
        # ~111km per degree latitude
        dist = haversine_distance(50.0, 6.0, 51.0, 6.0)
        assert 110000 < dist < 112000
    
    def test_small_distance(self):
        """Test small distance (typical waypoint spacing)"""
        # 0.0001 degrees ~ 11 meters
        dist = haversine_distance(50.9379, 6.9580, 50.9380, 6.9580)
        assert 100 < dist < 120


class TestCalculateBearing:
    """Test bearing calculation"""
    
    def test_north(self):
        """Bearing due north should be 0°"""
        bearing = calculate_bearing(50.0, 6.0, 51.0, 6.0)
        assert -1 < bearing < 1 or 359 < bearing < 361
    
    def test_east(self):
        """Bearing due east should be 90°"""
        bearing = calculate_bearing(50.0, 6.0, 50.0, 7.0)
        assert 85 < bearing < 95
    
    def test_south(self):
        """Bearing due south should be 180°"""
        bearing = calculate_bearing(51.0, 6.0, 50.0, 6.0)
        assert 175 < bearing < 185
    
    def test_west(self):
        """Bearing due west should be 270°"""
        bearing = calculate_bearing(50.0, 7.0, 50.0, 6.0)
        assert 265 < bearing < 275
    
    def test_range(self):
        """Bearing should always be 0-360°"""
        bearing = calculate_bearing(50.0, 6.0, 49.0, 5.0)
        assert 0 <= bearing < 360


class TestNormalizeAngle:
    """Test angle normalization"""
    
    def test_in_range(self):
        """Angles already in range should not change"""
        assert normalize_angle(45.0) == 45.0
        assert normalize_angle(-45.0) == -45.0
        assert normalize_angle(180.0) == 180.0
    
    def test_over_180(self):
        """Angles > 180 should wrap to negative"""
        assert abs(normalize_angle(270.0) - (-90.0)) < 0.01
        assert abs(normalize_angle(185.0) - (-175.0)) < 0.01
    
    def test_under_minus_180(self):
        """Angles < -180 should wrap to positive"""
        assert abs(normalize_angle(-270.0) - 90.0) < 0.01
        assert abs(normalize_angle(-185.0) - 175.0) < 0.01
    
    def test_multiple_wraps(self):
        """Large angles should wrap correctly"""
        assert abs(normalize_angle(720.0) - 0.0) < 0.01
        assert abs(normalize_angle(-720.0) - 0.0) < 0.01


class TestCrossTrackError:
    """Test cross-track error calculation"""
    
    def test_on_line(self):
        """Point on line should have CTE ≈ 0"""
        # Point halfway between start and end
        cte = calculate_cross_track_error(
            50.93795, 6.9580,  # Midpoint
            50.9379, 6.9580,   # Start
            50.9380, 6.9580    # End
        )
        assert abs(cte) < 1.0  # < 1 meter
    
    def test_right_of_line(self):
        """Point right of line should have positive CTE"""
        # Point east (right) of north-south line
        cte = calculate_cross_track_error(
            50.93795, 6.9581,  # East of line
            50.9379, 6.9580,   # Start
            50.9380, 6.9580    # End (north)
        )
        assert cte > 0  # Positive = right
    
    def test_left_of_line(self):
        """Point left of line should have negative CTE"""
        # Point west (left) of north-south line
        cte = calculate_cross_track_error(
            50.93795, 6.9579,  # West of line
            50.9379, 6.9580,   # Start
            50.9380, 6.9580    # End (north)
        )
        assert cte < 0  # Negative = left


class TestMetersToLatLonOffset:
    """Test meter to lat/lon conversion"""
    
    def test_north_offset(self):
        """100m north should be ~0.0009 degrees lat"""
        lat_off, lon_off = meters_to_latlon_offset(100, 0, 50.0)
        assert 0.0008 < lat_off < 0.0010
        assert abs(lon_off) < 0.00001
    
    def test_east_offset(self):
        """100m east should be ~0.0014 degrees lon (at 50°N)"""
        lat_off, lon_off = meters_to_latlon_offset(0, 100, 50.0)
        assert abs(lat_off) < 0.00001
        assert 0.0013 < lon_off < 0.0016


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
