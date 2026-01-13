"""
Rover State Machine for M.A.R.K. Rover
Manages rover operational states and transitions
"""

import logging
import time
from enum import Enum
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class RoverState(Enum):
    """
    Rover operational states
    """
    IDLE = "IDLE"                       # Waiting for mission
    ROTATING = "ROTATING"               # Aligning heading to target bearing
    DRIVING = "DRIVING"                 # Following line to waypoint
    REACHED_WAYPOINT = "REACHED_WAYPOINT"  # Waypoint reached
    MISSION_COMPLETE = "MISSION_COMPLETE"  # All waypoints completed
    ERROR = "ERROR"                     # Non-critical error
    EMERGENCY_STOP = "EMERGENCY_STOP"   # Critical error - motors stopped


class RoverStateMachine:
    """
    State machine for rover control
    
    Manages state transitions, error handling, and state history
    """
    
    def __init__(self):
        """
        Initialize state machine
        """
        self.current_state = RoverState.IDLE
        self.error_message = ""
        self.emergency_reason = ""
        
        # State history: list of (state, timestamp, reason)
        self.state_history: List[Tuple[RoverState, float, str]] = []
        self.max_history = 20
        
        logger.info("Rover State Machine initialized")
        self._add_to_history(RoverState.IDLE, "Initialization")
    
    def set_state(self, new_state: RoverState, reason: str = "") -> None:
        """
        Transition to new state
        
        Args:
            new_state: Target state
            reason: Reason for transition
        """
        if new_state != self.current_state:
            logger.info(f"State transition: {self.current_state.value} → {new_state.value} ({reason})")
            self.current_state = new_state
            self._add_to_history(new_state, reason)
    
    def get_state(self) -> RoverState:
        """
        Get current state
        
        Returns:
            Current state
        """
        return self.current_state
    
    def set_error(self, message: str) -> None:
        """
        Set error state with message
        
        Args:
            message: Error description
        """
        self.error_message = message
        logger.error(f"Error state set: {message}")
        self.set_state(RoverState.ERROR, message)
    
    def emergency_stop(self, reason: str = "") -> None:
        """
        Trigger emergency stop
        
        Args:
            reason: Reason for emergency stop
        """
        self.emergency_reason = reason
        logger.critical(f"EMERGENCY STOP: {reason}")
        self.set_state(RoverState.EMERGENCY_STOP, reason)
    
    def clear_error(self) -> None:
        """
        Clear error and return to IDLE
        """
        if self.current_state in [RoverState.ERROR, RoverState.EMERGENCY_STOP]:
            self.error_message = ""
            self.emergency_reason = ""
            logger.info("Error cleared, returning to IDLE")
            self.set_state(RoverState.IDLE, "Error cleared")
        else:
            logger.warning("Cannot clear error - not in error state")
    
    def is_operational(self) -> bool:
        """
        Check if rover is in operational state (not error/emergency)
        
        Returns:
            True if operational
        """
        return self.current_state not in [RoverState.ERROR, RoverState.EMERGENCY_STOP]
    
    def get_state_history(self) -> List[Tuple[RoverState, float, str]]:
        """
        Get state transition history
        
        Returns:
            List of (state, timestamp, reason) tuples
        """
        return self.state_history.copy()
    
    def _add_to_history(self, state: RoverState, reason: str) -> None:
        """
        Add state transition to history
        
        Args:
            state: New state
            reason: Transition reason
        """
        self.state_history.append((state, time.time(), reason))
        
        # Limit history size
        if len(self.state_history) > self.max_history:
            self.state_history = self.state_history[-self.max_history:]
    
    def get_status(self) -> dict:
        """
        Get comprehensive state machine status
        
        Returns:
            Dictionary with current status
        """
        return {
            'state': self.current_state.value,
            'operational': self.is_operational(),
            'error_message': self.error_message,
            'emergency_reason': self.emergency_reason
        }
