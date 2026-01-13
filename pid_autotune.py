"""
PID Auto-Tune Module for M.A.R.K. Rover
Implements Relay-Feedback method for automatic PID parameter tuning
"""

import logging
import math
import time
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class PIDAutoTune:
    """
    PID Auto-Tuner using Relay-Feedback Method
    
    This is more robust than Ziegler-Nichols for outdoor robotics
    where conditions may vary (wind, slippage, GPS drift)
    """
    
    def __init__(self, setpoint: float = 0.0, output_step: float = 0.5):
        """
        Initialize Auto-Tuner
        
        Args:
            setpoint: Target value (usually 0 for CTE)
            output_step: Relay amplitude for oscillation
        """
        self.setpoint = setpoint
        self.output_step = output_step
        
        # State
        self.running = False
        self.start_time = None
        self.measurements = []
        self.output_history = []
        
        # Results
        self.ultimate_gain = None
        self.ultimate_period = None
        self.tuned_kp = None
        self.tuned_ki = None
        self.tuned_kd = None
        
        logger.info(f"PID AutoTune initialized (setpoint={setpoint}, step={output_step})")
    
    def start(self) -> None:
        """Start auto-tune process"""
        self.running = True
        self.start_time = time.time()
        self.measurements = []
        self.output_history = []
        logger.info("Auto-tune started")
    
    def stop(self) -> None:
        """Stop auto-tune process"""
        self.running = False
        logger.info("Auto-tune stopped")
    
    def update(self, measured_value: float, dt: float) -> float:
        """
        Update auto-tuner with new measurement
        
        Args:
            measured_value: Current process value (e.g., CTE)
            dt: Time step in seconds
        
        Returns:
            Control output (relay value)
        """
        if not self.running:
            return 0.0
        
        # Record measurement
        timestamp = time.time() - self.start_time
        self.measurements.append((timestamp, measured_value))
        
        # Relay logic: switch output based on error
        error = measured_value - self.setpoint
        
        if error > 0:
            output = -self.output_step  # Negative correction
        else:
            output = +self.output_step  # Positive correction
        
        self.output_history.append((timestamp, output))
        
        return output
    
    def analyze(self) -> bool:
        """
        Analyze collected data and calculate PID parameters
        
        Returns:
            True if analysis successful
        """
        if len(self.measurements) < 100:
            logger.warning(f"Not enough data points: {len(self.measurements)} < 100")
            return False
        
        try:
            # Extract timestamps and values
            times = [m[0] for m in self.measurements]
            values = [m[1] for m in self.measurements]
            
            # Find oscillation period by detecting zero crossings
            crossings = self._find_zero_crossings(values, self.setpoint)
            
            if len(crossings) < 4:
                logger.warning(f"Not enough oscillations: {len(crossings)} crossings")
                return False
            
            # Calculate average period (time between consecutive crossings * 2)
            periods = []
            for i in range(0, len(crossings) - 2, 2):
                period = times[crossings[i + 2]] - times[crossings[i]]
                periods.append(period)
            
            self.ultimate_period = sum(periods) / len(periods)
            
            # Calculate oscillation amplitude
            peaks = self._find_peaks(values)
            if len(peaks) < 2:
                logger.warning("Not enough peaks found")
                return False
            
            peak_values = [abs(values[p]) for p in peaks]
            amplitude = sum(peak_values) / len(peak_values)
            
            # Ultimate gain: Ku = 4 * d / (π * a)
            # where d = relay amplitude, a = oscillation amplitude
            self.ultimate_gain = (4 * self.output_step) / (math.pi * amplitude)
            
            # Calculate PID parameters using Ziegler-Nichols tuning rules
            # Classic PID: Kp = 0.6 * Ku, Ki = 1.2 * Ku / Tu, Kd = 0.075 * Ku * Tu
            self.tuned_kp = 0.6 * self.ultimate_gain
            self.tuned_ki = 1.2 * self.ultimate_gain / self.ultimate_period
            self.tuned_kd = 0.075 * self.ultimate_gain * self.ultimate_period
            
            logger.info(f"Auto-tune complete:")
            logger.info(f"  Ultimate Period Tu = {self.ultimate_period:.2f} s")
            logger.info(f"  Ultimate Gain Ku = {self.ultimate_gain:.3f}")
            logger.info(f"  Tuned Kp = {self.tuned_kp:.3f}")
            logger.info(f"  Tuned Ki = {self.tuned_ki:.3f}")
            logger.info(f"  Tuned Kd = {self.tuned_kd:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Auto-tune analysis failed: {e}")
            return False
    
    def _find_zero_crossings(self, values: list, setpoint: float) -> list:
        """
        Find indices where signal crosses setpoint
        
        Args:
            values: Signal values
            setpoint: Zero-crossing threshold
        
        Returns:
            List of crossing indices
        """
        crossings = []
        for i in range(1, len(values)):
            if (values[i-1] - setpoint) * (values[i] - setpoint) < 0:
                crossings.append(i)
        return crossings
    
    def _find_peaks(self, values: list) -> list:
        """
        Find local maxima/minima in signal
        
        Args:
            values: Signal values
        
        Returns:
            List of peak indices
        """
        peaks = []
        for i in range(1, len(values) - 1):
            if (values[i] > values[i-1] and values[i] > values[i+1]) or \
               (values[i] < values[i-1] and values[i] < values[i+1]):
                peaks.append(i)
        return peaks
    
    def get_parameters(self) -> Optional[dict]:
        """
        Get tuned PID parameters
        
        Returns:
            Dictionary with Kp, Ki, Kd or None if not tuned yet
        """
        if self.tuned_kp is None:
            return None
        
        return {
            'kp': self.tuned_kp,
            'ki': self.tuned_ki,
            'kd': self.tuned_kd,
            'ultimate_gain': self.ultimate_gain,
            'ultimate_period': self.ultimate_period
        }
    
    def get_status(self) -> dict:
        """
        Get current auto-tune status
        
        Returns:
            Status dictionary
        """
        return {
            'running': self.running,
            'data_points': len(self.measurements),
            'duration': time.time() - self.start_time if self.start_time else 0,
            'complete': self.tuned_kp is not None,
            'parameters': self.get_parameters()
        }
