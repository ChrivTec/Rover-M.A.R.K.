"""
Motor Controller Module for RoboClaw 2x15A
Direct Packet Serial Protocol implementation
"""

import serial
import logging
import time
import math
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class MotorController:
    """
    RoboClaw 2x15A Motor Controller using Packet Serial Protocol
    
    Implements direct serial communication without external library
    for full control over motor commands
    """
    
    # RoboClaw Commands
    CMD_DRIVE_M1_FORWARD = 0
    CMD_DRIVE_M1_BACKWARD = 1
    CMD_DRIVE_M2_FORWARD = 4
    CMD_DRIVE_M2_BACKWARD = 5
    CMD_DRIVE_M1_7BIT = 6
    CMD_DRIVE_M2_7BIT = 7
    CMD_DRIVE_FORWARD_MIXED = 8
    CMD_DRIVE_BACKWARD_MIXED = 9
    CMD_TURN_RIGHT_MIXED = 10
    CMD_TURN_LEFT_MIXED = 11
    CMD_DRIVE_M1_DUTY = 32
    CMD_DRIVE_M2_DUTY = 33
    CMD_DRIVE_BOTH_DUTY = 34
    CMD_DRIVE_M1_SPEED = 35
    CMD_DRIVE_M2_SPEED = 36
    CMD_DRIVE_BOTH_SPEED = 37
    CMD_READ_MAIN_BATTERY = 24
    CMD_READ_LOGIC_BATTERY = 25
    CMD_READ_TEMP = 82
    CMD_READ_TEMP2 = 83
    CMD_READ_CURRENTS = 49
    
    def __init__(
        self,
        port: str,
        baudrate: int,
        address: int,
        config: dict
    ):
        """
        Initialize Motor Controller
        
        Args:
            port: Serial port (e.g., "/dev/ttyACM0")
            baudrate: Baud rate (e.g., 38400)
            address: RoboClaw address (default: 128 = 0x80)
            config: Hardware configuration
        """
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.config = config
        
        self.serial = None
        self.connected = False
        
        # Calculate max velocity from hardware config
        wheel_diameter = config.get('wheel_diameter_m', 0.079)
        max_rpm = config.get('max_rpm', 60)
        
        # v_max = (max_rpm / 60) * π * diameter
        self.max_velocity_ms = (max_rpm / 60.0) * math.pi * wheel_diameter
        
        logger.info(f"Motor Controller initialized on {port} @ {baudrate} baud")
        logger.info(f"Max velocity: {self.max_velocity_ms:.3f} m/s")
    
    def connect(self) -> bool:
        """
        Connect to RoboClaw via serial
        
        Returns:
            True if connection successful
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            self.connected = True
            logger.info(f"Connected to RoboClaw on {self.port}")
            
            # Test connection by reading battery voltage
            voltage = self.get_battery_voltage()
            if voltage and voltage > 0:
                logger.info(f"RoboClaw responding, battery voltage: {voltage:.1f}V")
                return True
            else:
                logger.warning("RoboClaw connected but not responding to commands")
                return True  # Still consider connected
                
        except Exception as e:
            logger.error(f"Failed to connect to RoboClaw: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """
        Disconnect from RoboClaw
        """
        if self.serial and self.serial.is_open:
            self.stop()  # Stop motors before disconnecting
            self.serial.close()
        self.connected = False
        logger.info("Motor Controller disconnected")
    
    def _calculate_checksum(self, data: bytes) -> int:
        """
        Calculate RoboClaw CRC16 checksum (CORRECTED!)
        
        Args:
            data: Packet data bytes
        
        Returns:
            CRC16 checksum (16-bit integer)
        """
        crc = 0
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
                crc &= 0xFFFF
        return crc
    
    def _send_command(self, command: int, *args) -> bool:
        """
        Send command to RoboClaw
        
        Args:
            command: Command byte
            *args: Additional data bytes
        
        Returns:
            True if command sent successfully
        """
        if not self.connected or not self.serial:
            return False
        
        try:
            # Build packet: [address, command, data..., checksum]
            packet = bytes([self.address, command] + list(args))
            checksum = self._calculate_checksum(packet)
            packet = packet + checksum.to_bytes(2, 'big')
            
            # Send packet
            self.serial.write(packet)
            self.serial.flush()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send command 0x{command:02X}: {e}")
            return False
    
    def _read_response(self, num_bytes: int) -> Optional[bytes]:
        """
        Read response from RoboClaw
        
        Args:
            num_bytes: Number of bytes to read (excluding checksum)
        
        Returns:
            Response bytes or None if error
        """
        if not self.connected or not self.serial:
            return None
        
        try:
            # Read data + checksum
            data = self.serial.read(num_bytes + 1)
            
            if len(data) != num_bytes + 1:
                return None
            
            # Verify checksum
            received_checksum = data[-1]
            calculated_checksum = self._calculate_checksum(data[:-1])
            
            if received_checksum != calculated_checksum:
                logger.warning("Checksum mismatch in response")
                return None
            
            return data[:-1]
            
        except Exception as e:
            logger.error(f"Failed to read response: {e}")
            return None
    
    def set_velocity(self, left_m_s: float, right_m_s: float) -> bool:
        """
        Set motor velocities in m/s
        
        Uses signed duty cycle commands for proper direction control.
        RoboClaw CMD_DRIVE_M1_DUTY accepts signed 16-bit values:
        - Positive = Forward
        - Negative = Backward
        
        Args:
            left_m_s: Left motor (M1) velocity in m/s
            right_m_s: Right motor (M2) velocity in m/s
        
        Returns:
            True if commands sent successfully
        """
        # Convert m/s to signed duty values (-32767 to +32767)
        left_duty = self._velocity_to_duty(left_m_s)
        right_duty = self._velocity_to_duty(right_m_s)
        
        # Send signed duty commands
        # CMD_DRIVE_M1_DUTY (32): M1 with signed duty
        # CMD_DRIVE_M2_DUTY (33): M2 with signed duty
        success = self._send_duty_command(self.CMD_DRIVE_M1_DUTY, left_duty)
        success &= self._send_duty_command(self.CMD_DRIVE_M2_DUTY, right_duty)
        
        return success
    
    def _send_duty_command(self, command: int, duty: int) -> bool:
        """
        Send signed duty command to RoboClaw
        
        Args:
            command: Command byte (CMD_DRIVE_M1_DUTY or CMD_DRIVE_M2_DUTY)
            duty: Signed duty value (-32767 to +32767)
        
        Returns:
            True if command sent successfully
        """
        # Convert signed integer to bytes (big-endian, signed 16-bit)
        # Clamp to valid range
        duty = max(-32767, min(32767, duty))
        
        # Convert to unsigned for transmission
        duty_unsigned = duty if duty >= 0 else (65536 + duty)
        
        high_byte = (duty_unsigned >> 8) & 0xFF
        low_byte = duty_unsigned & 0xFF
        
        return self._send_command(command, high_byte, low_byte)
    
    def _velocity_to_duty(self, velocity_m_s: float) -> int:
        """
        Convert velocity in m/s to signed RoboClaw duty cycle value
        
        Args:
            velocity_m_s: Velocity in m/s (can be negative for reverse)
        
        Returns:
            Signed duty value (-32767 to +32767)
            Negative = Reverse, Positive = Forward
        """
        # Clamp to max velocity
        velocity_m_s = max(-self.max_velocity_ms, min(self.max_velocity_ms, velocity_m_s))
        
        # Convert to duty cycle with sign
        ratio = velocity_m_s / self.max_velocity_ms
        duty = int(ratio * 32767)
        
        return duty
    
    def stop(self) -> bool:
        """
        Stop both motors immediately
        
        Returns:
            True if stop command sent successfully
        """
        logger.info("Stopping motors")
        return self.set_velocity(0.0, 0.0)
    
    def get_battery_voltage(self) -> Optional[float]:
        """
        Read main battery voltage
        
        Returns:
            Battery voltage in volts or None if error
        """
        if not self._send_command(self.CMD_READ_MAIN_BATTERY):
            return None
        
        response = self._read_response(2)
        if not response:
            return None
        
        # Convert to voltage (value / 10.0)
        voltage = (response[0] << 8 | response[1]) / 10.0
        return voltage
    
    def get_currents(self) -> Optional[Tuple[float, float]]:
        """
        Read motor currents
        
        Returns:
            Tuple of (left_current_a, right_current_a) or None if error
        """
        if not self._send_command(self.CMD_READ_CURRENTS):
            return None
        
        response = self._read_response(4)
        if not response:
            return None
        
        # Convert to amps (value / 100.0)
        left_current = (response[0] << 8 | response[1]) / 100.0
        right_current = (response[2] << 8 | response[3]) / 100.0
        
        return left_current, right_current
    
    def get_temperature(self) -> Optional[Tuple[float, float]]:
        """
        Read temperature sensors
        
        Returns:
            Tuple of (temp1_c, temp2_c) or None if error
        """
        # Read temp1
        if not self._send_command(self.CMD_READ_TEMP):
            return None
        response1 = self._read_response(2)
        
        # Read temp2
        if not self._send_command(self.CMD_READ_TEMP2):
            return None
        response2 = self._read_response(2)
        
        if not response1 or not response2:
            return None
        
        # Convert to Celsius (value / 10.0)
        temp1 = (response1[0] << 8 | response1[1]) / 10.0
        temp2 = (response2[0] << 8 | response2[1]) / 10.0
        
        return temp1, temp2
    
    def get_status(self) -> dict:
        """
        Get comprehensive motor controller status
        
        Returns:
            Dictionary with status data
        """
        status = {
            'connected': self.connected,
            'battery_v': None,
            'left_current_a': None,
            'right_current_a': None,
            'left_temp_c': None,
            'right_temp_c': None
        }
        
        if not self.connected:
            return status
        
        # Read battery voltage
        voltage = self.get_battery_voltage()
        if voltage:
            status['battery_v'] = voltage
        
        # Read currents
        currents = self.get_currents()
        if currents:
            status['left_current_a'], status['right_current_a'] = currents
        
        # Read temperatures
        temps = self.get_temperature()
        if temps:
            status['left_temp_c'], status['right_temp_c'] = temps
        
        return status
