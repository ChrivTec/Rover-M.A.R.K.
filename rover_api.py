"""
Flask REST API for M.A.R.K. Rover
Web interface integration with rover control system
"""

import logging
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from typing import Optional

logger = logging.getLogger(__name__)


class RoverAPI:
    """
    Flask REST API for rover control
    
    Provides endpoints for mission control, status, and telemetry
    Thread-safe access to RoverControlSystem
    """
    
    def __init__(self, rover_control_system, host: str = '0.0.0.0', port: int = 5000):
        """
        Initialize Rover API
        
        Args:
            rover_control_system: Instance of RoverControlSystem
            host: API host address (default: 0.0.0.0 = all interfaces)
            port: API port (default: 5000)
        """
        self.rover = rover_control_system
        self.host = host
        self.port = port
        
        # Flask app
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for web interface
        
        # Thread-safe lock for rover access
        self.lock = threading.Lock()
        
        # Register routes
        self._register_routes()
        
        logger.info(f"Rover API initialized on {host}:{port}")
    
    def _register_routes(self) -> None:
        """
        Register API endpoints
        """
        @self.app.route('/api/rover/start_mission', methods=['POST'])
        def start_mission():
            """
            Start autonomous mission
            
            Request body:
            {
                "route_file": "waypoints.json"
            }
            """
            try:
                data = request.get_json()
                route_file = data.get('route_file', 'waypoints.json')
                
                with self.lock:
                    success = self.rover.load_mission(route_file)
                
                if success:
                    return jsonify({
                        'status': 'starting',
                        'message': f'Mission loaded from {route_file}',
                        'error': None
                    }), 200
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to load mission',
                        'error': 'Invalid route file'
                    }), 400
                    
            except Exception as e:
                logger.error(f"Start mission error: {e}")
                return jsonify({
                    'status': 'error',
                    'message': 'Internal error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/rover/stop', methods=['POST'])
        def stop():
            """
            Stop rover (gentle stop, return to IDLE)
            """
            try:
                with self.lock:
                    self.rover.gentle_stop()
                
                return jsonify({
                    'status': 'stopped',
                    'state': 'IDLE'
                }), 200
                
            except Exception as e:
                logger.error(f"Stop error: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/rover/emergency_stop', methods=['POST'])
        def emergency_stop():
            """
            Emergency stop (hard stop)
            """
            try:
                with self.lock:
                    self.rover.emergency_stop("Emergency stop button pressed")
                
                return jsonify({
                    'status': 'emergency',
                    'state': 'EMERGENCY_STOP'
                }), 200
                
            except Exception as e:
                logger.error(f"Emergency stop error: {e}")
                return jsonify({
                    'status': 'error',
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/rover/status', methods=['GET'])
        def get_status():
            """
            Get basic rover status
            """
            try:
                with self.lock:
                    status = self.rover.get_status()
                
                return jsonify(status), 200
                
            except Exception as e:
                logger.error(f"Get status error: {e}")
                return jsonify({
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/rover/telemetry', methods=['GET'])
        def get_telemetry():
            """
            Get full telemetry data
            
            Returns comprehensive data including:
            - Position, heading, speed
            - GNSS status (fix quality, satellites, HDOP)
            - Motor status (currents, battery)
            - Waypoint progress
            """
            try:
                with self.lock:
                    telemetry = self.rover.get_telemetry()
                
                return jsonify(telemetry), 200
                
            except Exception as e:
                logger.error(f"Get telemetry error: {e}")
                return jsonify({
                    'error': str(e)
                }), 500
    
    def start(self) -> None:
        """
        Start Flask API server in separate thread
        """
        api_thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        api_thread.start()
        logger.info("Rover API server started in background thread")
    
    def _run_server(self) -> None:
        """
        Run Flask server
        """
        self.app.run(
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False
        )
