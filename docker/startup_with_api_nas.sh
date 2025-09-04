#!/bin/bash
# Startup script optimized for NAS deployment
# Includes better error handling and resource management

echo "Starting AV Metadata Scraper with API Server (NAS Optimized)..."

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Force use system chromedriver - prevent Selenium auto-download
export SE_SKIP_DRIVER_DOWNLOAD=1
export WDM_LOCAL=1
export SE_DRIVER_PATH=/usr/bin/chromedriver

# Limit resource usage for NAS
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

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
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT SIGHUP

# Function to monitor and restart API server
monitor_api() {
    while true; do
        if ! kill -0 $API_PID 2>/dev/null; then
            echo "API server died, restarting..."
            python -m src.api_server &
            API_PID=$!
            echo "API server restarted with PID $API_PID"
        fi
        sleep 30
    done
}

# Start API server with error handling
echo "Starting API server on port 5555..."
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    python -m src.api_server &
    API_PID=$!
    
    # Give API server time to start
    sleep 5
    
    # Check if process is still running
    if kill -0 $API_PID 2>/dev/null; then
        echo "API server started successfully with PID $API_PID"
        break
    else
        echo "API server failed to start, attempt $((RETRY_COUNT + 1)) of $MAX_RETRIES"
        RETRY_COUNT=$((RETRY_COUNT + 1))
        sleep 5
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Failed to start API server after $MAX_RETRIES attempts"
    exit 1
fi

# Start monitoring in background
monitor_api &
MONITOR_PID=$!

# Wait for API server process
wait $API_PID

# Clean up monitor
kill $MONITOR_PID 2>/dev/null || true