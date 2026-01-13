"""
PID Controller for M.A.R.K. Rover
Used for converting Cross-Track Error to speed modulation
"""

import logging
import time

logger = logging.getLogger(__name__)


class PIDController:
    """
    PID Controller with output clamping
    
    Used to convert error (e.g., Cross-Track Error) to control output
    (e.g., speed modulation for differential steering)
    """
    
    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        output_limit: float = 1.0
    ):
        """
        Initialize PID Controller
        
        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_limit: Maximum absolute output value (clamping)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limit = output_limit
        
        # Internal state
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = None
        
        logger.info(f"PID Controller initialized: Kp={kp}, Ki={ki}, Kd={kd}, limit=±{output_limit}")
    
    def update(self, error: float, dt: float = 0.1) -> float:
        """
        Update PID controller with current error
        
        Args:
            error: Current error value (e.g., CTE in meters)
            dt: Time step in seconds (default: 0.1s for 10Hz)
        
        Returns:
            Control output (clamped to ±output_limit)
        
        Example:
            error = 0.12  # 12cm right of line
            output = pid.update(error)  # e.g., -0.10 (should steer left)
        """
        # Proportional term
        p_term = self.kp * error
        
        # Integral term (accumulated error over time)
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term (rate of change of error)
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        d_term = self.kd * derivative
        
        # Calculate total output
        output = p_term + i_term + d_term
        
        # Clamp output to limits
        output = max(-self.output_limit, min(self.output_limit, output))
        
        # Anti-windup: prevent integral term from growing too large
        # If output is saturated, don't accumulate integral
        if abs(output) >= self.output_limit:
            self.integral -= error * dt  # Undo the integral accumulation
        
        # Update state for next iteration
        self.prev_error = error
        
        return output
    
    def reset(self) -> None:
        """
        Reset PID controller state
        
        Call this when starting a new control task (e.g., new waypoint)
        to prevent old integral/derivative terms from affecting new control
        """
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = None
        logger.debug("PID Controller reset")
    
    def get_state(self) -> dict:
        """
        Get current PID state for debugging
        
        Returns:
            Dictionary with current state values
        """
        return {
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'output_limit': self.output_limit,
            'integral': self.integral,
            'prev_error': self.prev_error
        }
    
    def set_gains(self, kp: float = None, ki: float = None, kd: float = None) -> None:
        """
        Update PID gains during runtime (for tuning)
        
        Args:
            kp: New proportional gain (optional)
            ki: New integral gain (optional)
            kd: New derivative gain (optional)
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd
        
        logger.info(f"PID gains updated: Kp={self.kp}, Ki={self.ki}, Kd={self.kd}")
