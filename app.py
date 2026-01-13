"""
M.A.R.K. Rover - Modern Web Application
Flask server with beautiful UI for rover control, route planning, and real-time monitoring
"""

import os
import json
import logging
import threading
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
from typing import Optional
import time
from datetime import datetime

# Import rover modules
from utils import setup_logging
from config_validator import validate_config
from rover_state import RoverState

logger = logging.getLogger(__name__)

# Global rover instance (initialized in main)
rover_system = None
rover_lock = threading.Lock()

# Flask app
app = Flask(__name__)
CORS(app)

# Configuration
CONFIG_FILE = 'config.json'

# Routes directory - use local project directory
ROUTES_DIR = os.path.join(os.path.dirname(__file__), 'routes')


# Error Log System
class ErrorLogHandler:
    """Track errors with timestamps for WebApp display"""
    def __init__(self, max_errors=50):
        self.errors = []
        self.max_errors = max_errors
        self.lock = threading.Lock()
    
    def add_error(self, level: str, message: str, source: str = "system"):
        """Add error to history"""
        with self.lock:
            error = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'level': level,  # 'ERROR', 'WARNING', 'CRITICAL'
                'message': message,
                'source': source
            }
            self.errors.insert(0, error)  # Newest first
            
            # Limit history size
            if len(self.errors) > self.max_errors:
                self.errors = self.errors[:self.max_errors]
            
            logger.log(
                logging.ERROR if level == 'ERROR' else 
                logging.WARNING if level == 'WARNING' else 
                logging.CRITICAL,
                f"[{source}] {message}"
            )
    
    def get_errors(self, limit: int = None):
        """Get error history"""
        with self.lock:
            if limit:
                return self.errors[:limit]
            return self.errors.copy()
    
    def clear_errors(self):
        """Clear all errors"""
        with self.lock:
            self.errors = []


# Global error log handler
error_log = ErrorLogHandler()



def load_config():
    """Load configuration from config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def convert_webapp_route_to_waypoints(route_data: dict) -> list:
    """
    Convert WebApp route format to Rover waypoint format
    WebApp Format:
    {
        "coordinates": [[lat, lon, alt?], ...],  # altitude is optional
        "segmentColors": ["#4a90e2", ...],
        "symbols": [{type, position}, ...],
        "name": "Route Name",
        "created": "ISO timestamp"
    }
    
    Rover Format:
    [
        {"lat": 50.933, "lon": 6.988, "altitude_m": 100.0, "speed_ms": 0.3},
        ...
    ]
    
    Color to Speed Mapping:
    - Red (#ef4444): 0.1 m/s (slow)
    - Orange (#f59e0b): 0.15 m/s
    - Yellow (#eab308): 0.2 m/s (medium)
    - Green (#22c55e): 0.3 m/s (normal)
    - Blue (#3b82f6): 0.5 m/s (fast)
    - Purple (#8b5cf6): 0.4 m/s
    - Other: 0.3 m/s (default)
    """
    coordinates = route_data.get('coordinates', [])
    segment_colors = route_data.get('segmentColors', [])
    
    # Color to speed mapping
    color_speed_map = {
        '#ef4444': 0.1,  # Red - slow
        '#f59e0b': 0.15, # Orange
        '#eab308': 0.2,  # Yellow - medium
        '#22c55e': 0.3,  # Green - normal
        '#3b82f6': 0.5,  # Blue - fast
        '#8b5cf6': 0.4,  # Purple
        '#ec4899': 0.35, # Pink
        '#6b7280': 0.25  # Gray
    }
    
    waypoints = []
    for i, coord in enumerate(coordinates):
        # Get speed from segment color (if available)
        speed = 0.3  # default
        if i < len(segment_colors):
            color = segment_colors[i]
            speed = color_speed_map.get(color, 0.3)
        
        # Extract lat, lon, altitude (if available)
        lat = coord[0]
        lon = coord[1]
        altitude = coord[2] if len(coord) > 2 else None
        
        waypoint = {
            'lat': lat,
            'lon': lon,
            'speed_ms': speed
        }
        
        # Add altitude if available
        if altitude is not None:
            waypoint['altitude_m'] = altitude
        
        waypoints.append(waypoint)
    
    return waypoints


@app.route('/')
def index():
    """Serve main dashboard with map and status displays"""
    return render_template('index.html')


@app.route('/new_job')
def new_job():
    """Serve route planning interface"""
    return render_template('new_job.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get basic rover status"""
    try:
        if rover_system is None:
            return jsonify({
                'mode': 'test',
                'state': 'DISCONNECTED',
                'error': 'Rover system not initialized (Test Mode)'
            }), 200
        
        with rover_lock:
            status = rover_system.get_status()
        
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    """
    Get full telemetry data
    
    Returns both real and simulated data depending on mode
    """
    try:
        mode = request.args.get('mode', 'live')
        
        if mode == 'test' or rover_system is None:
            # Return simulated test data (0 = missing/simulated, shown in red)
            return jsonify({
                'timestamp': time.time(),
                'mode': 'test',
                'state': 'IDLE',
                'position': {
                    'lat': 0.0,  # Simulated - no real GPS
                    'lon': 0.0
                },
                'heading_deg': 0.0,
                'speed_ms': 0.0,
                'current_waypoint': {
                    'index': 0,
                    'total': 0
                },
                'gnss': {
                    'fix_quality': 'Simulated',
                    'rtk_status': 'none',
                    'accuracy_cm': 0,
                    'num_satellites': 0,
                    'hdop': 0.0,
                    'connection': 'none'
                },
                'motors': {
                    'left_speed_ms': 0.0,
                    'right_speed_ms': 0.0,
                    'left_current_a': 0.0,
                    'right_current_a': 0.0
                },
                'battery_v': 0.0,
                'power_w': 0.0,
                'battery_percent': 0,
                'storage_gb': 0,
                'cpu_percent': 0,
                'cross_track_error_m': 0.0,
                'internet_connection': 'unknown',
                'error': 'Test Mode - No Hardware Connected'
            }), 200
        
        # Live mode - get real data from rover
        with rover_lock:
            telemetry = rover_system.get_telemetry()
        
        # Add calculated fields
        battery_v = telemetry.get('battery_v', 0.0) or 0.0
        left_current = telemetry.get('motors', {}).get('left_current_a', 0.0) or 0.0
        right_current = telemetry.get('motors', {}).get('right_current_a', 0.0) or 0.0
        total_current = left_current + right_current
        
        telemetry['mode'] = 'live'
        telemetry['power_w'] = round(battery_v * total_current, 2)
        
        # Calculate battery percentage (12V system: 11V=0%, 12.6V=100%)
        battery_percent = max(0, min(100, ((battery_v - 11.0) / 1.6) * 100))
        telemetry['battery_percent'] = round(battery_percent)
        
        # Add system stats (placeholder for now)
        telemetry['storage_gb'] = 64  # TODO: Get real value
        telemetry['cpu_percent'] = 55  # TODO: Get real value
        
        # Add RTK status and accuracy indicators
        gnss = telemetry.get('gnss', {})
        fix_quality = gnss.get('fix_quality', 'Invalid')
        hdop = gnss.get('hdop', 99.9)
        
        # RTK Status and Accuracy
        if fix_quality == 'RTK Fixed':
            gnss['rtk_status'] = 'fixed'
            gnss['accuracy_cm'] = 2
            gnss['connection'] = 'excellent'
        elif fix_quality == 'RTK Float':
            gnss['rtk_status'] = 'float'
            gnss['accuracy_cm'] = 10
            gnss['connection'] = 'good'
        elif fix_quality in ['GPS', 'DGPS']:
            gnss['rtk_status'] = 'none'
            gnss['accuracy_cm'] = 500
            gnss['connection'] = 'fair'
        else:
            gnss['rtk_status'] = 'none'
            gnss['accuracy_cm'] = 0
            gnss['connection'] = 'poor'
        
        # NTRIP Connection (check if str2str service is running)
        try:
            import subprocess
            result = subprocess.run(['systemctl', 'is-active', 'rtk-ntrip'], 
                                  capture_output=True, text=True, timeout=1)
            telemetry['internet_connection'] = 'good' if result.returncode == 0 else 'poor'
        except:
            telemetry['internet_connection'] = 'unknown'
        
        return jsonify(telemetry), 200
        
    except Exception as e:
        logger.error(f"Telemetry error: {e}")
        return jsonify({'error': str(e)}), 500


def telemetry_stream():
    """
    Server-Sent Events stream for real-time telemetry updates
    
    Yields telemetry data every 500ms
    """
    while True:
        try:
            # Get telemetry
            if rover_system is None:
                # Test mode data
                data = {
                    'timestamp': time.time(),
                    'mode': 'test',
                    'state': 'IDLE',
                    'position': {'lat': 50.9333833, 'lon': 6.9885841},
                    'heading_deg': 245.0,
                    'battery_percent': 87,
                    'battery_v': 12.2,
                    'power_w': 0.0,
                    'gnss': {
                        'fix_quality': 'RTK Fixed',
                        'num_satellites': 18,
                        'hdop': 0.8,
                        'connection': 'excellent'
                    },
                    'storage_gb': 64,
                    'cpu_percent': 55
                }
            else:
                with rover_lock:
                    data = rover_system.get_telemetry()
                
                # Add calculated fields
                battery_v = data.get('battery_v', 0.0) or 0.0
                battery_percent = max(0, min(100, ((battery_v - 11.0) / 1.6) * 100))
                data['battery_percent'] = round(battery_percent)
                
                # Add system stats
                data['storage_gb'] = 64  # TODO
                data['cpu_percent'] = 55  # TODO
            
            # Add latest errors (last 5)
            data['errors'] = error_log.get_errors(limit=5)
            
            # Send as SSE
            yield f"data: {json.dumps(data)}\n\n"
            
            time.sleep(0.5)  # 2 Hz update rate
            
        except GeneratorExit:
            break
        except Exception as e:
            logger.error(f"Telemetry stream error: {e}")
            time.sleep(1)


@app.route('/api/telemetry/stream')
def telemetry_stream_endpoint():
    """Server-Sent Events endpoint for real-time telemetry"""
    return Response(telemetry_stream(), mimetype='text/event-stream')


@app.route('/api/rover/start', methods=['POST'])
def start_mission():
    """Start autonomous mission"""
    try:
        data = request.get_json() or {}
        route_id = data.get('route_id')
        
        if rover_system is None:
            return jsonify({
                'status': 'error',
                'message': 'Rover system not initialized (Test mode)',
                'error': 'Cannot start mission in test mode'
            }), 400
        
        # Load route and convert to waypoints
        if route_id:
            route_file = f'route_{route_id}.json'
            route_path = os.path.join(ROUTES_DIR, route_file)
            
            if not os.path.exists(route_path):
                return jsonify({
                    'status': 'error',
                    'error': 'Route not found'
                }), 404
            
            # Load route data
            with open(route_path, 'r', encoding='utf-8') as f:
                route_data = json.load(f)
            
            # Convert to waypoints format
            waypoints = convert_webapp_route_to_waypoints(route_data)
            
            # Save to waypoints.json
            with open('waypoints.json', 'w', encoding='utf-8') as f:
                json.dump(waypoints, f, indent=2)
            
            logger.info(f"Converted route {route_id} to waypoints.json ({len(waypoints)} waypoints)")
        
        # Check RTK status before starting (Safety Check)
        with rover_lock:
            gnss_status = rover_system.gnss.get_status() if rover_system.gnss else None
        
        if gnss_status:
            fix_quality = gnss_status.get('fix_quality', 0)
            fix_str = gnss_status.get('fix_quality_str', 'Unknown')
            
            # Require RTK Float (5) or RTK Fixed (4)
            if fix_quality < 4:
                return jsonify({
                    'status': 'error',
                    'message': 'RTK GPS nicht bereit!',
                    'error': f'Benötigt RTK Float oder RTK Fixed. Aktuell: {fix_str}',
                    'fix_quality': fix_str,
                    'satellites': gnss_status.get('num_satellites', 0),
                    'hdop': gnss_status.get('hdop', 99.9)
                }), 400
            
            logger.info(f"RTK Status OK: {fix_str} - Starting mission")
        
        # Load mission
        with rover_lock:
            success = rover_system.load_mission('waypoints.json')
        
        if success:
            return jsonify({
                'status': 'starting',
                'message': f'Mission gestartet mit {fix_str}'
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
            'error': str(e)
        }), 500


@app.route('/api/rover/stop', methods=['POST'])
def stop_rover():
    """Gentle stop - return to IDLE"""
    try:
        if rover_system is None:
            return jsonify({'status': 'ok', 'message': 'Test mode - no action'}), 200
        
        with rover_lock:
            rover_system.gentle_stop()
        
        return jsonify({
            'status': 'stopped',
            'state': 'IDLE'
        }), 200
        
    except Exception as e:
        logger.error(f"Stop error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rover/emergency_stop', methods=['POST'])
def emergency_stop():
    """Emergency stop (hard stop)"""
    try:
        if rover_system is None:
            return jsonify({'status': 'ok', 'message': 'Test mode - no action'}), 200
        
        with rover_lock:
            rover_system.emergency_stop("Emergency stop button pressed")
        
        return jsonify({
            'status': 'emergency',
            'state': 'EMERGENCY_STOP'
        }), 200
        
    except Exception as e:
        logger.error(f"Emergency stop error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rover/manual', methods=['POST'])
def manual_control():
    """
    Manual rover control (real-time)
    
    Commands: FORWARD, BACKWARD, LEFT, RIGHT, STOP
    Speed: 0.0 - 1.0 (percentage of max speed)
    """
    try:
        data = request.get_json() or {}
        command = data.get('command', 'STOP').upper()
        speed = float(data.get('speed', 0.5))  # Default 50%
        
        # Clamp speed to valid range
        speed = max(0.0, min(1.0, speed))
        
        if rover_system is None:
            return jsonify({
                'status': 'ok',
                'message': 'Test mode - no hardware',
                'command': command,
                'speed': speed
            }), 200
        
        # Map commands to motor actions
        with rover_lock:
            if command == 'FORWARD':
                # Drive forward at specified speed
                rover_system.set_motor_speeds(speed, speed)
                logger.debug(f"Manual: FORWARD at {speed:.2f}")
                
            elif command == 'BACKWARD':
                # Drive backward at specified speed
                rover_system.set_motor_speeds(-speed, -speed)
                logger.debug(f"Manual: BACKWARD at {speed:.2f}")
                
            elif command == 'LEFT':
                # Turn left (left motor slower/reverse, right motor forward)
                rover_system.set_motor_speeds(-speed * 0.5, speed)
                logger.debug(f"Manual: LEFT at {speed:.2f}")
                
            elif command == 'RIGHT':
                # Turn right (right motor slower/reverse, left motor forward)
                rover_system.set_motor_speeds(speed, -speed * 0.5)
                logger.debug(f"Manual: RIGHT at {speed:.2f}")
                
            elif command == 'STOP':
                # Stop all motors
                rover_system.set_motor_speeds(0.0, 0.0)
                logger.debug("Manual: STOP")
                
            else:
                return jsonify({
                    'status': 'error',
                    'error': f'Unknown command: {command}'
                }), 400
        
        return jsonify({
            'status': 'ok',
            'command': command,
            'speed': speed
        }), 200
        
    except Exception as e:
        logger.error(f"Manual control error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/save_route', methods=['POST'])
def save_route():
    """Save a new route from WebApp"""
    try:
        data = request.json
        
        # Generate unique ID based on timestamp
        route_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Add ID to data
        data['id'] = route_id
        
        # Ensure routes directory exists
        try:
            # Check if routes exists as a file instead of directory
            if os.path.exists(ROUTES_DIR) and not os.path.isdir(ROUTES_DIR):
                logger.error(f"'{ROUTES_DIR}' exists but is not a directory")
                return jsonify({
                    'success': False, 
                    'error': f"'{ROUTES_DIR}' existiert als Datei. Bitte löschen Sie sie."
                }), 500
            
            # Create directory if it doesn't exist
            if not os.path.exists(ROUTES_DIR):
                os.makedirs(ROUTES_DIR, exist_ok=True)
                logger.info(f"Created routes directory: {ROUTES_DIR}")
        except PermissionError as pe:
            logger.error(f"Permission denied creating routes directory: {pe}")
            return jsonify({
                'success': False,
                'error': f"Keine Berechtigung für Verzeichnis '{ROUTES_DIR}'"
            }), 500
        except OSError as oe:
            logger.error(f"OS error creating routes directory: {oe}")
            return jsonify({
                'success': False,
                'error': f"Verzeichnisfehler: {str(oe)}"
            }), 500
        
        # Save to JSON file
        filename = f'route_{route_id}.json'
        filepath = os.path.join(ROUTES_DIR, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except PermissionError:
            logger.error(f"Permission denied writing to {filepath}")
            return jsonify({
                'success': False,
                'error': f"Keine Schreibberechtigung für '{filepath}'"
            }), 500
        except Exception as write_error:
            logger.error(f"Error writing route file: {write_error}")
            return jsonify({
                'success': False,
                'error': f"Fehler beim Schreiben: {str(write_error)}"
            }), 500
        
        logger.info(f"Route saved: {filename}")
        
        return jsonify({'success': True, 'id': route_id})
    
    except Exception as e:
        logger.error(f"Save route error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/routes', methods=['GET'])
def get_routes():
    """Get list of all saved routes"""
    try:
        routes = []
        
        if not os.path.exists(ROUTES_DIR):
            return jsonify({'success': True, 'routes': []})
        
        for filename in os.listdir(ROUTES_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(ROUTES_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        route_data = json.load(f)
                    # Only include metadata for list view
                    route_id = route_data.get('id', filename.replace('route_', '').replace('.json', ''))
                    routes.append({
                        'id': route_id,
                        'name': route_data.get('name', 'Unbenannte Route'),
                        'created': route_data.get('created', '')
                    })
                except Exception as e:
                    logger.warning(f"Could not load route {filename}: {e}")
        
        # Sort by creation date (newest first) - handle None/empty values
        routes.sort(key=lambda x: x.get('created') or '', reverse=True)
        
        return jsonify({'success': True, 'routes': routes})
    
    except Exception as e:
        logger.error(f"Get routes error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/route/<route_id>', methods=['GET'])
def get_route(route_id):
    """Get a specific route by ID"""
    try:
        filename = f'route_{route_id}.json'
        filepath = os.path.join(ROUTES_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Route not found'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        return jsonify({'success': True, 'route': route_data})
    
    except Exception as e:
        logger.error(f"Get route error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/route/<route_id>', methods=['DELETE'])
def delete_route(route_id):
    """Delete a specific route by ID"""
    try:
        filename = f'route_{route_id}.json'
        filepath = os.path.join(ROUTES_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Route not found'}), 404
        
        os.remove(filepath)
        logger.info(f"Route deleted: {filename}")
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Delete route error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Get error log history"""
    try:
        limit = request.args.get('limit', type=int)
        errors = error_log.get_errors(limit=limit)
        return jsonify({
            'success': True,
            'errors': errors,
            'count': len(errors)
        }), 200
    except Exception as e:
        logger.error(f"Get errors error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/errors/clear', methods=['POST'])
def clear_errors():
    """Clear all errors"""
    try:
        error_log.clear_errors()
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Clear errors error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get rover configuration"""
    try:
        config = load_config()
        # Remove sensitive data
        if 'ntrip' in config and 'password' in config['ntrip']:
            config['ntrip']['password'] = '***'
        
        return jsonify(config), 200
        
    except Exception as e:
        logger.error(f"Get config error: {e}")
        return jsonify({'error': str(e)}), 500


def init_rover_system():
    """
    Initialize rover control system
    
    Returns None if in test mode (hardware not available)
    """
    global rover_system
    
    try:
        # Try to import and initialize rover
        from main import RoverControlSystem
        
        config_file = 'config.json'
        rover_system = RoverControlSystem(config_file)
        
        # Try to initialize hardware
        if rover_system.initialize_hardware():
            logger.info("Rover system initialized successfully (LIVE MODE)")
            return True
        else:
            logger.warning("Hardware initialization failed - running in TEST MODE")
            rover_system = None
            return False
            
    except Exception as e:
        logger.warning(f"Could not initialize rover system: {e}")
        logger.info("Running in TEST MODE (simulated data)")
        rover_system = None
        return False


def main():
    """Main entry point"""
    # Setup logging
    setup_logging(level=logging.INFO)
    
    logger.info("="*60)
    logger.info("M.A.R.K. Rover - Modern Web Interface")
    logger.info("="*60)
    
    # Try to initialize rover system
    init_rover_system()
    
    # Add some demo errors for testing (remove in production)
    error_log.add_error('WARNING', 'GPS-Signal schwach - nur 4 Satelliten verfügbar', 'gnss')
    error_log.add_error('ERROR', 'NTRIP-Verbindung unterbrochen', 'ntrip')
    
    # Get network IP addresses
    import socket
    hostname = socket.gethostname()
    
    try:
        # Get all IP addresses
        import netifaces
        ip_addresses = []
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if not ip.startswith('127.'):  # Skip localhost
                        ip_addresses.append(ip)
    except:
        # Fallback method
        ip_addresses = []
        try:
            # Try to get primary IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_addresses.append(s.getsockname()[0])
            s.close()
        except:
            pass
    
    # Start web server
    host = '0.0.0.0'
    port = 5000
    
    logger.info(f"Starting web server on http://{host}:{port}")
    logger.info("="*60)
    logger.info("🌐 WEB-INTERFACE ZUGRIFF:")
    logger.info("="*60)
    
    if ip_addresses:
        for ip in ip_addresses:
            logger.info(f"📱 Handy/PC:  http://{ip}:{port}")
    else:
        logger.info(f"📱 Handy/PC:  http://{hostname}.local:{port}")
    
    logger.info(f"🖥️  Lokal:     http://localhost:{port}")
    logger.info("="*60)
    logger.info("Press Ctrl+C to stop")
    logger.info("="*60)
    
    app.run(
        host=host,
        port=port,
        debug=False,
        threaded=True
    )


if __name__ == '__main__':
    main()
