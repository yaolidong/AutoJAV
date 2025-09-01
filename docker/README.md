# Docker Configuration for AV Metadata Scraper

This directory contains Docker-related files and utilities for the AV Metadata Scraper project.

## Files Overview

- `Dockerfile` - Main Docker image definition
- `docker-compose.yml` - Standard Docker Compose configuration
- `docker-compose.dev.yml` - Development environment overrides
- `docker-compose.prod.yml` - Production environment overrides
- `startup.sh` - Container initialization script
- `healthcheck.py` - Container health check script
- `build.sh` - Docker build utility script
- `manage.sh` - Docker management utility script
- `README.md` - This documentation file

## Quick Start

### 1. Initial Setup

```bash
# Make scripts executable
chmod +x docker/*.sh

# Run initial setup
./docker/manage.sh setup
```

### 2. Configuration

Edit the generated `.env` file with your settings:

```bash
# Required directories
SOURCE_DIR=/path/to/your/videos
TARGET_DIR=/path/to/organized/output

# Optional JavDB credentials
JAVDB_USERNAME=your_username
JAVDB_PASSWORD=your_password
```

### 3. Start Application

```bash
# Development mode
./docker/manage.sh start --dev

# Production mode
./docker/manage.sh start --prod -d
```

## Build Options

### Standard Build

```bash
# Build with default settings
./docker/build.sh build

# Build with specific tag
./docker/build.sh build -t v1.0.0

# Build without cache
./docker/build.sh build --no-cache
```

### Development Build

```bash
# Build development image
./docker/build.sh build-dev

# Start development environment
./docker/manage.sh start --dev
```

### Production Build

```bash
# Build production image
./docker/build.sh build-prod

# Start production environment
./docker/manage.sh start --prod -d
```

## Management Commands

### Application Control

```bash
# Start application
./docker/manage.sh start [-d] [--dev|--prod]

# Stop application
./docker/manage.sh stop

# Restart application
./docker/manage.sh restart

# Check status
./docker/manage.sh status
```

### Monitoring and Debugging

```bash
# View logs
./docker/manage.sh logs [-f]

# Open shell in container
./docker/manage.sh shell

# Run health check
./docker/manage.sh health

# Monitor resource usage
./docker/manage.sh monitor
```

### Maintenance

```bash
# Update application
./docker/manage.sh update

# Backup data
./docker/manage.sh backup

# Restore from backup
./docker/manage.sh restore backup-20231201-120000.tar.gz

# Clean up resources
./docker/manage.sh clean
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SOURCE_DIR` | Directory containing video files | `/path/to/videos` |
| `TARGET_DIR` | Directory for organized output | `/path/to/organized` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_DIR` | `./config` | Configuration directory |
| `LOGS_DIR` | `./logs` | Logs directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `JAVDB_USERNAME` | - | JavDB username |
| `JAVDB_PASSWORD` | - | JavDB password |
| `MAX_CONCURRENT_FILES` | `2` | Concurrent file processing |
| `MEMORY_LIMIT` | `2G` | Container memory limit |
| `CPU_LIMIT` | `2.0` | Container CPU limit |
| `TZ` | `UTC` | Container timezone |
| `SAFE_MODE` | `true` | Copy instead of move files |
| `DEBUG_MODE` | `false` | Enable debug logging |

## Volume Mounts

### Standard Mounts

```yaml
volumes:
  - ${SOURCE_DIR}:/app/source:ro      # Source videos (read-only)
  - ${TARGET_DIR}:/app/target         # Organized output
  - ${CONFIG_DIR}:/app/config         # Configuration files
  - ${LOGS_DIR}:/app/logs             # Log files
  - chrome-data:/app/.chrome-data     # Chrome user data
```

### Development Mounts

```yaml
volumes:
  - ./src:/app/src:rw                 # Source code (live editing)
  - ./tests:/app/tests:rw             # Test files
  - ./examples:/app/examples:rw       # Example files
```

## Network Configuration

### Default Network

The application uses a custom bridge network `av-scraper-network` with subnet `172.20.0.0/16`.

### Proxy Support

Configure proxy through environment variables:

```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

## Security Features

### Container Security

- Runs as non-root user (`appuser`)
- Uses read-only filesystem in production
- Implements security options (`no-new-privileges`)
- Resource limits prevent resource exhaustion

### Data Security

- Sensitive credentials via environment variables
- Configuration files mounted from host
- Logs stored in separate volume

## Health Checks

### Automatic Health Checks

The container includes automatic health checks that verify:

- Python environment
- Chrome/ChromeDriver installation
- Directory accessibility
- Configuration validity
- Network connectivity
- Application modules

### Manual Health Check

```bash
# Run health check
./docker/manage.sh health

# Or directly
docker exec av-metadata-scraper python /app/docker/healthcheck.py
```

## Troubleshooting

### Common Issues

#### Permission Errors

```bash
# Fix directory permissions
sudo chown -R $USER:$USER source/ target/ config/ logs/

# Or use PUID/PGID
echo "PUID=$(id -u)" >> .env
echo "PGID=$(id -g)" >> .env
```

#### Chrome Issues

```bash
# Rebuild with latest Chrome
./docker/build.sh build --no-cache

# Check Chrome in container
docker exec av-metadata-scraper google-chrome --version
```

#### Memory Issues

```bash
# Increase memory limit
echo "MEMORY_LIMIT=4G" >> .env

# Reduce concurrent processing
echo "MAX_CONCURRENT_FILES=1" >> .env
```

#### Network Issues

```bash
# Test connectivity
docker exec av-metadata-scraper curl -I https://javdb.com

# Configure proxy
echo "HTTP_PROXY=http://proxy:8080" >> .env
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
echo "DEBUG_MODE=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env
./docker/manage.sh restart
```

### Log Analysis

```bash
# View recent errors
./docker/manage.sh logs | grep ERROR

# Export logs
docker logs av-metadata-scraper > scraper-logs.txt
```

## Performance Tuning

### Resource Optimization

```bash
# Adjust for your system
echo "MEMORY_LIMIT=4G" >> .env
echo "CPU_LIMIT=4.0" >> .env
echo "MAX_CONCURRENT_FILES=4" >> .env
```

### Storage Optimization

- Use SSD/NVMe storage for target directory
- Enable log compression (automatic in production)
- Regular cleanup of old Chrome data

### Network Optimization

- Use local DNS cache
- Configure appropriate proxy settings
- Optimize TCP settings on host

## Development

### Development Environment

```bash
# Start development environment
./docker/manage.sh start --dev

# Features:
# - Live code reloading
# - Debug logging
# - Chrome DevTools access (port 9222)
# - Development tools included
```

### Testing

```bash
# Test built image
./docker/build.sh test

# Run specific tests
docker exec av-metadata-scraper python -m pytest tests/

# Security scan
./docker/build.sh scan
```

### Building for Multiple Platforms

```bash
# Build for multiple architectures
./docker/build.sh build --platform linux/amd64,linux/arm64
```

## Production Deployment

### Production Configuration

```bash
# Use production compose file
./docker/manage.sh start --prod -d

# Features:
# - Optimized resource limits
# - Enhanced security
# - Compressed logging
# - Read-only filesystem
```

### Monitoring

```bash
# Monitor resources
./docker/manage.sh monitor

# Check health
./docker/manage.sh health

# View logs
./docker/manage.sh logs -f
```

### Backup and Recovery

```bash
# Regular backups
./docker/manage.sh backup

# Restore if needed
./docker/manage.sh restore backup-file.tar.gz
```

For more detailed information, see the main [DOCKER_DEPLOYMENT.md](../DOCKER_DEPLOYMENT.md) file.