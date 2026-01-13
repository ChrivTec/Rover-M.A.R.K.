"""
Kalman Filter for GPS position smoothing
Reduces GPS noise and provides velocity estimation
"""

import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class KalmanFilter:
    """
    Kalman Filter for GPS position smoothing
    
    State vector: [lat, lon, vel_lat, vel_lon]
    Measurement vector: [lat, lon]
    """
    
    def __init__(
        self,
        state_dim: int = 4,
        measurement_dim: int = 2,
        process_noise: float = 0.001,
        measurement_noise: float = 0.5
    ):
        """
        Initialize Kalman Filter
        
        Args:
            state_dim: Dimension of state vector (4: lat, lon, vel_lat, vel_lon)
            measurement_dim: Dimension of measurement vector (2: lat, lon)
            process_noise: Process noise covariance
            measurement_noise: Measurement noise covariance
        """
        self.state_dim = state_dim
        self.measurement_dim = measurement_dim
        
        # State vector [lat, lon, vel_lat, vel_lon]
        self.x = np.zeros((state_dim, 1))
        
        # State covariance matrix
        self.P = np.eye(state_dim) * 1000.0  # High initial uncertainty
        
        # State transition matrix (will be updated with dt in predict())
        self.F = np.eye(state_dim)
        
        # Measurement matrix (we only measure position, not velocity)
        self.H = np.zeros((measurement_dim, state_dim))
        self.H[0, 0] = 1.0  # lat
        self.H[1, 1] = 1.0  # lon
        
        # Process noise covariance
        self.Q = np.eye(state_dim) * process_noise
        
        # Measurement noise covariance
        self.R = np.eye(measurement_dim) * measurement_noise
        
        # Identity matrix
        self.I = np.eye(state_dim)
        
        self.initialized = False
        
        logger.info(f"Kalman Filter initialized (process_noise={process_noise}, measurement_noise={measurement_noise})")
    
    def predict(self, dt: float) -> None:
        """
        Prediction step: extrapolate state forward in time
        
        Args:
            dt: Time step in seconds
        """
        if not self.initialized:
            return
        
        # Update state transition matrix with current dt
        # Position updates based on velocity
        self.F[0, 2] = dt  # lat += vel_lat * dt
        self.F[1, 3] = dt  # lon += vel_lon * dt
        
        # Predict state: x = F * x
        self.x = self.F @ self.x
        
        # Predict covariance: P = F * P * F^T + Q
        self.P = self.F @ self.P @ self.F.T + self.Q
    
    def update(self, measurement: np.ndarray, noise: Optional[float] = None) -> None:
        """
        Update step: correct prediction with measurement
        
        Args:
            measurement: Measurement vector [lat, lon]
            noise: Optional custom measurement noise (overrides default R)
        """
        # Convert measurement to column vector
        z = measurement.reshape((self.measurement_dim, 1))
        
        # Initialize state with first measurement
        if not self.initialized:
            self.x[0, 0] = z[0, 0]  # lat
            self.x[1, 0] = z[1, 0]  # lon
            self.x[2, 0] = 0.0      # vel_lat
            self.x[3, 0] = 0.0      # vel_lon
            self.initialized = True
            logger.info(f"Kalman Filter initialized with first measurement: lat={z[0, 0]:.6f}, lon={z[1, 0]:.6f}")
            return
        
        # Use custom measurement noise if provided
        R = self.R
        if noise is not None:
            R = np.eye(self.measurement_dim) * noise
        
        # Innovation: y = z - H * x
        y = z - self.H @ self.x
        
        # Innovation covariance: S = H * P * H^T + R
        S = self.H @ self.P @ self.H.T + R
        
        # Kalman gain: K = P * H^T * S^-1
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        # Update state: x = x + K * y
        self.x = self.x + K @ y
        
        # Update covariance: P = (I - K * H) * P
        self.P = (self.I - K @ self.H) @ self.P
    
    def get_state(self) -> np.ndarray:
        """
        Get current state estimate
        
        Returns:
            State vector [lat, lon, vel_lat, vel_lon]
        """
        return self.x.flatten()
    
    def get_position(self) -> tuple[float, float]:
        """
        Get current position estimate
        
        Returns:
            Tuple of (latitude, longitude)
        """
        return float(self.x[0, 0]), float(self.x[1, 0])
    
    def get_velocity(self) -> tuple[float, float]:
        """
        Get current velocity estimate
        
        Returns:
            Tuple of (vel_lat, vel_lon) in degrees per second
        """
        return float(self.x[2, 0]), float(self.x[3, 0])
    
    def is_initialized(self) -> bool:
        """
        Check if filter has been initialized with first measurement
        
        Returns:
            True if initialized
        """
        return self.initialized
    
    def reset(self) -> None:
        """
        Reset filter to initial state
        """
        self.x = np.zeros((self.state_dim, 1))
        self.P = np.eye(self.state_dim) * 1000.0
        self.initialized = False
        logger.info("Kalman Filter reset")
