#!/bin/bash
# M.A.R.K. Rover - Web Interface Start Script
# Usage: ./start_webui.sh

# Navigate to project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================="
echo "M.A.R.K. Rover - Starting Web UI"
echo "================================="

# Activate virtual environment if exists
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠ Warning: Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo "✗ Error: app.py not found!"
    exit 1
fi

echo "✓ Starting Flask web server..."
echo ""
echo "  Access URL: http://0.0.0.0:5000"
echo "  Local:      http://localhost:5000"
echo "  Network:    http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Press Ctrl+C to stop"
echo "================================="
echo ""

# Start Flask app
python3 app.py
