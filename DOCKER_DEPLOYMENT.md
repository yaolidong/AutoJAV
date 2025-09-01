# Docker Deployment Guide

This guide covers the deployment and management of the AV Metadata Scraper using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment Options](#deployment-options)
- [Management](#management)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Performance Tuning](#performance-tuning)

## Prerequisites

### System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **System Memory**: Minimum 2GB RAM, recommended 4GB+
- **Storage**: At least 10GB free space for images and data
- **CPU**: Multi-core processor recommended for concurrent processing

### Supported Platforms

- Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- macOS (Intel and Apple Silicon)
- Windows 10/11 with WSL2

### Installation

#### Linux (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

#### macOS
```bash
# Install Docker Desktop
brew install --cask docker

# Or download from https://www.docker.com/products/docker-desktop
```

#### Windows
Download and install Docker Desktop from https://www.docker.com/products/docker-desktop

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd av-metadata-scraper

# Copy environment configuration
cp .env.example .env

# Copy configuration template
cp config/config.yaml.template config/config.yaml
```

### 2. Configure Environment

Edit the `.env` file with your settings:

```bash
# Required: Set your directories
SOURCE_DIR=/path/to/your/videos
TARGET_DIR=/path/to/organized/output
CONFIG_DIR=./config
LOGS_DIR=./logs

# Optional: JavDB credentials for better results
JAVDB_USERNAME=your_username
JAVDB_PASSWORD=your_password

# Optional: Performance tuning
MAX_CONCURRENT_FILES=2
LOG_LEVEL=INFO
```

### 3. Start the Application

```bash
# Start in foreground (for testing)
docker compose up

# Start in background (for production)
docker compose up -d

# View logs
docker compose logs -f av-scraper
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_DIR` | `./source` | Directory containing video files |
| `TARGET_DIR` | `./organized` | Directory for organized output |
| `CONFIG_DIR` | `./config` | Configuration files directory |
| `LOGS_DIR` | `./logs` | Log files directory |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `JAVDB_USERNAME` | - | JavDB login username (optional) |
| `JAVDB_PASSWORD` | - | JavDB login password (optional) |
| `MAX_CONCURRENT_FILES` | `2` | Maximum files processed simultaneously |
| `MAX_CONCURRENT_REQUESTS` | `2` | Maximum concurrent web requests |
| `MAX_CONCURRENT_DOWNLOADS` | `2` | Maximum concurrent image downloads |
| `MEMORY_LIMIT` | `2G` | Container memory limit |
| `CPU_LIMIT` | `2.0` | Container CPU limit |
| `TZ` | `UTC` | Container timezone |
| `SAFE_MODE` | `true` | Copy files instead of moving |
| `DEBUG_MODE` | `false` | Enable debug logging |

### Configuration File

Edit `config/config.yaml` for detailed settings:

```yaml
# Directory Settings
directories:
  source: "/app/source"
  target: "/app/target"

# Scraper Settings
scraping:
  priority: ["javdb", "javlibrary"]
  max_concurrent_files: 2
  retry_attempts: 3
  timeout: 30

# File Organization
organization:
  naming_pattern: "{actress}/{code}/{code}.{ext}"
  download_images: true
  save_metadata: true

# Browser Settings
browser:
  headless: true
  timeout: 30

# Network Settings
network:
  proxy_url: ""

# Logging
logging:
  level: "INFO"
```

## Deployment Options

### Development Deployment

For development with live code reloading:

```bash
# Start development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Features:
# - Source code mounted for live editing
# - Debug logging enabled
# - Chrome DevTools port exposed (9222)
# - Safe mode enabled (copies files)
```

### Production Deployment

For production with optimized settings:

```bash
# Build production image
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start production environment
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Features:
# - Optimized resource limits
# - Enhanced security
# - Compressed logging
# - Read-only filesystem
```

### Custom Deployment

Create your own override file:

```yaml
# docker-compose.custom.yml
version: '3.8'
services:
  av-scraper:
    environment:
      - CUSTOM_SETTING=value
    volumes:
      - /custom/path:/app/custom
```

```bash
docker compose -f docker-compose.yml -f docker-compose.custom.yml up -d
```

## Management

### Container Management

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# View status
docker compose ps

# View logs
docker compose logs -f av-scraper

# Execute commands in container
docker compose exec av-scraper bash

# Update and restart
docker compose pull
docker compose up -d
```

### Data Management

```bash
# Backup configuration
tar -czf config-backup.tar.gz config/

# Backup organized files
tar -czf organized-backup.tar.gz organized/

# Clean up old logs
docker compose exec av-scraper find /app/logs -name "*.log" -mtime +7 -delete

# View disk usage
docker system df
docker compose exec av-scraper df -h
```

### Health Monitoring

```bash
# Check container health
docker compose ps
docker inspect av-metadata-scraper --format='{{.State.Health.Status}}'

# Monitor resource usage
docker stats av-metadata-scraper

# View detailed logs
docker compose logs --tail=100 av-scraper
```

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs for errors
docker compose logs av-scraper

# Common causes:
# - Invalid configuration
# - Permission issues
# - Port conflicts
# - Insufficient resources
```

#### Permission Denied Errors

```bash
# Fix directory permissions
sudo chown -R $USER:$USER source/ organized/ config/ logs/
chmod -R 755 source/ organized/ config/ logs/

# Or use PUID/PGID in .env
echo "PUID=$(id -u)" >> .env
echo "PGID=$(id -g)" >> .env
```

#### Chrome/ChromeDriver Issues

```bash
# Update Chrome and ChromeDriver
docker compose build --no-cache av-scraper

# Check Chrome version in container
docker compose exec av-scraper google-chrome --version
docker compose exec av-scraper chromedriver --version
```

#### Network/Proxy Issues

```bash
# Test network connectivity
docker compose exec av-scraper curl -I https://javdb.com

# Configure proxy in .env
echo "HTTP_PROXY=http://proxy:8080" >> .env
echo "HTTPS_PROXY=http://proxy:8080" >> .env
```

#### Memory Issues

```bash
# Increase memory limit
echo "MEMORY_LIMIT=4G" >> .env

# Monitor memory usage
docker stats av-metadata-scraper

# Reduce concurrent processing
echo "MAX_CONCURRENT_FILES=1" >> .env
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Enable debug in .env
echo "DEBUG_MODE=true" >> .env
echo "LOG_LEVEL=DEBUG" >> .env

# Restart with debug
docker compose restart av-scraper

# View debug logs
docker compose logs -f av-scraper | grep DEBUG
```

### Log Analysis

```bash
# View recent errors
docker compose logs av-scraper | grep ERROR

# Monitor real-time logs
docker compose logs -f --tail=50 av-scraper

# Export logs for analysis
docker compose logs av-scraper > scraper-logs.txt
```

## Security

### Security Best Practices

1. **Use Non-Root User**: Container runs as `appuser` by default
2. **Read-Only Filesystem**: Production mode uses read-only root filesystem
3. **No New Privileges**: Security option prevents privilege escalation
4. **Resource Limits**: Memory and CPU limits prevent resource exhaustion
5. **Network Isolation**: Uses custom bridge network

### Credential Management

```bash
# Use Docker secrets (Docker Swarm)
echo "your_password" | docker secret create javdb_password -

# Use environment files
echo "JAVDB_PASSWORD=your_password" > .env.secret
chmod 600 .env.secret
```

### Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp  # SSH
sudo ufw deny 9222/tcp  # Chrome DevTools (development only)
```

## Performance Tuning

### Resource Optimization

```bash
# Adjust based on your system
echo "MEMORY_LIMIT=4G" >> .env
echo "CPU_LIMIT=4.0" >> .env

# Optimize concurrent processing
echo "MAX_CONCURRENT_FILES=4" >> .env
echo "MAX_CONCURRENT_REQUESTS=6" >> .env
echo "MAX_CONCURRENT_DOWNLOADS=8" >> .env
```

### Storage Optimization

```bash
# Use faster storage for target directory
# Mount SSD/NVMe for better performance

# Enable compression for logs
# Already configured in production compose file

# Clean up old Chrome data
docker volume rm av-metadata-scraper_chrome-data
```

### Network Optimization

```bash
# Use local DNS cache
echo "nameserver 127.0.0.1" > /etc/resolv.conf

# Optimize TCP settings (Linux)
echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' >> /etc/sysctl.conf
sysctl -p
```

### Monitoring

```bash
# Set up monitoring with Prometheus/Grafana
# Add monitoring labels to compose file

# Use Docker health checks
# Already configured in compose file

# Monitor with cAdvisor
docker run -d \
  --name=cadvisor \
  --publish=8080:8080 \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  gcr.io/cadvisor/cadvisor:latest
```

## Maintenance

### Regular Maintenance Tasks

```bash
# Weekly: Clean up old logs
find logs/ -name "*.log" -mtime +7 -delete

# Monthly: Update base images
docker compose pull
docker compose up -d

# Quarterly: Clean up Docker system
docker system prune -a

# Backup configuration monthly
tar -czf "config-backup-$(date +%Y%m%d).tar.gz" config/
```

### Updates and Upgrades

```bash
# Update application
git pull origin main
docker compose build --no-cache
docker compose up -d

# Update base images
docker compose pull
docker compose up -d

# Rollback if needed
docker compose down
git checkout previous-version
docker compose up -d
```

For additional support, check the project documentation or create an issue in the repository.