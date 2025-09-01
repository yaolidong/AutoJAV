#!/bin/bash
set -e

# Docker Build Script for AV Metadata Scraper
# This script provides various build options and utilities

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="av-metadata-scraper"
DEFAULT_TAG="latest"

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
Docker Build Script for AV Metadata Scraper

Usage: $0 [OPTIONS] [COMMAND]

Commands:
    build           Build the Docker image (default)
    build-dev       Build development image
    build-prod      Build production image
    push            Push image to registry
    clean           Clean up build artifacts
    test            Test the built image
    scan            Scan image for vulnerabilities
    help            Show this help message

Options:
    -t, --tag TAG   Image tag (default: latest)
    -r, --registry  Registry URL for push
    --no-cache      Build without using cache
    --platform      Target platform (e.g., linux/amd64,linux/arm64)
    --quiet         Suppress build output
    --verbose       Verbose output

Examples:
    $0 build                    # Build with default settings
    $0 build -t v1.0.0         # Build with specific tag
    $0 build --no-cache        # Build without cache
    $0 build-prod -t v1.0.0    # Build production image
    $0 push -r registry.com    # Push to registry
    $0 test                    # Test the built image

EOF
}

# Parse command line arguments
parse_args() {
    COMMAND="build"
    TAG="$DEFAULT_TAG"
    REGISTRY=""
    NO_CACHE=""
    PLATFORM=""
    QUIET=""
    VERBOSE=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            build|build-dev|build-prod|push|clean|test|scan|help)
                COMMAND="$1"
                shift
                ;;
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            --no-cache)
                NO_CACHE="--no-cache"
                shift
                ;;
            --platform)
                PLATFORM="--platform $2"
                shift 2
                ;;
            --quiet)
                QUIET="--quiet"
                shift
                ;;
            --verbose)
                VERBOSE="--progress=plain"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_DIR/Dockerfile" ]]; then
        log_error "Dockerfile not found in project directory"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Build image
build_image() {
    local dockerfile="$1"
    local build_args="$2"
    
    log_info "Building Docker image: $IMAGE_NAME:$TAG"
    log_info "Using Dockerfile: $dockerfile"
    
    # Prepare build command
    local build_cmd="docker build"
    build_cmd="$build_cmd -t $IMAGE_NAME:$TAG"
    build_cmd="$build_cmd -f $dockerfile"
    
    # Add optional arguments
    [[ -n "$NO_CACHE" ]] && build_cmd="$build_cmd $NO_CACHE"
    [[ -n "$PLATFORM" ]] && build_cmd="$build_cmd $PLATFORM"
    [[ -n "$QUIET" ]] && build_cmd="$build_cmd $QUIET"
    [[ -n "$VERBOSE" ]] && build_cmd="$build_cmd $VERBOSE"
    [[ -n "$build_args" ]] && build_cmd="$build_cmd $build_args"
    
    # Add context
    build_cmd="$build_cmd $PROJECT_DIR"
    
    log_info "Build command: $build_cmd"
    
    # Execute build
    if eval "$build_cmd"; then
        log_success "Image built successfully: $IMAGE_NAME:$TAG"
        
        # Show image info
        docker images "$IMAGE_NAME:$TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    else
        log_error "Build failed"
        exit 1
    fi
}

# Build development image
build_dev() {
    log_info "Building development image..."
    build_image "$PROJECT_DIR/Dockerfile" "--target builder"
}

# Build production image
build_prod() {
    log_info "Building production image..."
    build_image "$PROJECT_DIR/Dockerfile" ""
}

# Push image to registry
push_image() {
    if [[ -z "$REGISTRY" ]]; then
        log_error "Registry URL not specified. Use -r or --registry option."
        exit 1
    fi
    
    local full_image="$REGISTRY/$IMAGE_NAME:$TAG"
    
    log_info "Tagging image for registry: $full_image"
    docker tag "$IMAGE_NAME:$TAG" "$full_image"
    
    log_info "Pushing image to registry: $full_image"
    if docker push "$full_image"; then
        log_success "Image pushed successfully: $full_image"
    else
        log_error "Push failed"
        exit 1
    fi
}

# Test the built image
test_image() {
    log_info "Testing Docker image: $IMAGE_NAME:$TAG"
    
    # Check if image exists
    if ! docker images "$IMAGE_NAME:$TAG" --format "{{.Repository}}:{{.Tag}}" | grep -q "$IMAGE_NAME:$TAG"; then
        log_error "Image $IMAGE_NAME:$TAG not found. Build it first."
        exit 1
    fi
    
    # Run health check
    log_info "Running health check..."
    if docker run --rm "$IMAGE_NAME:$TAG" python /app/docker/healthcheck.py; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi
    
    # Test basic functionality
    log_info "Testing basic functionality..."
    if docker run --rm "$IMAGE_NAME:$TAG" python -c "import sys; sys.path.insert(0, '/app/src'); from src.utils.logging_config import setup_logging; setup_logging(); print('Basic test passed')"; then
        log_success "Basic functionality test passed"
    else
        log_error "Basic functionality test failed"
        exit 1
    fi
    
    log_success "All tests passed"
}

# Scan image for vulnerabilities
scan_image() {
    log_info "Scanning image for vulnerabilities: $IMAGE_NAME:$TAG"
    
    # Check if trivy is available
    if command -v trivy &> /dev/null; then
        log_info "Using Trivy for vulnerability scanning..."
        trivy image "$IMAGE_NAME:$TAG"
    elif command -v docker &> /dev/null && docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest --version &> /dev/null; then
        log_info "Using Trivy Docker image for vulnerability scanning..."
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy:latest image "$IMAGE_NAME:$TAG"
    else
        log_warning "Trivy not available. Skipping vulnerability scan."
        log_info "Install Trivy for security scanning: https://aquasecurity.github.io/trivy/"
    fi
}

# Clean up build artifacts
clean_build() {
    log_info "Cleaning up build artifacts..."
    
    # Remove dangling images
    if docker images -f "dangling=true" -q | grep -q .; then
        log_info "Removing dangling images..."
        docker rmi $(docker images -f "dangling=true" -q)
    fi
    
    # Remove build cache
    log_info "Pruning build cache..."
    docker builder prune -f
    
    # Remove unused volumes
    log_info "Pruning unused volumes..."
    docker volume prune -f
    
    log_success "Cleanup completed"
}

# Main function
main() {
    parse_args "$@"
    
    case "$COMMAND" in
        build)
            check_prerequisites
            build_image "$PROJECT_DIR/Dockerfile" ""
            ;;
        build-dev)
            check_prerequisites
            build_dev
            ;;
        build-prod)
            check_prerequisites
            build_prod
            ;;
        push)
            push_image
            ;;
        test)
            test_image
            ;;
        scan)
            scan_image
            ;;
        clean)
            clean_build
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