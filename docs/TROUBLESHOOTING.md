# AV Metadata Scraper - Troubleshooting Guide

## Table of Contents

- [Common Issues](#common-issues)
- [Installation Problems](#installation-problems)
- [Configuration Issues](#configuration-issues)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Docker-Specific Issues](#docker-specific-issues)
- [Network and Proxy Issues](#network-and-proxy-issues)
- [Browser and WebDriver Issues](#browser-and-webdriver-issues)
- [File System Issues](#file-system-issues)
- [Debugging Tools](#debugging-tools)
- [Getting Help](#getting-help)

## Common Issues

### 1. Application Won't Start

**Symptoms:**
- Application exits immediately
- "Configuration error" messages
- Import errors

**Diagnosis:**
```bash
# Check configuration
av-scraper config validate

# Test with debug logging
av-scraper --log-level DEBUG process --dry-run

# Check Python environment
python --version
pip list | grep -E "(selenium|beautifulsoup|requests)"
```

**Solutions:**
1. **Invalid Configuration:**
   ```bash
   # Copy and edit example configuration
   cp config/config.yaml.example config/config.yaml
   # Edit config.yaml with correct paths and settings
   ```

2. **Missing Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Python Version Issues:**
   ```bash
   # Ensure Python 3.9+
   python --version
   # Use virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate  # Windows
   ```

### 2. No Files Being Processed

**Symptoms:**
- Scan completes but finds no files
- "No video files found" message

**Diagnosis:**
```bash
# Check directory contents
ls -la /path/to/source/directory

# Test file scanner
av-scraper scan --source /path/to/source --verbose

# Check supported extensions
av-scraper config show | grep extensions
```

**Solutions:**
1. **Incorrect Source Directory:**
   ```yaml
   # In config.yaml
   directories:
     source: "/correct/path/to/videos"
   ```

2. **Unsupported File Extensions:**
   ```yaml
   # Add more extensions in config.yaml
   supported_extensions:
     - ".mp4"
     - ".mkv"
     - ".avi"
     - ".your_extension"
   ```

3. **Permission Issues:**
   ```bash
   # Fix permissions
   chmod -R 755 /path/to/source
   ```

### 3. Metadata Not Found

**Symptoms:**
- Files are scanned but no metadata is retrieved
- "No metadata found" for all files

**Diagnosis:**
```bash
# Test scrapers
av-scraper test scrapers

# Check network connectivity
curl -I https://javdb.com
curl -I https://www.javlibrary.com

# Test with specific file
av-scraper process --files "specific_file.mp4" --verbose
```

**Solutions:**
1. **Network Connectivity:**
   ```bash
   # Test internet connection
   ping google.com
   
   # Configure proxy if needed
   # In config.yaml:
   network:
     proxy_url: "http://proxy:8080"
   ```

2. **Scraper Issues:**
   ```bash
   # Try different scraper priority
   # In config.yaml:
   scraping:
     priority: ["javlibrary", "javdb"]
   ```

3. **Code Detection Issues:**
   ```bash
   # Check if codes are detected from filenames
   av-scraper scan --verbose
   
   # Rename files to include proper codes
   # Example: "SSIS-001.mp4" instead of "video1.mp4"
   ```

### 4. Login Failures

**Symptoms:**
- "Login failed" messages
- JavDB scraper not working
- Captcha-related errors

**Diagnosis:**
```bash
# Test login credentials
av-scraper test login

# Check browser automation
av-scraper test browser

# Enable debug logging
av-scraper --log-level DEBUG process --dry-run
```

**Solutions:**
1. **Incorrect Credentials:**
   ```yaml
   # Verify credentials in config.yaml
   credentials:
     javdb:
       username: "correct_username"
       password: "correct_password"
   ```

2. **Account Issues:**
   - Verify account is not banned
   - Try manual login in browser first
   - Check if 2FA is enabled (not supported)

3. **Captcha Problems:**
   ```yaml
   # Try headless mode disabled for debugging
   browser:
     headless: false
   ```

## Installation Problems

### Python Environment Issues

**Problem:** Import errors, module not found

**Solutions:**
```bash
# Create clean virtual environment
python -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import selenium, bs4, requests; print('All modules imported successfully')"
```

### Chrome/ChromeDriver Issues

**Problem:** WebDriver errors, Chrome not found

**Solutions:**

**Linux:**
```bash
# Install Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google.list
sudo apt-get update
sudo apt-get install google-chrome-stable

# Install ChromeDriver
CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f3 | cut -d '.' -f1)
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}/chromedriver_linux64.zip"
unzip /tmp/chromedriver.zip -d /tmp/
sudo mv /tmp/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

**macOS:**
```bash
# Install Chrome
brew install --cask google-chrome

# Install ChromeDriver
brew install chromedriver
```

**Windows:**
1. Download Chrome from https://www.google.com/chrome/
2. Download ChromeDriver from https://chromedriver.chromium.org/
3. Add ChromeDriver to PATH

### Docker Installation Issues

**Problem:** Docker-related installation errors

**Solutions:**
```bash
# Install Docker (Linux)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version
docker compose version

# Test Docker
docker run hello-world
```

## Configuration Issues

### Invalid YAML Syntax

**Problem:** Configuration file parsing errors

**Solutions:**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Use online YAML validator
# Copy config content to https://yamlchecker.com/

# Common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing quotes around special characters
# - Incorrect list format
```

### Path Configuration Issues

**Problem:** Directory not found, permission denied

**Solutions:**
```bash
# Use absolute paths
# In config.yaml:
directories:
  source: "/home/user/videos"  # Not "~/videos"
  target: "/home/user/organized"

# Create directories if they don't exist
mkdir -p /path/to/source /path/to/target

# Fix permissions
sudo chown -R $USER:$USER /path/to/directories
chmod -R 755 /path/to/directories
```

### Environment Variable Issues

**Problem:** Docker environment variables not working

**Solutions:**
```bash
# Check .env file syntax
cat .env

# Ensure no spaces around = sign
SOURCE_DIR=/path/to/videos  # Correct
# SOURCE_DIR = /path/to/videos  # Incorrect

# Restart Docker after .env changes
docker-compose down
docker-compose up -d
```

## Runtime Errors

### Memory Issues

**Symptoms:**
- Application crashes with "Out of memory"
- System becomes unresponsive
- Docker container killed

**Solutions:**
```bash
# Reduce concurrent processing
# In config.yaml:
scraping:
  max_concurrent_files: 1
  max_concurrent_requests: 1
  max_concurrent_downloads: 2

# For Docker, increase memory limit
# In .env:
MEMORY_LIMIT=4G

# Monitor memory usage
docker stats av-metadata-scraper
```

### Disk Space Issues

**Symptoms:**
- "No space left on device" errors
- File operations fail

**Solutions:**
```bash
# Check disk space
df -h

# Clean up Docker
docker system prune -a

# Clean up logs
find logs/ -name "*.log" -mtime +7 -delete

# Move large files to external storage
```

### Network Timeout Issues

**Symptoms:**
- Frequent timeout errors
- Slow scraping performance

**Solutions:**
```bash
# Increase timeouts
# In config.yaml:
scraping:
  timeout: 60  # Increase from 30

browser:
  timeout: 60

# Reduce concurrent requests
scraping:
  max_concurrent_requests: 1

# Check network connectivity
ping javdb.com
traceroute javdb.com
```

## Performance Issues

### Slow Processing

**Diagnosis:**
```bash
# Monitor resource usage
top
htop
docker stats

# Check logs for bottlenecks
tail -f logs/av-scraper.log | grep -E "(ERROR|WARNING|SLOW)"

# Profile with debug logging
av-scraper --log-level DEBUG process
```

**Solutions:**
1. **Optimize Concurrent Settings:**
   ```yaml
   scraping:
     max_concurrent_files: 4      # Increase if you have resources
     max_concurrent_requests: 3   # Balance with rate limiting
     max_concurrent_downloads: 6  # Images can be downloaded faster
   ```

2. **Hardware Optimization:**
   - Use SSD storage for target directory
   - Increase RAM allocation
   - Use faster internet connection

3. **Network Optimization:**
   ```yaml
   network:
     proxy_url: ""  # Remove proxy if not needed
   
   scraping:
     timeout: 30    # Reduce if network is fast
   ```

### High Resource Usage

**Solutions:**
```bash
# Limit Docker resources
# In docker-compose.yml:
services:
  av-scraper:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'

# Use nice/ionice for manual installation
nice -n 10 ionice -c 3 python main.py
```

## Docker-Specific Issues

### Container Won't Start

**Diagnosis:**
```bash
# Check container logs
docker-compose logs av-scraper

# Check container status
docker-compose ps

# Inspect container
docker inspect av-metadata-scraper
```

**Solutions:**
1. **Port Conflicts:**
   ```bash
   # Check port usage
   netstat -tulpn | grep :9222
   
   # Change port in docker-compose.yml
   ports:
     - "9223:9222"  # Use different host port
   ```

2. **Volume Mount Issues:**
   ```bash
   # Check volume permissions
   ls -la /host/path/to/volumes
   
   # Fix ownership
   sudo chown -R 1000:1000 /host/path/to/volumes
   ```

3. **Image Build Issues:**
   ```bash
   # Rebuild without cache
   docker-compose build --no-cache
   
   # Pull latest base images
   docker-compose pull
   ```

### Permission Issues in Container

**Problem:** Cannot access mounted volumes

**Solutions:**
```bash
# Set PUID/PGID in .env
echo "PUID=$(id -u)" >> .env
echo "PGID=$(id -g)" >> .env

# Restart container
docker-compose down
docker-compose up -d

# Alternative: Fix host permissions
sudo chown -R 1000:1000 source/ target/ config/ logs/
```

### Container Memory Issues

**Solutions:**
```bash
# Increase Docker memory limit
# In .env:
MEMORY_LIMIT=4G

# Or in docker-compose.yml:
services:
  av-scraper:
    mem_limit: 4g
    memswap_limit: 4g

# Monitor container memory
docker stats av-metadata-scraper
```

## Network and Proxy Issues

### Proxy Configuration

**Problem:** Cannot connect through corporate proxy

**Solutions:**
```bash
# Configure proxy in .env (Docker)
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080

# Or in config.yaml (manual installation)
network:
  proxy_url: "http://proxy.company.com:8080"

# With authentication
network:
  proxy_url: "http://username:password@proxy.company.com:8080"

# Test proxy connectivity
curl --proxy http://proxy:8080 -I https://javdb.com
```

### SSL/TLS Issues

**Problem:** SSL certificate errors

**Solutions:**
```bash
# Disable SSL verification (not recommended for production)
export PYTHONHTTPSVERIFY=0

# Or configure in code (for development)
# Add to config.yaml:
network:
  verify_ssl: false

# Update certificates
# Linux:
sudo apt-get update && sudo apt-get install ca-certificates

# macOS:
brew install ca-certificates
```

### DNS Issues

**Problem:** Cannot resolve domain names

**Solutions:**
```bash
# Test DNS resolution
nslookup javdb.com
dig javdb.com

# Configure DNS in Docker
# In docker-compose.yml:
services:
  av-scraper:
    dns:
      - 8.8.8.8
      - 8.8.4.4

# Or use host networking
network_mode: host
```

## Browser and WebDriver Issues

### Chrome Crashes

**Problem:** Chrome browser crashes frequently

**Solutions:**
```bash
# Add Chrome arguments in config
# For Docker, these are usually pre-configured
# For manual installation, modify browser initialization:

chrome_options = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-extensions',
    '--disable-plugins',
    '--disable-images',  # Faster loading
    '--disable-javascript',  # If not needed
]
```

### WebDriver Version Mismatch

**Problem:** ChromeDriver version doesn't match Chrome

**Solutions:**
```bash
# Check versions
google-chrome --version
chromedriver --version

# Update ChromeDriver
# Linux:
CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f3 | cut -d '.' -f1)
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}/chromedriver_linux64.zip"
unzip /tmp/chromedriver.zip -d /tmp/
sudo mv /tmp/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

# macOS:
brew upgrade chromedriver

# For Docker, rebuild image:
docker-compose build --no-cache
```

### Headless Mode Issues

**Problem:** Browser automation fails in headless mode

**Solutions:**
```yaml
# Temporarily disable headless mode for debugging
browser:
  headless: false

# Add display for headless environments (Linux servers)
# Install Xvfb:
sudo apt-get install xvfb

# Run with virtual display:
xvfb-run -a python main.py
```

## File System Issues

### Permission Denied

**Problem:** Cannot read source files or write to target directory

**Solutions:**
```bash
# Check current permissions
ls -la /path/to/directories

# Fix permissions
sudo chown -R $USER:$USER /path/to/source /path/to/target
chmod -R 755 /path/to/source
chmod -R 755 /path/to/target

# For Docker with bind mounts
sudo chown -R 1000:1000 /host/path/to/volumes

# Use PUID/PGID in Docker
echo "PUID=$(id -u)" >> .env
echo "PGID=$(id -g)" >> .env
```

### File Locking Issues

**Problem:** "File is being used by another process"

**Solutions:**
```bash
# Check what's using the file
lsof /path/to/file

# Kill processes using the file
fuser -k /path/to/file

# Enable safe mode to copy instead of move
# In config.yaml:
organization:
  safe_mode: true
```

### Disk Space Issues

**Problem:** Target disk full

**Solutions:**
```bash
# Check disk usage
df -h /path/to/target

# Clean up old files
find /path/to/target -name "*.tmp" -delete
find /path/to/target -name "*.partial" -delete

# Move to larger disk
# Update config.yaml with new target directory

# Enable compression for images
organization:
  compress_images: true
  image_quality: 85
```

## Debugging Tools

### Enable Debug Logging

```bash
# Command line
av-scraper --log-level DEBUG process

# Configuration file
logging:
  level: "DEBUG"

# Docker environment
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Log Analysis

```bash
# View recent logs
tail -f logs/av-scraper.log

# Filter for errors
grep ERROR logs/av-scraper.log

# Filter for specific component
grep "FileScanner" logs/av-scraper.log

# Count error types
grep ERROR logs/av-scraper.log | cut -d' ' -f4- | sort | uniq -c
```

### Performance Profiling

```bash
# Monitor system resources
htop
iotop
nethogs

# Docker resource monitoring
docker stats av-metadata-scraper

# Python profiling (for developers)
python -m cProfile -o profile.stats main.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"
```

### Network Debugging

```bash
# Monitor network traffic
sudo tcpdump -i any host javdb.com
sudo netstat -tulpn | grep python

# Test connectivity
curl -v https://javdb.com
wget --spider https://javlibrary.com

# Check proxy
curl --proxy http://proxy:8080 -v https://javdb.com
```

### Browser Debugging

```bash
# Enable Chrome DevTools (Docker)
# Access http://localhost:9222 in browser

# Save screenshots on errors
# In config.yaml:
browser:
  save_screenshots: true
  screenshot_dir: "debug/screenshots"

# Disable headless for visual debugging
browser:
  headless: false
```

## Getting Help

### Before Asking for Help

1. **Check logs** for error messages
2. **Try debug mode** for detailed information
3. **Test individual components** (scrapers, browser, etc.)
4. **Search existing issues** in the project repository
5. **Try with minimal configuration** to isolate the problem

### Information to Include

When reporting issues, include:

1. **System Information:**
   ```bash
   uname -a
   python --version
   docker --version
   google-chrome --version
   ```

2. **Configuration:**
   ```bash
   # Sanitized config (remove credentials)
   av-scraper config show --sanitized
   ```

3. **Error Logs:**
   ```bash
   # Recent error logs
   tail -100 logs/av-scraper.log | grep -A5 -B5 ERROR
   ```

4. **Steps to Reproduce:**
   - Exact commands used
   - Expected vs actual behavior
   - Sample files (if relevant)

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check latest documentation for updates
- **Docker Hub**: Check for image updates and known issues
- **Stack Overflow**: Search for similar problems

### Professional Support

For commercial use or complex deployments:
- Custom configuration assistance
- Performance optimization
- Integration support
- Training and documentation

---

**Remember**: Always sanitize logs and configuration files before sharing, removing any sensitive information like usernames, passwords, or personal file paths.