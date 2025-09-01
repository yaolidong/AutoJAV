#!/bin/bash
set -e

# Docker Management Script for AV Metadata Scraper
# This script provides easy management commands for the Docker deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/.env"

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

# Help function
show_help() {
    cat << EOF
Docker Management Script for AV Metadata Scraper

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    start           Start the application
    stop            Stop the application
    restart         Restart the application
    status          Show application status
    logs            Show application logs
    shell           Open shell in container
    update          Update and restart application
    backup          Backup configuration and data
    restore         Restore from backup
    clean           Clean up Docker resources
    setup           Initial setup and configuration
    health          Run health check
    monitor         Monitor resource usage
    help            Show this help message

Options:
    -d, --detach    Run in background (for start command)
    -f, --follow    Follow logs (for logs command)
    --dev           Use development configuration
    --prod          Use production configuration
    --no-build      Don't rebuild images (for start/update)

Examples:
    $0 setup                # Initial setup
    $0 start -d            # Start in background
    $0 logs -f             # Follow logs
    $0 shell               # Open shell
    $0 update              # Update application
    $0 backup              # Backup data
    $0 clean               # Clean up resources

EOF
}

# Check prerequisites
check_prerequisites() {
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose.yml not found in $PROJECT_DIR"
        exit 1
    fi
}

# Setup environment
setup_environment() {
    log_info "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "$PROJECT_DIR/.env.example" ]]; then
            log_info "Creating .env from .env.example"
            cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
        else
            log_info "Creating default .env file"
            cat > "$ENV_FILE" << EOF
# AV Metadata Scraper Environment Configuration
SOURCE_DIR=./source
TARGET_DIR=./organized
CONFIG_DIR=./config
LOGS_DIR=./logs
LOG_LEVEL=INFO
MAX_CONCURRENT_FILES=2
MEMORY_LIMIT=2G
CPU_LIMIT=2.0
TZ=UTC
SAFE_MODE=true
DEBUG_MODE=false
EOF
        fi
        log_warning "Please edit $ENV_FILE with your configuration"
    fi
    
    # Create required directories
    local source_dir=$(grep "^SOURCE_DIR=" "$ENV_FILE" | cut -d'=' -f2)
    local target_dir=$(grep "^TARGET_DIR=" "$ENV_FILE" | cut -d'=' -f2)
    local config_dir=$(grep "^CONFIG_DIR=" "$ENV_FILE" | cut -d'=' -f2)
    local logs_dir=$(grep "^LOGS_DIR=" "$ENV_FILE" | cut -d'=' -f2)
    
    mkdir -p "$source_dir" "$target_dir" "$config_dir" "$logs_dir"
    
    # Create config file if it doesn't exist
    if [[ ! -f "$config_dir/config.yaml" ]]; then
        if [[ -f "$PROJECT_DIR/config/config.yaml.template" ]]; then
            log_info "Creating config.yaml from template"
            cp "$PROJECT_DIR/config/config.yaml.template" "$config_dir/config.yaml"
        fi
    fi
    
    log_success "Environment setup completed"
}

# Get compose command with appropriate overrides
get_compose_cmd() {
    local cmd="docker compose -f $COMPOSE_FILE"
    
    if [[ "$USE_DEV" == "true" ]]; then
        cmd="$cmd -f $PROJECT_DIR/docker-compose.dev.yml"
    elif [[ "$USE_PROD" == "true" ]]; then
        cmd="$cmd -f $PROJECT_DIR/docker-compose.prod.yml"
    fi
    
    echo "$cmd"
}

# Start application
start_app() {
    log_info "Starting AV Metadata Scraper..."
    
    local compose_cmd=$(get_compose_cmd)
    local start_args=""
    
    if [[ "$DETACH" == "true" ]]; then
        start_args="$start_args -d"
    fi
    
    if [[ "$NO_BUILD" != "true" ]]; then
        log_info "Building images..."
        $compose_cmd build
    fi
    
    if $compose_cmd up $start_args; then
        log_success "Application started successfully"
        if [[ "$DETACH" == "true" ]]; then
            log_info "Use '$0 logs -f' to view logs"
            log_info "Use '$0 status' to check status"
        fi
    else
        log_error "Failed to start application"
        exit 1
    fi
}

# Stop application
stop_app() {
    log_info "Stopping AV Metadata Scraper..."
    
    local compose_cmd=$(get_compose_cmd)
    
    if $compose_cmd down; then
        log_success "Application stopped successfully"
    else
        log_error "Failed to stop application"
        exit 1
    fi
}

# Restart application
restart_app() {
    log_info "Restarting AV Metadata Scraper..."
    stop_app
    start_app
}

# Show status
show_status() {
    log_info "Application status:"
    
    local compose_cmd=$(get_compose_cmd)
    $compose_cmd ps
    
    echo ""
    log_info "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" 2>/dev/null || log_warning "No running containers found"
}

# Show logs
show_logs() {
    local compose_cmd=$(get_compose_cmd)
    local log_args=""
    
    if [[ "$FOLLOW" == "true" ]]; then
        log_args="$log_args -f"
    fi
    
    $compose_cmd logs $log_args av-scraper
}

# Open shell
open_shell() {
    log_info "Opening shell in container..."
    
    local compose_cmd=$(get_compose_cmd)
    
    if $compose_cmd exec av-scraper bash; then
        log_success "Shell session ended"
    else
        log_warning "Container not running, starting temporary container..."
        $compose_cmd run --rm av-scraper bash
    fi
}

# Update application
update_app() {
    log_info "Updating AV Metadata Scraper..."
    
    # Pull latest code (if in git repo)
    if [[ -d "$PROJECT_DIR/.git" ]]; then
        log_info "Pulling latest code..."
        cd "$PROJECT_DIR"
        git pull origin main || log_warning "Failed to pull latest code"
    fi
    
    # Rebuild and restart
    local compose_cmd=$(get_compose_cmd)
    
    log_info "Rebuilding images..."
    $compose_cmd build --no-cache
    
    log_info "Restarting application..."
    $compose_cmd down
    $compose_cmd up -d
    
    log_success "Application updated successfully"
}

# Backup data
backup_data() {
    log_info "Creating backup..."
    
    local backup_dir="backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup configuration
    if [[ -d "config" ]]; then
        log_info "Backing up configuration..."
        cp -r config "$backup_dir/"
    fi
    
    # Backup organized files (if not too large)
    local target_dir=$(grep "^TARGET_DIR=" "$ENV_FILE" | cut -d'=' -f2 2>/dev/null || echo "./organized")
    if [[ -d "$target_dir" ]]; then
        local size=$(du -sm "$target_dir" | cut -f1)
        if [[ $size -lt 1000 ]]; then  # Less than 1GB
            log_info "Backing up organized files..."
            cp -r "$target_dir" "$backup_dir/"
        else
            log_warning "Organized files too large ($size MB), skipping"
        fi
    fi
    
    # Backup logs
    local logs_dir=$(grep "^LOGS_DIR=" "$ENV_FILE" | cut -d'=' -f2 2>/dev/null || echo "./logs")
    if [[ -d "$logs_dir" ]]; then
        log_info "Backing up logs..."
        cp -r "$logs_dir" "$backup_dir/"
    fi
    
    # Create archive
    tar -czf "$backup_dir.tar.gz" "$backup_dir"
    rm -rf "$backup_dir"
    
    log_success "Backup created: $backup_dir.tar.gz"
}

# Restore from backup
restore_data() {
    local backup_file="$1"
    
    if [[ -z "$backup_file" ]]; then
        log_error "Please specify backup file to restore"
        exit 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_info "Restoring from backup: $backup_file"
    
    # Extract backup
    tar -xzf "$backup_file"
    local backup_dir=$(basename "$backup_file" .tar.gz)
    
    # Restore configuration
    if [[ -d "$backup_dir/config" ]]; then
        log_info "Restoring configuration..."
        cp -r "$backup_dir/config"/* config/ 2>/dev/null || true
    fi
    
    # Restore logs
    if [[ -d "$backup_dir/logs" ]]; then
        log_info "Restoring logs..."
        local logs_dir=$(grep "^LOGS_DIR=" "$ENV_FILE" | cut -d'=' -f2 2>/dev/null || echo "./logs")
        mkdir -p "$logs_dir"
        cp -r "$backup_dir/logs"/* "$logs_dir/" 2>/dev/null || true
    fi
    
    # Clean up
    rm -rf "$backup_dir"
    
    log_success "Restore completed"
}

# Clean up Docker resources
clean_resources() {
    log_info "Cleaning up Docker resources..."
    
    # Stop application first
    local compose_cmd=$(get_compose_cmd)
    $compose_cmd down 2>/dev/null || true
    
    # Remove unused images
    log_info "Removing unused images..."
    docker image prune -f
    
    # Remove unused volumes
    log_info "Removing unused volumes..."
    docker volume prune -f
    
    # Remove unused networks
    log_info "Removing unused networks..."
    docker network prune -f
    
    # Remove build cache
    log_info "Removing build cache..."
    docker builder prune -f
    
    log_success "Cleanup completed"
}

# Run health check
run_health_check() {
    log_info "Running health check..."
    
    local compose_cmd=$(get_compose_cmd)
    
    if $compose_cmd exec av-scraper python /app/docker/healthcheck.py; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi
}

# Monitor resource usage
monitor_resources() {
    log_info "Monitoring resource usage (Press Ctrl+C to stop)..."
    
    # Monitor Docker stats
    docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Parse command line arguments
parse_args() {
    COMMAND=""
    DETACH=""
    FOLLOW=""
    USE_DEV=""
    USE_PROD=""
    NO_BUILD=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|logs|shell|update|backup|restore|clean|setup|health|monitor|help)
                COMMAND="$1"
                shift
                ;;
            -d|--detach)
                DETACH="true"
                shift
                ;;
            -f|--follow)
                FOLLOW="true"
                shift
                ;;
            --dev)
                USE_DEV="true"
                shift
                ;;
            --prod)
                USE_PROD="true"
                shift
                ;;
            --no-build)
                NO_BUILD="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                # For restore command, this might be the backup file
                if [[ "$COMMAND" == "restore" ]]; then
                    BACKUP_FILE="$1"
                else
                    log_error "Unknown option: $1"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
}

# Main function
main() {
    parse_args "$@"
    check_prerequisites
    
    case "$COMMAND" in
        setup)
            setup_environment
            ;;
        start)
            start_app
            ;;
        stop)
            stop_app
            ;;
        restart)
            restart_app
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        shell)
            open_shell
            ;;
        update)
            update_app
            ;;
        backup)
            backup_data
            ;;
        restore)
            restore_data "$BACKUP_FILE"
            ;;
        clean)
            clean_resources
            ;;
        health)
            run_health_check
            ;;
        monitor)
            monitor_resources
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"