# AV Metadata Scraper - Frequently Asked Questions (FAQ)

## Table of Contents

- [General Questions](#general-questions)
- [Installation and Setup](#installation-and-setup)
- [Configuration](#configuration)
- [Usage and Operation](#usage-and-operation)
- [Troubleshooting](#troubleshooting)
- [Performance and Optimization](#performance-and-optimization)
- [Docker-Specific Questions](#docker-specific-questions)
- [Legal and Ethical Questions](#legal-and-ethical-questions)
- [Advanced Usage](#advanced-usage)

## General Questions

### What is AV Metadata Scraper?

AV Metadata Scraper is an automated tool that helps organize Japanese AV (Adult Video) collections by:
- Scanning video files in specified directories
- Extracting metadata from multiple online sources (JavDB, JavLibrary)
- Organizing files into a structured directory layout
- Downloading cover images and posters
- Saving metadata in JSON format

### What makes this different from other media organizers?

- **Specialized for Japanese AV content** with proper code recognition
- **Multi-source scraping** with fallback mechanisms
- **Docker-ready** for easy deployment on servers and NAS systems
- **Concurrent processing** for faster organization
- **Robust error handling** with retry mechanisms
- **Extensible architecture** for adding new scrapers

### What video formats are supported?

By default, the following formats are supported:
- MP4, MKV, AVI, WMV, MOV
- FLV, WebM, M4V, TS, M2TS
- MPG, MPEG, 3GP, ASF, RM, RMVB

You can add more formats in the configuration file.

### Do I need programming knowledge to use this?

No programming knowledge is required for basic usage. The tool provides:
- Simple configuration files (YAML format)
- Docker deployment for easy setup
- Command-line interface with helpful commands
- Comprehensive documentation and examples

## Installation and Setup

### What are the system requirements?

**Minimum Requirements:**
- 2GB RAM
- 10GB free disk space
- Internet connection
- Docker 20.10+ (for Docker installation)
- Python 3.9+ (for manual installation)

**Recommended:**
- 4GB+ RAM for better performance
- SSD storage for faster file operations
- Multi-core CPU for concurrent processing

### Should I use Docker or manual installation?

**Use Docker if:**
- You want the easiest setup experience
- You're running on a server or NAS
- You want isolated environment
- You don't want to manage Python dependencies

**Use manual installation if:**
- You want to modify the source code
- You're developing or debugging
- You have specific Python environment requirements
- Docker is not available on your system

### How do I install Chrome/ChromeDriver?

**Docker:** Chrome and ChromeDriver are automatically included in the Docker image.

**Manual Installation:**

*Linux (Ubuntu/Debian):*
```bash
# Install Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google.list
sudo apt-get update && sudo apt-get install google-chrome-stable

# Install ChromeDriver
CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f3 | cut -d '.' -f1)
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}/chromedriver_linux64.zip"
unzip /tmp/chromedriver.zip -d /tmp/
sudo mv /tmp/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

*macOS:*
```bash
brew install --cask google-chrome
brew install chromedriver
```

*Windows:*
1. Download Chrome from https://www.google.com/chrome/
2. Download ChromeDriver from https://chromedriver.chromium.org/
3. Add ChromeDriver to your PATH

## Configuration

### Do I need JavDB login credentials?

JavDB login is **optional but highly recommended** because:
- **Better results:** Access to more detailed metadata
- **Higher success rate:** Logged-in users have better access
- **More images:** Access to additional screenshots and images
- **Reduced rate limiting:** Better request handling

Without login, the tool will still work but with limited functionality.

### How do I configure file naming patterns?

You can customize how files are organized using placeholders in the `naming_pattern` setting:

**Available placeholders:**
- `{actress}` - Primary actress name
- `{code}` - Video identification code
- `{title}` - Movie title
- `{studio}` - Production studio
- `{year}` - Release year
- `{ext}` - File extension

**Examples:**
```yaml
# By actress and code (default)
naming_pattern: "{actress}/{code}/{code}.{ext}"
# Result: "Yui Hatano/SSIS-001/SSIS-001.mp4"

# By studio and actress
naming_pattern: "{studio}/{actress}/{code} - {title}.{ext}"
# Result: "S1 NO.1 STYLE/Yui Hatano/SSIS-001 - Movie Title.mp4"

# By year
naming_pattern: "{year}/{actress}/{code}.{ext}"
# Result: "2023/Yui Hatano/SSIS-001.mp4"
```

### How do I configure proxy settings?

**For Docker (.env file):**
```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

**For manual installation (config.yaml):**
```yaml
network:
  proxy_url: "http://proxy.example.com:8080"
  # With authentication:
  # proxy_url: "http://user:pass@proxy.example.com:8080"
```

### Can I process files from multiple directories?

Currently, the tool processes one source directory at a time, but you can:

1. **Run multiple instances** with different configurations
2. **Use symbolic links** to combine multiple directories
3. **Run sequentially** by changing the source directory in configuration

Future versions may support multiple source directories natively.

## Usage and Operation

### How does the tool detect video codes from filenames?

The tool uses pattern matching to extract codes from filenames:

**Supported patterns:**
- `ABC-123.mp4` → `ABC-123`
- `[ABC-123] Title.mkv` → `ABC-123`
- `ABC123.avi` → `ABC-123` (adds hyphen)
- `Title ABC-123 [1080p].mp4` → `ABC-123`

**Tips for better detection:**
- Include the code in the filename
- Use standard format (STUDIO-NUMBER)
- Avoid special characters around the code

### What happens if metadata is not found?

If metadata cannot be found:
1. **File is moved to `_unorganized` folder** in the target directory
2. **Error is logged** with the reason (network error, no results, etc.)
3. **Processing continues** with the next file
4. **You can retry later** by moving files back to source directory

### Can I resume interrupted processing?

Yes! The tool includes progress tracking:

```bash
# Resume interrupted processing
av-scraper process --resume

# Or in Docker
docker-compose restart av-scraper
```

The tool automatically saves progress and can continue from where it left off.

### How do I process only specific files?

```bash
# Process specific files
av-scraper process --files "file1.mp4,file2.mkv"

# Process files matching pattern
av-scraper process --pattern "*SSIS*"

# Dry run to see what would be processed
av-scraper process --dry-run
```

### What happens to duplicate files?

The tool includes duplicate detection and handling:

**Configuration options:**
```yaml
organization:
  handle_duplicates: "skip"  # Options: skip, overwrite, rename
```

- **skip:** Leave existing file, skip the duplicate
- **overwrite:** Replace existing file with new one
- **rename:** Add suffix to new file (e.g., `movie_2.mp4`)

## Troubleshooting

### Why are no files being found during scan?

**Common causes:**
1. **Incorrect source directory path**
2. **Unsupported file extensions**
3. **Permission issues**
4. **Files in subdirectories** (check recursive scanning)

**Solutions:**
```bash
# Check directory contents
ls -la /path/to/source

# Test scanner
av-scraper scan --source /path/to/source --verbose

# Check supported extensions
av-scraper config show | grep extensions
```

### Why is metadata not being found?

**Common causes:**
1. **Network connectivity issues**
2. **Incorrect video codes in filenames**
3. **Website availability problems**
4. **Rate limiting or blocking**

**Solutions:**
```bash
# Test scrapers
av-scraper test scrapers

# Test network connectivity
curl -I https://javdb.com

# Check code detection
av-scraper scan --verbose

# Try different scraper priority
# In config.yaml:
scraping:
  priority: ["javlibrary", "javdb"]
```

### Why is the browser crashing?

**Common causes:**
1. **Insufficient memory**
2. **ChromeDriver version mismatch**
3. **Missing dependencies**
4. **Resource limits in Docker**

**Solutions:**
```bash
# Increase memory limit (Docker)
echo "MEMORY_LIMIT=4G" >> .env

# Reduce concurrent processing
# In config.yaml:
scraping:
  max_concurrent_files: 1

# Update Chrome/ChromeDriver
docker-compose build --no-cache  # Docker
# Or download latest versions for manual installation
```

### How do I fix permission errors?

**For Docker:**
```bash
# Set user/group IDs in .env
echo "PUID=$(id -u)" >> .env
echo "PGID=$(id -g)" >> .env

# Restart container
docker-compose down && docker-compose up -d
```

**For manual installation:**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER /path/to/directories
chmod -R 755 /path/to/directories
```

## Performance and Optimization

### How can I make processing faster?

**Increase concurrency (if you have resources):**
```yaml
scraping:
  max_concurrent_files: 4
  max_concurrent_requests: 3
  max_concurrent_downloads: 6
```

**Use faster storage:**
- SSD/NVMe for target directory
- Fast network connection
- Local storage vs. network storage

**Optimize Docker resources:**
```bash
# In .env
MEMORY_LIMIT=4G
CPU_LIMIT=4.0
```

### How much system resources does it use?

**Typical usage:**
- **Memory:** 1-2GB per concurrent file
- **CPU:** Moderate usage, spikes during image processing
- **Network:** Depends on image downloads and metadata requests
- **Disk:** Temporary space for downloads and processing

**Resource monitoring:**
```bash
# Monitor Docker container
docker stats av-metadata-scraper

# Monitor system resources
htop
iotop
```

### Can I run this on a Raspberry Pi?

Yes, but with limitations:

**Recommended settings for Pi:**
```yaml
scraping:
  max_concurrent_files: 1
  max_concurrent_requests: 1
  max_concurrent_downloads: 2

organization:
  resize_images: true
  image_quality: 75
```

**Docker configuration:**
```bash
# In .env
MEMORY_LIMIT=1G
CPU_LIMIT=1.0
```

## Docker-Specific Questions

### How do I update the Docker image?

```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d

# Or rebuild if using local Dockerfile
docker-compose build --no-cache
docker-compose up -d
```

### How do I access logs in Docker?

```bash
# View recent logs
docker-compose logs av-scraper

# Follow logs in real-time
docker-compose logs -f av-scraper

# View logs from specific time
docker-compose logs --since="2023-12-01T10:00:00" av-scraper
```

### How do I backup my Docker setup?

```bash
# Backup configuration and data
tar -czf backup-$(date +%Y%m%d).tar.gz \
  .env \
  config/ \
  organized/ \
  logs/

# Backup Docker volumes
docker run --rm -v av-metadata-scraper_data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/volumes-backup.tar.gz /data
```

### Can I run multiple instances?

Yes, you can run multiple instances for different directories:

```bash
# Create separate directories
mkdir instance1 instance2

# Copy configuration to each
cp -r config/ docker-compose.yml .env instance1/
cp -r config/ docker-compose.yml .env instance2/

# Modify .env in each instance with different:
# - SOURCE_DIR
# - TARGET_DIR
# - Container names (to avoid conflicts)

# Start each instance
cd instance1 && docker-compose up -d
cd instance2 && docker-compose up -d
```

## Legal and Ethical Questions

### Is this legal to use?

This tool is designed for **personal use** to organize your **legally owned** content. You should:

- Only use it with content you legally own
- Respect website terms of service
- Follow copyright laws in your jurisdiction
- Use reasonable request rates to avoid overloading websites

### Does this violate website terms of service?

The tool is designed to be respectful:
- Uses reasonable request delays
- Implements rate limiting
- Doesn't overload servers
- Only accesses publicly available information

However, you should review the terms of service of websites you're scraping and use the tool responsibly.

### Can I use this commercially?

The tool is provided for personal use. For commercial use:
- Review the project license
- Consider the legal implications
- Respect website terms of service
- Consider contacting website owners for permission

### How do I report inappropriate content or copyright issues?

If you encounter issues:
1. **Remove the content** from your collection
2. **Report to appropriate authorities** if necessary
3. **Contact website administrators** for content issues
4. **Follow local laws** regarding content reporting

## Advanced Usage

### Can I add custom scrapers?

Yes! The architecture is designed to be extensible. See the [Developer Guide](DEVELOPER_GUIDE.md) for detailed instructions on:
- Creating custom scraper classes
- Implementing the BaseScraper interface
- Adding scrapers to the factory
- Testing new scrapers

### Can I integrate this with other tools?

The tool provides several integration options:

**Command-line integration:**
```bash
# JSON output for scripting
av-scraper status --json

# Exit codes for automation
if av-scraper process; then
  echo "Processing completed successfully"
fi
```

**Webhook notifications:**
```yaml
# In config.yaml
webhooks:
  completion_url: "http://your-server/webhook"
  error_url: "http://your-server/error-webhook"
```

**File system integration:**
- Watch source directory for new files
- Trigger processing on file system events
- Integration with download managers

### How do I contribute to the project?

We welcome contributions! See the [Developer Guide](DEVELOPER_GUIDE.md) for:
- Setting up development environment
- Code style guidelines
- Testing requirements
- Pull request process

**Ways to contribute:**
- Bug reports and feature requests
- Code contributions (new features, bug fixes)
- Documentation improvements
- New scraper implementations
- Testing and feedback

### Can I run this as a service?

Yes, you can set up the tool as a system service:

**Docker with systemd:**
```bash
# Create systemd service file
sudo tee /etc/systemd/system/av-scraper.service > /dev/null <<EOF
[Unit]
Description=AV Metadata Scraper
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/av-metadata-scraper
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable av-scraper.service
sudo systemctl start av-scraper.service
```

**Scheduled processing with cron:**
```bash
# Add to crontab for daily processing
0 2 * * * cd /path/to/av-metadata-scraper && docker-compose exec av-scraper av-scraper process
```

### How do I monitor the application?

**Built-in monitoring:**
```bash
# Check application status
av-scraper status

# View statistics
av-scraper stats

# Health check
av-scraper health --verbose
```

**External monitoring:**
- Prometheus metrics (future feature)
- Log aggregation (ELK stack, etc.)
- Webhook notifications for alerts
- File system monitoring for completion

---

**Still have questions?** 

- Check the [User Guide](USER_GUIDE.md) for detailed usage instructions
- See the [Troubleshooting Guide](TROUBLESHOOTING.md) for common issues
- Review the [API Documentation](API_DOCUMENTATION.md) for technical details
- Create an issue in the project repository for specific problems