"""
Connection Monitor for M.A.R.K. Rover
GNSS connection watchdog - triggers emergency stop on timeout
"""

import logging
import time
import threading
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class ConnectionMonitor:
    """
    GNSS connection watchdog
    
    Monitors GPS updates and triggers emergency stop if connection is lost
    for longer than timeout period
    """
    
    def __init__(self, timeout_seconds: float = 35.0):
        """
        Initialize Connection Monitor
        
        Args:
            timeout_seconds: Maximum time without GPS update before emergency stop
        """
        self.timeout_seconds = timeout_seconds
        self.last_ping_time = time.time()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.emergency_callback: Optional[Callable] = None
        
        # Thread synchronization
        self.lock = threading.Lock()
        
        logger.info(f"Connection Monitor initialized (timeout: {timeout_seconds}s)")
    
    def start(self, emergency_callback: Optional[Callable] = None) -> None:
        """
        Start watchdog thread
        
        Args:
            emergency_callback: Function to call on timeout (e.g., emergency_stop)
        """
        if self.running:
            logger.warning("Connection Monitor already running")
            return
        
        self.emergency_callback = emergency_callback
        self.running = True
        self.last_ping_time = time.time()
        
        self.thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.thread.start()
        
        logger.info("Connection Monitor started")
    
    def stop(self) -> None:
        """
        Stop watchdog thread
        """
        if not self.running:
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        logger.info("Connection Monitor stopped")
    
    def ping(self) -> None:
        """
        Signal that GPS update was received
        
        Call this every time GPS data is successfully updated
        """
        with self.lock:
            self.last_ping_time = time.time()
    
    def is_safe(self) -> bool:
        """
        Check if connection is safe (within timeout)
        
        Returns:
            True if last update was within timeout period
        """
        with self.lock:
            time_since_last = time.time() - self.last_ping_time
            return time_since_last < self.timeout_seconds
    
    def get_time_since_last_connection(self) -> float:
        """
        Get time since last GPS update
        
        Returns:
            Seconds since last ping
        """
        with self.lock:
            return time.time() - self.last_ping_time
    
    def _watchdog_loop(self) -> None:
        """
        Watchdog thread main loop
        
        Checks connection status every second and triggers emergency stop
        if timeout is exceeded
        """
        logger.info("Watchdog thread started")
        
        while self.running:
            try:
                time_since_last = self.get_time_since_last_connection()
                
                if time_since_last > self.timeout_seconds:
                    logger.critical(f"GPS CONNECTION LOST! (timeout: {time_since_last:.1f}s)")
                    
                    # Trigger emergency callback if provided
                    if self.emergency_callback:
                        try:
                            self.emergency_callback(f"GPS connection timeout ({time_since_last:.1f}s)")
                        except Exception as e:
                            logger.error(f"Error calling emergency callback: {e}")
                    
                    # Stop monitoring (emergency already triggered)
                    self.running = False
                    break
                
                # Check every second
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                time.sleep(1.0)
        
        logger.info("Watchdog thread stopped")
