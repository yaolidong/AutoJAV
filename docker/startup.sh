#!/bin/bash
set -e

# AV Metadata Scraper Docker Startup Script
# This script handles container initialization and startup

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Initialize directories
init_directories() {
    log_info "Initializing directories..."
    
    # Create required directories if they don't exist
    mkdir -p /app/logs /app/config /app/source /app/target /app/.chrome-data
    
    # Set proper permissions based on PUID/PGID if provided
    if [[ -n "$PUID" && -n "$PGID" ]]; then
        log_info "Setting ownership to PUID=$PUID, PGID=$PGID"
        chown -R "$PUID:$PGID" /app/logs /app/config /app/.chrome-data
        # Don't change ownership of source (read-only) and target (may be mounted)
    fi
    
    log_success "Directories initialized"
}

# Initialize configuration
init_config() {
    log_info "Initializing configuration..."
    
    # Copy default config if none exists
    if [[ ! -f /app/config/config.yaml ]]; then
        if [[ -f /app/config/config.yaml.template ]]; then
            log_info "Creating config.yaml from template"
            cp /app/config/config.yaml.template /app/config/config.yaml
        elif [[ -f /app/config/config.yaml.example ]]; then
            log_info "Creating config.yaml from example"
            cp /app/config/config.yaml.example /app/config/config.yaml
        else
            log_warning "No configuration template found"
        fi
    fi
    
    # Update config with environment variables if provided
    if [[ -n "$JAVDB_USERNAME" || -n "$JAVDB_PASSWORD" ]]; then
        log_info "Updating configuration with environment credentials"
        # This would require a Python script to properly update YAML
        # For now, just log that credentials are available
        log_info "JavDB credentials provided via environment"
    fi
    
    log_success "Configuration initialized"
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Chrome/Chromium installation
    if command -v chromium &> /dev/null; then
        log_info "Chromium found"
    elif command -v google-chrome &> /dev/null; then
        log_info "Google Chrome found"
    else
        log_error "Chrome/Chromium not found"
        exit 1
    fi
    
    # Check ChromeDriver installation
    if ! command -v chromedriver &> /dev/null; then
        log_error "ChromeDriver not found"
        exit 1
    fi
    
    # Check Python environment
    if ! python -c "import selenium, requests, yaml, bs4" &> /dev/null; then
        log_error "Required Python packages not available"
        exit 1
    fi
    
    # Check directory permissions
    for dir in /app/logs /app/config; do
        if [[ ! -w "$dir" ]]; then
            log_error "Directory $dir is not writable"
            exit 1
        fi
    done
    
    log_success "System requirements check passed"
}

# Setup Chrome for container environment
setup_chrome() {
    log_info "Setting up Chrome for container environment..."
    
    # Create Chrome user data directory
    mkdir -p /app/.chrome-data
    
    # Set Chrome environment variables
    if command -v chromium &> /dev/null; then
        export CHROME_BIN=/usr/bin/chromium
    else
        export CHROME_BIN=/usr/bin/google-chrome
    fi
    export CHROMEDRIVER_PATH=/usr/bin/chromedriver
    export DISPLAY=${DISPLAY:-:99}
    
    # Test Chrome installation
    if $CHROME_BIN --version &> /dev/null; then
        log_success "Chrome setup completed"
    else
        log_error "Chrome setup failed"
        exit 1
    fi
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment..."
    
    # Set Python path
    export PYTHONPATH=/app/src:$PYTHONPATH
    export PYTHONUNBUFFERED=1
    
    # Test Python imports
    if python -c "import sys; sys.path.insert(0, '/app'); import src.utils.logging_config; import src.main_application" 2>/dev/null; then
        log_success "Python environment setup completed"
    else
        # Try with more detailed error output for debugging
        log_warning "Testing Python environment with detailed output..."
        python -c "import sys; sys.path.insert(0, '/app'); print('Python path:', sys.path); import src.utils.logging_config; import src.main_application; print('Import successful')"
        if [ $? -eq 0 ]; then
            log_success "Python environment setup completed"
        else
            log_error "Python environment setup failed"
            exit 1
        fi
    fi
}

# Run health check
run_health_check() {
    log_info "Running health check..."
    
    if [[ -f /app/docker/healthcheck.py ]]; then
        if python /app/docker/healthcheck.py; then
            log_success "Health check passed"
        else
            log_error "Health check failed"
            exit 1
        fi
    else
        log_warning "Health check script not found, skipping"
    fi
}

# Handle shutdown signals
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    
    # Kill any running Chrome processes
    pkill -f chrome || true
    pkill -f chromedriver || true
    
    # Clean up temporary files
    rm -rf /tmp/chrome_* /tmp/.org.chromium.* || true
    
    log_info "Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main startup function
main() {
    log_info "Starting AV Metadata Scraper container..."
    
    # Initialize container environment
    init_directories
    init_config
    check_requirements
    setup_chrome
    setup_python
    
    # Run health check if not in debug mode
    if [[ "$DEBUG_MODE" != "true" ]]; then
        run_health_check
    fi
    
    log_success "Container initialization completed"
    
    # Execute the main command
    log_info "Starting application: $*"
    exec "$@"
}

# Run main function with all arguments
main "$@"