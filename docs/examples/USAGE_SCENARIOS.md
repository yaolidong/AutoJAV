# AV Metadata Scraper - Usage Scenarios

This document provides real-world usage scenarios and examples for different types of users and setups.

## Table of Contents

- [Home User Scenarios](#home-user-scenarios)
- [Server and NAS Scenarios](#server-and-nas-scenarios)
- [Advanced User Scenarios](#advanced-user-scenarios)
- [Corporate/Multi-User Scenarios](#corporatemulti-user-scenarios)
- [Development and Testing Scenarios](#development-and-testing-scenarios)

## Home User Scenarios

### Scenario 1: Basic Home Setup

**User Profile:** Home user with a personal collection on Windows/Mac/Linux desktop

**Requirements:**
- Simple setup and operation
- Process files occasionally
- Basic organization by actress and code
- Download cover images

**Setup:**

1. **Docker Installation (Recommended):**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd av-metadata-scraper
   
   # Configure environment
   cp .env.example .env
   ```

2. **Edit .env file:**
   ```bash
   SOURCE_DIR=C:\Users\YourName\Videos\Unsorted  # Windows
   # SOURCE_DIR=/home/username/Videos/Unsorted   # Linux
   # SOURCE_DIR=/Users/username/Videos/Unsorted  # Mac
   
   TARGET_DIR=C:\Users\YourName\Videos\Organized
   MAX_CONCURRENT_FILES=2
   LOG_LEVEL=INFO
   SAFE_MODE=true
   ```

3. **Basic configuration (config/config.yaml):**
   ```yaml
   directories:
     source: "/app/source"
     target: "/app/target"
   
   scraping:
     priority: ["javdb", "javlibrary"]
     max_concurrent_files: 2
     retry_attempts: 3
   
   organization:
     naming_pattern: "{actress}/{code}/{code}.{ext}"
     download_images: true
     safe_mode: true
   
   browser:
     headless: true
   
   logging:
     level: "INFO"
   ```

4. **Start processing:**
   ```bash
   docker-compose up -d
   
   # Monitor progress
   docker-compose logs -f av-scraper
   ```

**Expected Results:**
- Files organized as: `Organized/Actress Name/ABC-123/ABC-123.mp4`
- Cover images downloaded
- Metadata saved as JSON files
- Processing logs available

### Scenario 2: Home User with JavDB Account

**User Profile:** Enthusiast with JavDB account wanting better metadata

**Additional Configuration:**

1. **Add JavDB credentials to .env:**
   ```bash
   JAVDB_USERNAME=your_username
   JAVDB_PASSWORD=your_password
   ```

2. **Enhanced config.yaml:**
   ```yaml
   credentials:
     javdb:
       username: "your_username"
       password: "your_password"
   
   scraping:
     priority: ["javdb", "javlibrary"]  # JavDB first for better results
     max_concurrent_files: 3
   
   organization:
     naming_pattern: "{studio}/{actress}/{code} - {title}.{ext}"
     download_images: true
     create_thumbnails: true
   ```

**Benefits:**
- Access to more detailed metadata
- Better success rate for finding information
- Additional images and screenshots
- More accurate actress and studio information

### Scenario 3: Home User with Proxy/VPN

**User Profile:** User behind corporate firewall or using VPN

**Configuration:**

1. **Proxy settings in .env:**
   ```bash
   HTTP_PROXY=http://proxy.company.com:8080
   HTTPS_PROXY=http://proxy.company.com:8080
   # Or for SOCKS proxy:
   # HTTP_PROXY=socks5://127.0.0.1:1080
   ```

2. **Network configuration:**
   ```yaml
   network:
     proxy_url: "http://proxy.company.com:8080"
     verify_ssl: true
     timeout: 60  # Longer timeout for slow connections
   
   scraping:
     retry_attempts: 5  # More retries for unreliable connections
     timeout: 60
   ```

## Server and NAS Scenarios

### Scenario 4: Synology NAS Setup

**User Profile:** Home server enthusiast with Synology NAS

**Setup Process:**

1. **Enable Docker on Synology:**
   - Install Docker package from Package Center
   - Enable SSH access

2. **Create directory structure:**
   ```bash
   # SSH into NAS
   mkdir -p /volume1/docker/av-scraper/{config,logs}
   mkdir -p /volume1/videos/{unsorted,organized}
   ```

3. **Docker Compose configuration:**
   ```yaml
   version: '3.8'
   services:
     av-scraper:
       image: av-metadata-scraper:latest
       container_name: av-scraper
       restart: unless-stopped
       environment:
         - SOURCE_DIR=/app/source
         - TARGET_DIR=/app/target
         - LOG_LEVEL=INFO
         - TZ=Asia/Tokyo
         - PUID=1026  # Synology user ID
         - PGID=100   # Synology users group
       volumes:
         - /volume1/videos/unsorted:/app/source:ro
         - /volume1/videos/organized:/app/target
         - /volume1/docker/av-scraper/config:/app/config
         - /volume1/docker/av-scraper/logs:/app/logs
       networks:
         - av-scraper-network
   
   networks:
     av-scraper-network:
       driver: bridge
   ```

4. **Automated processing with Task Scheduler:**
   - Create scheduled task in Synology DSM
   - Run daily at 2 AM: `docker-compose -f /volume1/docker/av-scraper/docker-compose.yml exec av-scraper av-scraper process`

### Scenario 5: Unraid Server Setup

**User Profile:** Unraid server with Docker support

**Setup:**

1. **Install from Community Applications:**
   - Search for "AV Metadata Scraper" in CA
   - Or add custom Docker container

2. **Container configuration:**
   ```
   Repository: av-metadata-scraper:latest
   Network Type: Bridge
   
   Port Mappings:
   - Container Port: 9222, Host Port: 9222 (for debugging)
   
   Volume Mappings:
   - Container Path: /app/source, Host Path: /mnt/user/videos/unsorted, Access Mode: Read Only
   - Container Path: /app/target, Host Path: /mnt/user/videos/organized, Access Mode: Read/Write
   - Container Path: /app/config, Host Path: /mnt/user/appdata/av-scraper/config
   - Container Path: /app/logs, Host Path: /mnt/user/appdata/av-scraper/logs
   
   Environment Variables:
   - MAX_CONCURRENT_FILES=4
   - LOG_LEVEL=INFO
   - SAFE_MODE=true
   ```

3. **User Scripts for automation:**
   ```bash
   #!/bin/bash
   # /boot/config/plugins/user.scripts/scripts/av-scraper-daily/script
   
   echo "Starting AV Metadata Scraper daily processing..."
   docker exec av-scraper av-scraper process
   echo "Processing completed."
   ```

### Scenario 6: Ubuntu Server with Systemd

**User Profile:** Linux server administrator

**Setup:**

1. **Install Docker and Docker Compose:**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   sudo apt-get install docker-compose-plugin
   ```

2. **Create systemd service:**
   ```bash
   sudo tee /etc/systemd/system/av-scraper.service > /dev/null <<EOF
   [Unit]
   Description=AV Metadata Scraper
   Requires=docker.service
   After=docker.service
   
   [Service]
   Type=oneshot
   RemainAfterExit=yes
   User=avuser
   Group=avuser
   WorkingDirectory=/opt/av-scraper
   ExecStart=/usr/bin/docker-compose up -d
   ExecStop=/usr/bin/docker-compose down
   ExecReload=/usr/bin/docker-compose restart
   TimeoutStartSec=0
   
   [Install]
   WantedBy=multi-user.target
   EOF
   
   sudo systemctl enable av-scraper.service
   sudo systemctl start av-scraper.service
   ```

3. **Monitoring with systemd:**
   ```bash
   # Check status
   sudo systemctl status av-scraper
   
   # View logs
   sudo journalctl -u av-scraper -f
   
   # Restart service
   sudo systemctl restart av-scraper
   ```

## Advanced User Scenarios

### Scenario 7: High-Performance Processing Server

**User Profile:** Power user with dedicated server for large collections

**Hardware:**
- 32GB RAM
- 16-core CPU
- NVMe SSD storage
- 10Gbps network

**Configuration:**

1. **High-performance .env:**
   ```bash
   SOURCE_DIR=/mnt/nvme/videos/unsorted
   TARGET_DIR=/mnt/nvme/videos/organized
   
   # Aggressive concurrency settings
   MAX_CONCURRENT_FILES=8
   MAX_CONCURRENT_REQUESTS=6
   MAX_CONCURRENT_DOWNLOADS=12
   
   # Resource limits
   MEMORY_LIMIT=16G
   CPU_LIMIT=12.0
   
   # Performance optimizations
   SAFE_MODE=false  # Move files instead of copy
   RESIZE_IMAGES=false  # Keep original quality
   CREATE_THUMBNAILS=true
   ```

2. **Optimized config.yaml:**
   ```yaml
   scraping:
     max_concurrent_files: 8
     max_concurrent_requests: 6
     max_concurrent_downloads: 12
     timeout: 15  # Faster timeout
     delay_between_requests: 0.5  # Shorter delays
   
   performance:
     memory_limit_mb: 16384
     cache_size: 5000  # Large cache
     cleanup_temp_files: true
   
   organization:
     safe_mode: false
     image_quality: 95  # High quality
   ```

3. **Monitoring setup:**
   ```bash
   # Install monitoring tools
   docker run -d --name=cadvisor \
     --publish=8080:8080 \
     --volume=/:/rootfs:ro \
     --volume=/var/run:/var/run:ro \
     --volume=/sys:/sys:ro \
     --volume=/var/lib/docker/:/var/lib/docker:ro \
     gcr.io/cadvisor/cadvisor:latest
   
   # Prometheus monitoring
   docker run -d --name=prometheus \
     --publish=9090:9090 \
     prom/prometheus
   ```

### Scenario 8: Multi-Source Processing

**User Profile:** Advanced user with multiple video sources and complex organization

**Setup:**

1. **Multiple source directories:**
   ```bash
   # Create separate instances for different sources
   mkdir -p ~/av-scraper/{instance1,instance2,instance3}
   
   # Instance 1: New downloads
   cd ~/av-scraper/instance1
   cat > .env <<EOF
   SOURCE_DIR=/downloads/new-videos
   TARGET_DIR=/organized/new
   MAX_CONCURRENT_FILES=4
   EOF
   
   # Instance 2: Archive processing
   cd ~/av-scraper/instance2
   cat > .env <<EOF
   SOURCE_DIR=/archive/old-videos
   TARGET_DIR=/organized/archive
   MAX_CONCURRENT_FILES=2
   SAFE_MODE=true
   EOF
   
   # Instance 3: High-priority processing
   cd ~/av-scraper/instance3
   cat > .env <<EOF
   SOURCE_DIR=/priority/videos
   TARGET_DIR=/organized/priority
   MAX_CONCURRENT_FILES=6
   JAVDB_USERNAME=premium_account
   JAVDB_PASSWORD=premium_password
   EOF
   ```

2. **Orchestration script:**
   ```bash
   #!/bin/bash
   # process-all.sh
   
   echo "Starting multi-instance processing..."
   
   # Start all instances
   for instance in instance1 instance2 instance3; do
     echo "Starting $instance..."
     cd ~/av-scraper/$instance
     docker-compose up -d
   done
   
   # Monitor progress
   while true; do
     echo "=== Processing Status ==="
     for instance in instance1 instance2 instance3; do
       cd ~/av-scraper/$instance
       echo "$instance: $(docker-compose exec av-scraper av-scraper status --json | jq -r '.status')"
     done
     sleep 60
   done
   ```

### Scenario 9: Custom Scraper Integration

**User Profile:** Developer adding support for new websites

**Implementation:**

1. **Create custom scraper:**
   ```python
   # src/scrapers/custom_site_scraper.py
   from .base_scraper import BaseScraper
   from ..models.movie_metadata import MovieMetadata
   
   class CustomSiteScraper(BaseScraper):
       @property
       def name(self) -> str:
           return "customsite"
       
       @property
       def base_url(self) -> str:
           return "https://customsite.com"
       
       async def search_movie(self, code: str) -> Optional[MovieMetadata]:
           # Custom implementation
           pass
   ```

2. **Register in factory:**
   ```python
   # src/scrapers/scraper_factory.py
   from .custom_site_scraper import CustomSiteScraper
   
   def create_scraper(scraper_type: str, config: Config) -> BaseScraper:
       # Add custom scraper
       if scraper_type == "customsite":
           return CustomSiteScraper(config)
   ```

3. **Update configuration:**
   ```yaml
   scraping:
     priority: ["customsite", "javdb", "javlibrary"]
   ```

## Corporate/Multi-User Scenarios

### Scenario 10: Corporate Environment with Proxy

**User Profile:** Corporate user behind firewall with authentication

**Configuration:**

1. **Proxy with authentication:**
   ```bash
   # .env
   HTTP_PROXY=http://username:password@proxy.company.com:8080
   HTTPS_PROXY=http://username:password@proxy.company.com:8080
   NO_PROXY=localhost,127.0.0.1,company.internal
   ```

2. **Corporate security settings:**
   ```yaml
   network:
     verify_ssl: true
     proxy_url: "http://username:password@proxy.company.com:8080"
   
   browser:
     chrome_options:
       - "--proxy-server=http://proxy.company.com:8080"
       - "--disable-web-security"  # If needed for corporate certificates
   
   logging:
     level: "WARNING"  # Reduce log verbosity
   ```

3. **Compliance and monitoring:**
   ```yaml
   features:
     enable_statistics_tracking: true
     enable_webhook_notifications: true
   
   webhooks:
     completion_url: "https://monitoring.company.com/av-scraper/complete"
     error_url: "https://monitoring.company.com/av-scraper/error"
     headers:
       "Authorization": "Bearer company-token"
   ```

### Scenario 11: Multi-Tenant Setup

**User Profile:** Service provider hosting for multiple users

**Architecture:**

1. **Docker Compose for multi-tenancy:**
   ```yaml
   version: '3.8'
   services:
     av-scraper-user1:
       image: av-metadata-scraper:latest
       container_name: av-scraper-user1
       environment:
         - SOURCE_DIR=/app/source
         - TARGET_DIR=/app/target
         - TENANT_ID=user1
       volumes:
         - /data/user1/source:/app/source:ro
         - /data/user1/organized:/app/target
         - /config/user1:/app/config
       networks:
         - user1-network
     
     av-scraper-user2:
       image: av-metadata-scraper:latest
       container_name: av-scraper-user2
       environment:
         - SOURCE_DIR=/app/source
         - TARGET_DIR=/app/target
         - TENANT_ID=user2
       volumes:
         - /data/user2/source:/app/source:ro
         - /data/user2/organized:/app/target
         - /config/user2:/app/config
       networks:
         - user2-network
   
   networks:
     user1-network:
       driver: bridge
     user2-network:
       driver: bridge
   ```

2. **Resource management:**
   ```bash
   # Set resource limits per user
   docker update --memory=2g --cpus=1.0 av-scraper-user1
   docker update --memory=4g --cpus=2.0 av-scraper-user2
   ```

3. **Monitoring and billing:**
   ```bash
   #!/bin/bash
   # collect-usage-stats.sh
   
   for user in user1 user2; do
     stats=$(docker stats av-scraper-$user --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}")
     echo "User: $user, Stats: $stats" >> /var/log/usage-stats.log
   done
   ```

## Development and Testing Scenarios

### Scenario 12: Development Environment

**User Profile:** Developer working on the project

**Setup:**

1. **Development Docker Compose:**
   ```yaml
   version: '3.8'
   services:
     av-scraper-dev:
       build:
         context: .
         dockerfile: Dockerfile.dev
       container_name: av-scraper-dev
       environment:
         - DEBUG_MODE=true
         - LOG_LEVEL=DEBUG
         - ENABLE_DEVTOOLS=true
       volumes:
         - ./src:/app/src:rw  # Live code editing
         - ./tests:/app/tests:rw
         - ./config:/app/config
         - ./test-data:/app/source:ro
         - ./test-output:/app/target
       ports:
         - "9222:9222"  # Chrome DevTools
         - "8000:8000"  # Development server
       command: ["python", "-m", "pytest", "--watch"]
   ```

2. **Test data setup:**
   ```bash
   # Create test video files
   mkdir -p test-data
   for code in SSIS-001 STARS-123 MIDE-456; do
     echo "fake video content" > "test-data/${code}.mp4"
   done
   ```

3. **Development workflow:**
   ```bash
   # Start development environment
   docker-compose -f docker-compose.dev.yml up -d
   
   # Run tests
   docker-compose exec av-scraper-dev pytest tests/
   
   # Debug with Chrome DevTools
   # Open http://localhost:9222 in browser
   
   # Live code editing
   # Edit files in src/ and see changes immediately
   ```

### Scenario 13: CI/CD Pipeline

**User Profile:** DevOps engineer setting up automated testing

**GitHub Actions workflow:**

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        flake8 src/ tests/
        black --check src/ tests/
        isort --check-only src/ tests/
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  docker-test:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t av-metadata-scraper:test .
    
    - name: Test Docker image
      run: |
        docker run --rm av-metadata-scraper:test --version
        docker run --rm av-metadata-scraper:test config validate

  deploy:
    runs-on: ubuntu-latest
    needs: [test, docker-test]
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build and push Docker image
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker build -t av-metadata-scraper:latest .
        docker push av-metadata-scraper:latest
```

### Scenario 14: Performance Testing

**User Profile:** QA engineer testing performance characteristics

**Setup:**

1. **Performance test configuration:**
   ```yaml
   # config/performance-test.yaml
   directories:
     source: "/test-data/large-collection"
     target: "/test-output/performance"
   
   scraping:
     max_concurrent_files: 10
     max_concurrent_requests: 8
     max_concurrent_downloads: 16
   
   performance:
     memory_limit_mb: 8192
     cache_size: 10000
   ```

2. **Load testing script:**
   ```python
   # tests/performance/test_load.py
   import asyncio
   import time
   from pathlib import Path
   
   async def test_large_collection_processing():
       """Test processing of large video collection."""
       # Create 1000 test files
       test_files = create_test_collection(1000)
       
       start_time = time.time()
       
       # Process files
       scraper = AVMetadataScraper("config/performance-test.yaml")
       result = await scraper.process_files()
       
       end_time = time.time()
       processing_time = end_time - start_time
       
       # Performance assertions
       assert result.processed_count == 1000
       assert processing_time < 3600  # Should complete within 1 hour
       assert result.error_count < 50  # Less than 5% error rate
       
       # Calculate throughput
       throughput = result.processed_count / processing_time
       print(f"Throughput: {throughput:.2f} files/second")
   ```

3. **Memory profiling:**
   ```bash
   # Install memory profiler
   pip install memory-profiler psutil
   
   # Run with memory profiling
   python -m memory_profiler main.py
   
   # Generate memory usage report
   mprof run main.py
   mprof plot
   ```

---

These scenarios cover a wide range of real-world usage patterns and can be adapted to specific needs. Each scenario includes practical configuration examples and step-by-step setup instructions.