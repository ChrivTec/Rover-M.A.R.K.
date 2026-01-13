"""
GNSS Module for u-blox ZED-F9P with RTK support
Handles NMEA parsing, Kalman filtering, and antenna offset correction

IMPROVED VERSION: Direct NMEA parsing without pynmea2 dependency
"""

import serial
import numpy as np
import logging
import time
import math
from typing import Optional, Tuple, Dict, Any
from kalman_filter import KalmanFilter

logger = logging.getLogger(__name__)


class GNSSModule:
    """
    GNSS/RTK Interface for u-blox ZED-F9P
    
    Reads NMEA sentences, parses position data, applies Kalman filtering,
    and corrects for antenna offset using IMU heading
    """
    
    def __init__(
        self,
        port: str,
        baudrate: int,
        kalman_config: dict = None,
        hardware_config: dict = None
    ):
        """
        Initialize GNSS module
        
        Args:
            port: Serial port (e.g., "/dev/ttyACM1")
            baudrate: Baud rate (e.g., 115200)
            kalman_config: Kalman filter configuration dict
            hardware_config: Hardware configuration dict (for antenna offset etc.)
        """
        self.port = port
        self.baudrate = baudrate
        self.hardware_config = hardware_config or {}
        
        self.serial = None
        self.connected = False
        
        # GNSS data - initialize with zeros (realistic defaults)
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.fix_quality = 0  # 0=Invalid, 1=GPS, 2=DGPS, 4=RTK Fixed, 5=RTK Float
        self.num_satellites = 0
        self.hdop = 99.9
        self.speed_kmh = 0.0
        
        # Create Kalman filter from config
        kalman_config = kalman_config or {}
        self.kalman = KalmanFilter(
            process_noise=kalman_config.get('process_noise', 0.001),
            measurement_noise=kalman_config.get('measurement_noise_gps', 0.5)
        )
        
        self.last_update_time = time.time()
        
        logger.info(f"GNSS Module initialized on {port} @ {baudrate} baud")
    
    def connect(self) -> bool:
        """
        Connect to GNSS receiver via serial port
        
        Returns:
            True if connection successful
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            self.connected = True
            logger.info(f"Connected to GNSS on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to GNSS: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """
        Disconnect from GNSS receiver
        """
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
        logger.info("GNSS disconnected")
    
    def _parse_nmea_gga(self, sentence: str) -> bool:
        """
        Parse $GNGGA NMEA sentence directly without pynmea2
        
        Format: $GNGGA,hhmmss.ss,ddmm.mmmm,N,dddmm.mmmm,E,q,nn,h.h,alt,M,sep,M,age,stn*cs
        
        Args:
            sentence: NMEA sentence string
            
        Returns:
            True if parsed successfully
        """
        try:
            parts = sentence.split(',')
            
            if len(parts) < 15:
                return False
            
            # Extract fix quality (index 6)
            fix_qual = parts[6]
            if fix_qual:
                self.fix_quality = int(fix_qual)
            else:
                self.fix_quality = 0
            
            # Extract number of satellites (index 7)
            num_sats = parts[7]
            if num_sats:
                self.num_satellites = int(num_sats)
            else:
                self.num_satellites = 0
            
            # Extract HDOP (index 8)
            hdop = parts[8]
            if hdop:
                self.hdop = float(hdop)
            else:
                self.hdop = 99.9
            
            # Extract latitude (index 2-3)
            lat_str = parts[2]
            lat_dir = parts[3]
            if lat_str and lat_dir:
                # Convert DDMM.MMMM to DD.DDDDDD
                lat_deg = float(lat_str[:2])
                lat_min = float(lat_str[2:])
                self.latitude = lat_deg + (lat_min / 60.0)
                if lat_dir == 'S':
                    self.latitude = -self.latitude
            else:
                self.latitude = 0.0
            
            # Extract longitude (index 4-5)
            lon_str = parts[4]
            lon_dir = parts[5]
            if lon_str and lon_dir:
                # Convert DDDMM.MMMM to DDD.DDDDDD
                lon_deg = float(lon_str[:3])
                lon_min = float(lon_str[3:])
                self.longitude = lon_deg + (lon_min / 60.0)
                if lon_dir == 'W':
                    self.longitude = -self.longitude
            else:
                self.longitude = 0.0
            
            # Extract altitude (index 9)
            alt_str = parts[9]
            if alt_str:
                self.altitude = float(alt_str)
            else:
                self.altitude = 0.0
            
            return True
            
        except (ValueError, IndexError) as e:
            logger.debug(f"GGA parse error: {e}")
            return False
    
    def _parse_nmea_rmc(self, sentence: str) -> bool:
        """
        Parse $GNRMC NMEA sentence for speed
        
        Format: $GNRMC,hhmmss.ss,A,ddmm.mmmm,N,dddmm.mmmm,E,spd,cog,ddmmyy,,,mode*cs
        
        Args:
            sentence: NMEA sentence string
            
        Returns:
            True if parsed successfully
        """
        try:
            parts = sentence.split(',')
            
            if len(parts) < 8:
                return False
            
            # Extract speed over ground in knots (index 7)
            spd_str = parts[7]
            if spd_str:
                speed_knots = float(spd_str)
                self.speed_kmh = speed_knots * 1.852  # Convert to km/h
            else:
                self.speed_kmh = 0.0
            
            return True
            
        except (ValueError, IndexError) as e:
            logger.debug(f"RMC parse error: {e}")
            return False
    
    def update(self, heading: Optional[float] = None) -> bool:
        """
        Read and parse NMEA data from GNSS receiver
        
        Args:
            heading: Current IMU heading for antenna offset correction (optional)
        
        Returns:
            True if new data was processed successfully
        """
        if not self.connected or not self.serial:
            return False
        
        try:
            # Read available lines
            data_updated = False
            current_time = time.time()
            dt = current_time - self.last_update_time
            
            # Read multiple lines if available
            lines_read = 0
            while self.serial.in_waiting > 0 and lines_read < 10:
                try:
                    line = self.serial.readline().decode('ascii', errors='ignore').strip()
                    
                    if not line or not line.startswith('$'):
                        continue
                    
                    # Parse NMEA sentence based on type
                    if '$GNGGA' in line or '$GPGGA' in line:
                        if self._parse_nmea_gga(line):
                            # Update Kalman filter if we have valid position
                            if self.latitude != 0.0 and self.longitude != 0.0:
                                self._update_kalman_filter(dt)
                            data_updated = True
                    
                    elif '$GNRMC' in line or '$GPRMC' in line:
                        self._parse_nmea_rmc(line)
                    
                    lines_read += 1
                    
                except Exception as e:
                    logger.debug(f"Error reading line: {e}")
                    continue
            
            if data_updated:
                self.last_update_time = current_time
            
            return data_updated
            
        except Exception as e:
            logger.error(f"GNSS update error: {e}")
            return False
    
    def _update_kalman_filter(self, dt: float) -> None:
        """
        Update Kalman filter with current GPS measurement
        
        Args:
            dt: Time step in seconds
        """
        # Predict step
        self.kalman.predict(dt)
        
        # Determine measurement noise based on fix quality
        if self.fix_quality == 4:  # RTK Fixed
            noise = 0.01
        elif self.fix_quality == 5:  # RTK Float
            noise = 0.05
        else:  # GPS or DGPS
            noise = 0.5
        
        # Update with measurement
        measurement = np.array([self.latitude, self.longitude])
        self.kalman.update(measurement, noise)
    
    def get_position(self, filtered: bool = True) -> Tuple[float, float]:
        """
        Get current position
        
        Args:
            filtered: If True, return Kalman-filtered position; if False, return raw GPS
        
        Returns:
            Tuple of (latitude, longitude)
        """
        if filtered and self.kalman.is_initialized():
            return self.kalman.get_position()
        else:
            return self.latitude, self.longitude
    
    def get_position_with_offset_correction(
        self,
        heading: float,
        filtered: bool = True
    ) -> Tuple[float, float]:
        """
        Get position corrected for antenna offset using IMU heading
        
        The GPS antenna is mounted at the rear of the rover.
        This function calculates the rover center position.
        
        Args:
            heading: Current heading from IMU (0-360°, 0=North)
            filtered: Use filtered or raw position
        
        Returns:
            Tuple of (latitude, longitude) at rover center
        """
        lat, lon = self.get_position(filtered)
        
        # Antenna offset in meters (from config)
        # Negative Y = rear of rover
        offset_y = -0.34  # Default value
        
        # Convert heading to radians (0° = North, clockwise)
        heading_rad = math.radians(heading)
        
        # Calculate offset in North/East coordinates
        north_offset = offset_y * math.cos(heading_rad)
        east_offset = offset_y * math.sin(heading_rad)
        
        # Convert meter offsets to lat/lon offsets
        lat_offset = north_offset / 111111.0
        lon_offset = east_offset / (111111.0 * math.cos(math.radians(lat)))
        
        # Apply correction
        corrected_lat = lat - lat_offset
        corrected_lon = lon - lon_offset
        
        return corrected_lat, corrected_lon
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive GNSS status
        
        Returns:
            Dictionary with all GNSS data (realistic values or 0)
        """
        filtered_lat, filtered_lon = self.get_position(filtered=True)
        
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'filtered_lat': filtered_lat,
            'filtered_lon': filtered_lon,
            'altitude': self.altitude,
            'fix_quality': self.fix_quality,
            'fix_quality_str': self.get_fix_quality_str(),
            'num_satellites': self.num_satellites,
            'hdop': self.hdop,
            'speed_kmh': self.speed_kmh,
            'connected': self.connected
        }
    
    def has_valid_fix(self) -> bool:
        """
        Check if GPS has valid fix (at least 4 satellites)
        
        Returns:
            True if valid fix
        """
        return self.fix_quality > 0 and self.num_satellites >= 4
    
    def has_rtk_fix(self) -> bool:
        """
        Check if GPS has RTK fix (Fixed or Float)
        
        Returns:
            True if RTK Fixed (4) or RTK Float (5)
        """
        return self.fix_quality in [4, 5]
    
    def get_fix_quality_str(self) -> str:
        """
        Get human-readable fix quality string
        
        Returns:
            Fix quality string
        """
        quality_map = {
            0: 'Invalid',
            1: 'GPS',
            2: 'DGPS',
            3: 'PPS',
            4: 'RTK Fixed',
            5: 'RTK Float',
            6: 'Estimated'
        }
        return quality_map.get(self.fix_quality, 'Unknown')
