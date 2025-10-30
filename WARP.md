# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

AutoJAV is an automated Japanese AV video metadata scraper and file organizer. It scrapes metadata from multiple sources (JavDB, JavLibrary, JAVBus), downloads cover images, and organizes video files into a structured directory layout.

## Common Commands

### Testing
```powershell
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/ -m "unit" --cov=src --cov-report=term-missing -v

# Run integration tests
pytest tests/integration/ -m "integration" -v

# Run performance tests
pytest tests/performance/ -m "performance" -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

### Code Quality
```powershell
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Run linter (flake8)
flake8 src/ tests/ --max-line-length=127

# Type checking (mypy)
mypy src/ --ignore-missing-imports
```

### Running the Application

#### Direct Mode (Python)
```powershell
# Run once with default config
python main.py

# Run with custom config
python main.py --config config/custom_config.yaml

# Run in watch mode (continuous monitoring)
python main.py --watch
```

#### CLI Mode
```powershell
# Enter CLI mode
python main.py --cli

# Process files
python main.py --cli process

# Scan directory
python main.py --cli scan --source /path/to/videos

# Check status
python main.py --cli status --json

# Run health check
python main.py --cli health --verbose

# Configuration wizard
python main.py --cli config wizard
```

#### Docker
```powershell
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f av-scraper

# Stop services
docker-compose down

# Rebuild image
docker-compose build --no-cache
```

### Development Scripts
The `scripts/` directory contains many helper scripts:
```powershell
# Test scrapers
python scripts/test_javdb.py

# Browser debugging
python scripts/debug_browser.py
python scripts/open_javdb_browser.py

# Login helpers (for JavDB authentication)
python scripts/javdb_login_helper.py
python scripts/manual_login.py

# Configuration validation
python scripts/validate_config.py
```

## Architecture

### Core Components

#### 1. Main Application (`src/main_application.py`)
- **AVMetadataScraper**: Central orchestrator that coordinates the entire workflow
- Manages the processing pipeline: scan → scrape → organize → download images
- Supports two execution modes:
  - **Direct mode**: Run once and exit
  - **Watch mode**: Continuously monitor for new files
- Implements concurrent processing with worker tasks and queues
- Integrates error handling, progress tracking, and performance monitoring

#### 2. Scraper System (`src/scrapers/`)
**Factory Pattern**: `ScraperFactory` creates and configures all scrapers
- **BaseScraper**: Abstract base class defining the scraper interface
- **MetadataScraper**: Sequential fallback coordinator - tries scrapers by priority
- **ParallelMetadataScraper**: Parallel coordinator - queries all sources simultaneously
- **Individual Scrapers**:
  - `JavDBScraper`: Primary source, requires Selenium/WebDriver, supports login
  - `JavLibraryScraper`: Secondary source, HTTP-based
  - `JAVBusScraper`: Tertiary source, HTTP-based

**Key Insight**: The factory creates scrapers with proper WebDriver/HTTP client injection, handles proxy configuration, and manages login credentials.

#### 3. File Organization (`src/organizers/`)
- **FileOrganizer**: Moves/copies files to structured directories
- Supports naming patterns: `{actress}/{code}/{code}.{ext}`
- Conflict resolution strategies: rename, skip, overwrite
- Creates metadata JSON files alongside videos
- Safe mode option to copy instead of move

#### 4. Image Downloading (`src/downloaders/`)
- **ImageDownloader**: Async concurrent image downloads
- Supports multiple image types: cover, poster, thumbnail, screenshots
- Optional image resizing and thumbnail generation
- Rate limiting and retry logic

#### 5. File Scanning (`src/scanner/`)
- **FileScanner**: Recursively scans directories for video files
- Extracts movie codes from filenames using regex patterns
- Supports multiple video formats (.mp4, .mkv, .avi)

#### 6. CLI System (`src/cli/`)
- **AVScraperCLI**: Full command-line interface with subcommands
- Commands: process, scan, status, stop, config, health, stats, advanced
- Interactive configuration wizard
- JSON output support for scripting

#### 7. Utilities (`src/utils/`)
- **WebDriverManager**: Manages Selenium WebDriver lifecycle (supports Selenium Grid for Docker)
- **LoginManager**: Handles JavDB authentication with captcha support
- **HttpClient**: HTTP client with proxy, rate limiting, retries
- **ErrorHandler**: Centralized error handling with categorization
- **ProgressTracker**: Real-time progress tracking for operations
- **ProgressPersistence**: Session management for resumable processing
- **DuplicateDetector**: File hash-based duplicate detection
- **PerformanceMonitor**: Performance metrics collection
- **FileWatcher**: File system monitoring for watch mode

### Data Flow

1. **Scanning**: FileScanner finds video files and extracts codes
2. **Queuing**: Files are added to async processing queue
3. **Workers**: Concurrent workers (configurable) process files from queue
4. **Scraping**: MetadataScraper queries sources by priority until metadata found
5. **Organization**: FileOrganizer moves files to target directory with proper naming
6. **Images**: ImageDownloader fetches cover/poster images
7. **Completion**: Progress tracking updates, statistics collected

### Configuration System (`src/config/`)
- **ConfigManager**: Loads and validates YAML configuration
- Supports environment variable overrides
- Configuration sections: scrapers, directories, network, processing, logging
- Default config location: `config/config.yaml`

### Key Design Patterns

1. **Factory Pattern**: ScraperFactory for creating scrapers with dependencies
2. **Strategy Pattern**: Different duplicate handling and conflict resolution strategies
3. **Singleton Pattern**: Utility managers (error handler, progress tracker)
4. **Worker Pool Pattern**: Async queue-based concurrent processing
5. **Context Manager Pattern**: Performance monitoring and progress tracking contexts

## Important Behaviors

### Selenium/WebDriver Usage
- JavDB requires WebDriver (Chrome/Chromium) for JavaScript rendering
- In Docker: connects to Selenium Grid (`selenium-grid:4444`)
- Local: uses webdriver-manager to download/manage ChromeDriver
- Login state persists via cookies saved to `config/javdb_cookies.json`

### Proxy Configuration
- Global proxy setting in `config.yaml` under `network.proxy_url`
- Applied to both WebDriver and HTTP clients
- Essential for accessing blocked websites

### Concurrent Processing
- Configurable worker count: `processing.max_concurrent_files`
- Separate concurrency limits for requests and downloads
- Uses asyncio queues and tasks for coordination

### Error Handling
- Errors categorized (FILE_SYSTEM, NETWORK, SCRAPING, etc.)
- Automatic retry logic for transient failures
- Errors don't stop entire pipeline, just skip problematic files

### Watch Mode
- Uses watchdog library for file system monitoring
- Cooldown period to avoid processing incomplete file transfers
- Tracks processed files to avoid reprocessing

## Project-Specific Conventions

### Code Naming
- Movie codes are referred to as "code" (e.g., "SSIS-001")
- Files are "video files" or "VideoFile" objects
- Metadata results are "MovieMetadata" objects

### Directory Structure
- Source: unorganized video files
- Target: organized output with actress/code structure
- Config: configuration files and cookies
- Logs: application logs

### Testing
- Tests marked with pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.performance`
- Integration tests require Chrome/ChromeDriver
- Performance tests use `pytest-benchmark`

### Docker Deployment
- Multi-stage build for optimized image size
- Separate services: `av-scraper` (backend), `av-scraper-web` (web UI), `selenium-grid`
- Health checks use `docker/healthcheck.py` or `docker/healthcheck_simple.py`
- Volume mounts for source, target, config, logs

### API Server
- Flask-based API server in `src/api_server.py`
- Exposed on port 5555
- Provides REST endpoints for status, control, configuration

## Development Notes

### When Adding New Scrapers
1. Inherit from `BaseScraper`
2. Implement `search_movie()` and `is_available()` methods
3. Add to `ScraperFactory._create_scraper()` switch
4. Update default config in `ScraperFactory.__init__()`

### When Modifying Processing Pipeline
- Main pipeline is in `AVMetadataScraper._run_processing_pipeline()`
- Workers execute `_worker_loop()` and call `_process_single_file()`
- Add progress tracking contexts for new steps
- Update ProcessingStats dataclass if tracking new metrics

### Configuration Changes
- Update `ConfigManager` validation if adding required fields
- Update docker-compose.yml environment variables
- Update config examples in docs/

### Windows-Specific Notes
- Use PowerShell for commands (current environment)
- Path separators handled by `pathlib.Path`
- WebDriver must match Chrome version on Windows
