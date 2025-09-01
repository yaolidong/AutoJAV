# AV Metadata Scraper - User Guide

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [File Organization](#file-organization)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## Overview

AV Metadata Scraper is an automated system that helps organize your Japanese AV video collection by:

- **Scanning** video files in specified directories
- **Scraping** metadata from multiple sources (JavDB, JavLibrary)
- **Organizing** files into a structured directory layout
- **Downloading** cover images, posters, and screenshots
- **Saving** metadata in JSON format for future reference

### Key Features

- 🔍 **Multi-source scraping**: Supports JavDB, JavLibrary, and extensible for more sources
- 🤖 **Automated login**: Handles website login with captcha support
- 📁 **Smart organization**: Organizes files by actress/code structure
- 🖼️ **Image download**: Downloads covers, posters, and screenshots
- 🐳 **Docker ready**: Easy deployment with Docker containers
- ⚡ **Concurrent processing**: Processes multiple files simultaneously
- 🔄 **Retry mechanism**: Robust error handling and retry logic
- 📊 **Progress tracking**: Saves progress and can resume interrupted operations

## Installation

### Option 1: Docker (Recommended)

Docker provides the easiest and most reliable installation method.

#### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- At least 2GB RAM and 10GB free disk space

#### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd av-metadata-scraper
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   cp config/config.yaml.example config/config.yaml
   ```

3. **Configure directories** (edit `.env`):
   ```bash
   SOURCE_DIR=/path/to/your/videos
   TARGET_DIR=/path/to/organized/output
   ```

4. **Start the application**:
   ```bash
   docker-compose up -d
   ```

### Option 2: Manual Installation

For advanced users who prefer manual installation.

#### Prerequisites

- Python 3.9 or higher
- Chrome or Chromium browser
- ChromeDriver (matching your Chrome version)

#### Installation Steps

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd av-metadata-scraper
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Chrome and ChromeDriver**:
   - Download Chrome from https://www.google.com/chrome/
   - Download ChromeDriver from https://chromedriver.chromium.org/
   - Ensure ChromeDriver is in your PATH

4. **Configure the application**:
   ```bash
   cp config/config.yaml.example config/config.yaml
   # Edit config/config.yaml with your settings
   ```

5. **Run the application**:
   ```bash
   python main.py
   ```

## Configuration

### Basic Configuration

The main configuration file is `config/config.yaml`. Here's a minimal setup:

```yaml
# Directory Settings
directories:
  source: "/path/to/your/videos"
  target: "/path/to/organized/files"

# Scraper Settings
scraping:
  priority: ["javdb", "javlibrary"]
  max_concurrent_files: 2
  retry_attempts: 3

# File Organization
organization:
  naming_pattern: "{actress}/{code}/{code}.{ext}"
  download_images: true
  save_metadata: true
```

### Advanced Configuration

#### JavDB Login (Recommended)

For better results, configure JavDB login:

```yaml
credentials:
  javdb:
    username: "your_username"
    password: "your_password"
```

#### Custom File Naming

Customize how files are organized using placeholders:

```yaml
organization:
  # Available placeholders: {actress}, {code}, {title}, {studio}, {year}, {ext}
  naming_pattern: "{actress}/{code}/{code}.{ext}"
  
  # Alternative patterns:
  # naming_pattern: "{studio}/{actress}/{code} - {title}.{ext}"
  # naming_pattern: "{year}/{actress}/{code}.{ext}"
```

#### Performance Tuning

Adjust concurrent processing based on your system:

```yaml
scraping:
  max_concurrent_files: 3      # Number of files processed simultaneously
  max_concurrent_requests: 2   # Concurrent web requests per scraper
  max_concurrent_downloads: 4  # Concurrent image downloads
  timeout: 30                  # Request timeout in seconds
```

#### Network Configuration

Configure proxy if needed:

```yaml
network:
  proxy_url: "http://proxy.example.com:8080"
  # Or with authentication:
  # proxy_url: "http://user:pass@proxy.example.com:8080"
```

### Environment Variables (Docker)

When using Docker, you can override settings with environment variables:

```bash
# In .env file
SOURCE_DIR=/path/to/videos
TARGET_DIR=/path/to/organized
JAVDB_USERNAME=your_username
JAVDB_PASSWORD=your_password
MAX_CONCURRENT_FILES=2
LOG_LEVEL=INFO
```

## Usage

### Command Line Interface

The application provides a comprehensive CLI with multiple commands:

#### Basic Commands

```bash
# Process all files with default configuration
av-scraper process

# Scan directory without processing
av-scraper scan --source /path/to/videos

# Check application status
av-scraper status

# Stop running processes
av-scraper stop
```

#### Configuration Commands

```bash
# Interactive configuration wizard
av-scraper config wizard

# Validate configuration
av-scraper config validate

# Show current configuration
av-scraper config show
```

#### Testing and Debugging

```bash
# Test scraper connectivity
av-scraper test scrapers

# Test configuration
av-scraper test config

# Health check
av-scraper health --verbose

# View statistics
av-scraper stats
```

#### Advanced Usage

```bash
# Process with custom configuration
av-scraper process --config /path/to/custom.yaml

# Dry run (no actual file operations)
av-scraper process --dry-run

# Process specific files
av-scraper process --files "file1.mp4,file2.mkv"

# Resume interrupted processing
av-scraper process --resume

# JSON output for scripting
av-scraper status --json
```

### Docker Usage

#### Basic Docker Commands

```bash
# Start application
docker-compose up -d

# View logs
docker-compose logs -f av-scraper

# Stop application
docker-compose down

# Restart application
docker-compose restart av-scraper
```

#### Docker Management Scripts

The project includes management scripts for easier Docker operations:

```bash
# Setup and start
./docker/manage.sh setup
./docker/manage.sh start

# Monitor and debug
./docker/manage.sh logs
./docker/manage.sh health
./docker/manage.sh shell

# Maintenance
./docker/manage.sh backup
./docker/manage.sh update
./docker/manage.sh clean
```

### Web Interface (Future Feature)

A web interface is planned for future releases to provide:
- Real-time processing status
- Configuration management
- File browser and preview
- Statistics and reports

## File Organization

### Directory Structure

The application organizes files into a structured hierarchy:

```
target_directory/
├── Actress Name 1/
│   ├── ABC-001/
│   │   ├── ABC-001.mp4
│   │   ├── ABC-001.json          # Metadata
│   │   ├── ABC-001-cover.jpg     # Cover image
│   │   ├── ABC-001-poster.jpg    # Poster image
│   │   └── ABC-001-thumb.jpg     # Thumbnail
│   └── ABC-002/
│       └── ...
├── Actress Name 2/
│   └── ...
└── _unorganized/                 # Files that couldn't be processed
    ├── unknown-file1.mp4
    └── processing-failed.mkv
```

### Naming Patterns

You can customize the directory structure using naming patterns:

#### Default Pattern
```yaml
naming_pattern: "{actress}/{code}/{code}.{ext}"
```
Result: `Yui Hatano/SSIS-001/SSIS-001.mp4`

#### Studio-based Pattern
```yaml
naming_pattern: "{studio}/{actress}/{code} - {title}.{ext}"
```
Result: `S1 NO.1 STYLE/Yui Hatano/SSIS-001 - Title Here.mp4`

#### Year-based Pattern
```yaml
naming_pattern: "{year}/{actress}/{code}.{ext}"
```
Result: `2023/Yui Hatano/SSIS-001.mp4`

### Metadata Files

Each organized video includes a JSON metadata file:

```json
{
  "code": "SSIS-001",
  "title": "Video Title",
  "title_en": "English Title",
  "actresses": ["Yui Hatano"],
  "release_date": "2023-01-15",
  "duration": 120,
  "studio": "S1 NO.1 STYLE",
  "genres": ["Drama", "Solowork"],
  "cover_url": "https://example.com/cover.jpg",
  "description": "Video description...",
  "rating": 4.5,
  "source_url": "https://javdb.com/v/...",
  "scraped_at": "2023-12-01T10:30:00Z"
}
```

### Image Files

The application downloads and saves various image types:

- **Cover**: Main cover image (`{code}-cover.jpg`)
- **Poster**: Poster image (`{code}-poster.jpg`)
- **Thumbnail**: Small thumbnail (`{code}-thumb.jpg`)
- **Screenshots**: Sample screenshots (`{code}-screenshot-1.jpg`, etc.)

## Troubleshooting

### Common Issues

#### 1. Permission Denied Errors

**Problem**: Cannot access source or target directories.

**Solution**:
```bash
# Fix directory permissions
sudo chown -R $USER:$USER /path/to/directories
chmod -R 755 /path/to/directories

# For Docker, set PUID/PGID in .env
echo "PUID=$(id -u)" >> .env
echo "PGID=$(id -g)" >> .env
```

#### 2. Chrome/ChromeDriver Issues

**Problem**: Browser automation fails.

**Solutions**:
```bash
# Update Chrome and ChromeDriver
# For Docker:
docker-compose build --no-cache

# For manual installation:
# Download latest Chrome and ChromeDriver
# Ensure versions match
```

#### 3. Network/Proxy Issues

**Problem**: Cannot connect to scraping websites.

**Solutions**:
```bash
# Test connectivity
curl -I https://javdb.com

# Configure proxy in config.yaml:
network:
  proxy_url: "http://proxy:8080"

# Or in .env for Docker:
HTTP_PROXY=http://proxy:8080
HTTPS_PROXY=http://proxy:8080
```

#### 4. Memory Issues

**Problem**: Application crashes due to insufficient memory.

**Solutions**:
```bash
# Reduce concurrent processing
# In config.yaml:
scraping:
  max_concurrent_files: 1
  max_concurrent_requests: 1

# For Docker, increase memory limit in .env:
MEMORY_LIMIT=4G
```

#### 5. Login Issues

**Problem**: Cannot login to JavDB.

**Solutions**:
1. Verify credentials in configuration
2. Check if account is not banned
3. Try manual login in browser first
4. Enable debug logging to see detailed errors

### Debug Mode

Enable debug mode for detailed logging:

```bash
# For Docker (.env file):
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# For manual installation (config.yaml):
logging:
  level: "DEBUG"
```

### Log Analysis

Check logs for errors and debugging information:

```bash
# Docker logs
docker-compose logs -f av-scraper

# Manual installation logs
tail -f logs/av-scraper.log

# Filter for errors
grep ERROR logs/av-scraper.log
```

## FAQ

### General Questions

**Q: Is this legal to use?**
A: This tool is for personal use to organize your legally owned content. Always respect copyright laws and website terms of service.

**Q: Does this work with other types of videos?**
A: Currently optimized for Japanese AV content, but the architecture is extensible for other content types.

**Q: Can I run this on a NAS or server?**
A: Yes, the Docker version works well on NAS systems like Synology, QNAP, or dedicated servers.

### Technical Questions

**Q: How much system resources does it need?**
A: Minimum 2GB RAM, recommended 4GB+. CPU usage depends on concurrent processing settings.

**Q: Can I process files while the system is running?**
A: Yes, you can add new files to the source directory and they will be processed in the next scan.

**Q: What happens if processing is interrupted?**
A: The system saves progress and can resume from where it left off using `--resume` flag.

**Q: Can I customize the scrapers?**
A: Yes, the scraper system is modular. See the developer guide for adding new scrapers.

### Configuration Questions

**Q: Do I need JavDB login credentials?**
A: Not required, but highly recommended for better results and access to more content.

**Q: Can I change the file naming pattern after processing?**
A: Yes, but you'll need to reorganize existing files. Consider using the `--dry-run` option first.

**Q: How do I handle duplicate files?**
A: The system includes duplicate detection. Configure the behavior in the advanced settings.

### Troubleshooting Questions

**Q: Why are some files not being processed?**
A: Check logs for errors. Common causes: unsupported format, unrecognizable filename, network issues.

**Q: The browser keeps crashing, what should I do?**
A: Try reducing concurrent processing, increase memory limits, or update Chrome/ChromeDriver.

**Q: How do I report bugs or request features?**
A: Create an issue in the project repository with detailed information and logs.

---

For more detailed technical information, see:
- [API Documentation](API_DOCUMENTATION.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Docker Deployment Guide](../DOCKER_DEPLOYMENT.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)