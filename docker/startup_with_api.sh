#!/bin/bash
# Startup script with API server for AV Metadata Scraper

set -e

echo "Starting AV Metadata Scraper with API Server..."

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Force use system chromedriver - prevent Selenium auto-download
export SE_SKIP_DRIVER_DOWNLOAD=1
export WDM_LOCAL=1
export SE_DRIVER_PATH=/usr/bin/chromedriver

# Create necessary directories
mkdir -p /app/logs /app/source /app/target /app/config

# Check if config exists
if [ ! -f /app/config/config.yaml ]; then
    echo "Creating default config..."
    cp /app/config/config.yaml.example /app/config/config.yaml 2>/dev/null || true
fi

# Function to handle shutdown
cleanup() {
    echo "Shutting down services..."
    kill $API_PID $MAIN_PID 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Start API server in background
echo "Starting API server on port 5555..."
python -m src.api_server &
API_PID=$!

# Give API server time to start
sleep 3

# Start main application
echo "Starting main scraper application..."
python /app/main.py &
MAIN_PID=$!

# Wait for both processes
wait $API_PID $MAIN_PID