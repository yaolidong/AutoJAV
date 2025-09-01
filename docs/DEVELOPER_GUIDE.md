# AV Metadata Scraper - Developer Guide

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Contributing Guidelines](#contributing-guidelines)
- [Adding New Scrapers](#adding-new-scrapers)
- [Testing](#testing)
- [Code Style](#code-style)
- [Debugging](#debugging)
- [Performance Optimization](#performance-optimization)
- [Release Process](#release-process)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- Chrome/Chromium browser
- ChromeDriver
- Docker (optional, for testing)

### Local Development Environment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd av-metadata-scraper
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   # Install main dependencies
   pip install -r requirements.txt
   
   # Install development dependencies
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

5. **Set up configuration:**
   ```bash
   cp config/config.yaml.example config/config.yaml
   # Edit config.yaml with your test settings
   ```

6. **Run tests:**
   ```bash
   pytest tests/
   ```

### Development Dependencies

The `requirements-dev.txt` includes:

```text
# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0

# Code Quality
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.0.0

# Documentation
sphinx>=6.0.0
sphinx-rtd-theme>=1.2.0

# Development Tools
pre-commit>=3.0.0
ipython>=8.0.0
jupyter>=1.0.0

# Debugging
pdb++>=0.10.0
ipdb>=0.13.0
```

### IDE Configuration

#### VS Code

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### PyCharm

1. Set interpreter to `.venv/bin/python`
2. Enable Black formatter
3. Configure isort with Black profile
4. Enable flake8 and mypy inspections

## Project Structure

```
av-metadata-scraper/
├── src/                          # Source code
│   ├── __init__.py
│   ├── main_application.py       # Main application class
│   ├── cli/                      # Command line interface
│   │   ├── __init__.py
│   │   ├── cli_main.py          # CLI entry point
│   │   ├── config_wizard.py     # Interactive configuration
│   │   └── commands/            # CLI commands
│   ├── config/                   # Configuration management
│   │   ├── __init__.py
│   │   └── config_manager.py
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration model
│   │   ├── movie_metadata.py    # Movie metadata model
│   │   └── video_file.py        # Video file model
│   ├── scanner/                  # File scanning
│   │   ├── __init__.py
│   │   └── file_scanner.py
│   ├── scrapers/                 # Website scrapers
│   │   ├── __init__.py
│   │   ├── base_scraper.py      # Abstract base scraper
│   │   ├── javdb_scraper.py     # JavDB scraper
│   │   ├── javlibrary_scraper.py # JavLibrary scraper
│   │   ├── metadata_scraper.py   # Scraper coordinator
│   │   └── scraper_factory.py   # Scraper factory
│   ├── organizers/               # File organization
│   │   ├── __init__.py
│   │   └── file_organizer.py
│   ├── downloaders/              # Image downloading
│   │   ├── __init__.py
│   │   └── image_downloader.py
│   └── utils/                    # Utility modules
│       ├── __init__.py
│       ├── error_handler.py     # Error handling
│       ├── http_client.py       # HTTP client wrapper
│       ├── logging_config.py    # Logging configuration
│       ├── login_manager.py     # Login management
│       ├── progress_tracker.py  # Progress tracking
│       └── webdriver_manager.py # WebDriver management
├── tests/                        # Test files
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration
│   ├── fixtures/                # Test fixtures
│   ├── integration/             # Integration tests
│   ├── performance/             # Performance tests
│   └── test_*.py               # Unit tests
├── docs/                         # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   ├── TROUBLESHOOTING.md
│   └── examples/               # Configuration examples
├── config/                       # Configuration files
│   ├── config.yaml.example
│   └── config.yaml.template
├── docker/                       # Docker files
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── scripts/
├── scripts/                      # Utility scripts
├── examples/                     # Usage examples
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── pyproject.toml               # Project configuration
├── setup.py                     # Package setup
└── README.md                    # Project README
```

## Architecture Overview

### Core Components

1. **Main Application (`main_application.py`)**
   - Orchestrates the entire process
   - Manages component lifecycle
   - Handles configuration and logging

2. **File Scanner (`scanner/file_scanner.py`)**
   - Discovers video files in directories
   - Extracts codes from filenames
   - Provides file metadata

3. **Metadata Scraper (`scrapers/metadata_scraper.py`)**
   - Coordinates multiple scraper sources
   - Implements retry and fallback logic
   - Manages scraper priority

4. **Individual Scrapers (`scrapers/*_scraper.py`)**
   - Implement website-specific scraping logic
   - Handle login and session management
   - Parse HTML and extract metadata

5. **File Organizer (`organizers/file_organizer.py`)**
   - Organizes files based on metadata
   - Creates directory structures
   - Handles file operations

6. **Image Downloader (`downloaders/image_downloader.py`)**
   - Downloads cover images and posters
   - Handles image processing and optimization
   - Manages concurrent downloads

### Design Patterns

#### Abstract Factory Pattern
Used for scraper creation:

```python
class ScraperFactory:
    @staticmethod
    def create_scraper(scraper_type: str, config: Config) -> BaseScraper:
        if scraper_type == "javdb":
            return JavDBScraper(config)
        elif scraper_type == "javlibrary":
            return JavLibraryScraper(config)
        else:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
```

#### Strategy Pattern
Used for different organization strategies:

```python
class OrganizationStrategy(ABC):
    @abstractmethod
    def generate_path(self, metadata: MovieMetadata) -> Path:
        pass

class ActressCodeStrategy(OrganizationStrategy):
    def generate_path(self, metadata: MovieMetadata) -> Path:
        return Path(f"{metadata.primary_actress}/{metadata.code}")
```

#### Observer Pattern
Used for progress tracking:

```python
class ProgressObserver(ABC):
    @abstractmethod
    def on_progress_update(self, progress: ProgressInfo) -> None:
        pass

class FileProgressObserver(ProgressObserver):
    def on_progress_update(self, progress: ProgressInfo) -> None:
        # Save progress to file
        pass
```

## Contributing Guidelines

### Code Contribution Process

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes:**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation

4. **Run tests and linting:**
   ```bash
   # Run tests
   pytest tests/
   
   # Run linting
   flake8 src/ tests/
   black --check src/ tests/
   isort --check-only src/ tests/
   mypy src/
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

6. **Push and create pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

Use conventional commits format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(scrapers): add new scraper for example.com
fix(organizer): handle special characters in filenames
docs: update API documentation
test: add integration tests for file scanner
```

### Pull Request Guidelines

1. **Title**: Use descriptive title following conventional commits
2. **Description**: Explain what changes were made and why
3. **Testing**: Describe how the changes were tested
4. **Documentation**: Update relevant documentation
5. **Breaking Changes**: Clearly mark any breaking changes

## Adding New Scrapers

### Step 1: Create Scraper Class

Create a new file `src/scrapers/yoursite_scraper.py`:

```python
from typing import Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from ..models.movie_metadata import MovieMetadata
from ..models.config import Config

class YourSiteScraper(BaseScraper):
    """Scraper for YourSite website."""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self._base_url = "https://yoursite.com"
    
    @property
    def name(self) -> str:
        return "yoursite"
    
    @property
    def base_url(self) -> str:
        return self._base_url
    
    async def search_movie(self, code: str) -> Optional[MovieMetadata]:
        """Search for movie metadata by code."""
        try:
            # Implement search logic
            search_url = f"{self._base_url}/search?q={code}"
            response = await self._http_client.get(search_url)
            
            if response.status_code != 200:
                return None
            
            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')
            movie_links = self._parse_search_results(soup)
            
            if not movie_links:
                return None
            
            # Get detailed movie information
            movie_url = movie_links[0]  # Take first result
            movie_response = await self._http_client.get(movie_url)
            movie_soup = BeautifulSoup(movie_response.text, 'html.parser')
            
            return self._parse_movie_page(movie_soup, movie_url)
            
        except Exception as e:
            self.logger.error(f"Error scraping {code}: {e}")
            return None
    
    async def is_available(self) -> bool:
        """Check if the scraper is available."""
        try:
            response = await self._http_client.get(self._base_url)
            return response.status_code == 200
        except:
            return False
    
    def _parse_search_results(self, soup: BeautifulSoup) -> List[str]:
        """Parse search results to extract movie URLs."""
        # Implement parsing logic specific to the site
        links = []
        for link in soup.find_all('a', class_='movie-link'):
            href = link.get('href')
            if href:
                links.append(f"{self._base_url}{href}")
        return links
    
    def _parse_movie_page(self, soup: BeautifulSoup, url: str) -> MovieMetadata:
        """Parse movie page to extract metadata."""
        # Extract metadata from the page
        title = self._extract_title(soup)
        actresses = self._extract_actresses(soup)
        # ... extract other fields
        
        return MovieMetadata(
            code=self._extract_code(soup),
            title=title,
            actresses=actresses,
            # ... other fields
            source_url=url
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract movie title from page."""
        title_elem = soup.find('h1', class_='movie-title')
        return title_elem.text.strip() if title_elem else ""
    
    def _extract_actresses(self, soup: BeautifulSoup) -> List[str]:
        """Extract actress names from page."""
        actresses = []
        for actress_elem in soup.find_all('a', class_='actress-link'):
            actresses.append(actress_elem.text.strip())
        return actresses
```

### Step 2: Register Scraper

Update `src/scrapers/scraper_factory.py`:

```python
from .yoursite_scraper import YourSiteScraper

class ScraperFactory:
    @staticmethod
    def create_scraper(scraper_type: str, config: Config) -> BaseScraper:
        if scraper_type == "javdb":
            return JavDBScraper(config)
        elif scraper_type == "javlibrary":
            return JavLibraryScraper(config)
        elif scraper_type == "yoursite":  # Add this
            return YourSiteScraper(config)
        else:
            raise ValueError(f"Unknown scraper type: {scraper_type}")
```

### Step 3: Add Tests

Create `tests/test_yoursite_scraper.py`:

```python
import pytest
from unittest.mock import AsyncMock, Mock
from src.scrapers.yoursite_scraper import YourSiteScraper
from src.models.config import Config

@pytest.fixture
def config():
    return Config(
        source_directory="/test/source",
        target_directory="/test/target"
    )

@pytest.fixture
def scraper(config):
    return YourSiteScraper(config)

@pytest.mark.asyncio
async def test_search_movie_success(scraper):
    """Test successful movie search."""
    # Mock HTTP response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <body>
            <a class="movie-link" href="/movie/123">Test Movie</a>
        </body>
    </html>
    """
    
    scraper._http_client.get = AsyncMock(return_value=mock_response)
    
    # Test search
    result = await scraper.search_movie("TEST-001")
    
    assert result is not None
    assert result.code == "TEST-001"

@pytest.mark.asyncio
async def test_is_available(scraper):
    """Test availability check."""
    mock_response = Mock()
    mock_response.status_code = 200
    
    scraper._http_client.get = AsyncMock(return_value=mock_response)
    
    result = await scraper.is_available()
    assert result is True
```

### Step 4: Update Configuration

Add the new scraper to configuration examples:

```yaml
# In config.yaml.example
scraping:
  priority: ["javdb", "javlibrary", "yoursite"]  # Add yoursite
```

### Step 5: Update Documentation

Update relevant documentation files:
- Add scraper description to README.md
- Update API documentation
- Add configuration examples

## Testing

### Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── fixtures/                # Test data and fixtures
│   ├── __init__.py
│   └── mock_data.py        # Mock HTML responses, test data
├── integration/             # Integration tests
│   ├── __init__.py
│   └── test_end_to_end.py  # Full workflow tests
├── performance/             # Performance tests
│   ├── __init__.py
│   └── test_performance.py # Load and performance tests
├── test_*.py               # Unit tests for each module
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_file_scanner.py

# Run specific test
pytest tests/test_file_scanner.py::test_scan_directory

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/

# Run performance tests
pytest tests/performance/
```

### Test Categories

#### Unit Tests
Test individual components in isolation:

```python
@pytest.mark.asyncio
async def test_file_scanner_finds_video_files():
    """Test that file scanner correctly identifies video files."""
    scanner = FileScanner(['.mp4', '.mkv'])
    
    # Mock file system
    with patch('pathlib.Path.iterdir') as mock_iterdir:
        mock_iterdir.return_value = [
            Mock(name='video1.mp4', is_file=lambda: True),
            Mock(name='video2.mkv', is_file=lambda: True),
            Mock(name='document.txt', is_file=lambda: True),
        ]
        
        files = await scanner.scan_directory(Path('/test'))
        
        assert len(files) == 2
        assert all(f.extension in ['.mp4', '.mkv'] for f in files)
```

#### Integration Tests
Test component interactions:

```python
@pytest.mark.asyncio
async def test_full_processing_workflow():
    """Test complete file processing workflow."""
    # Setup test environment
    config = create_test_config()
    app = AVMetadataScraper(config)
    
    # Create test files
    create_test_video_files()
    
    # Run processing
    result = await app.process_files()
    
    # Verify results
    assert result.processed_count > 0
    assert result.error_count == 0
    
    # Verify file organization
    verify_organized_files()
```

#### Performance Tests
Test performance characteristics:

```python
@pytest.mark.performance
def test_concurrent_processing_performance():
    """Test performance with concurrent file processing."""
    import time
    
    start_time = time.time()
    
    # Process multiple files concurrently
    result = process_test_files(concurrent=True)
    
    concurrent_time = time.time() - start_time
    
    # Process same files sequentially
    start_time = time.time()
    result = process_test_files(concurrent=False)
    sequential_time = time.time() - start_time
    
    # Concurrent should be faster
    assert concurrent_time < sequential_time * 0.8
```

### Test Fixtures

Create reusable test data in `tests/fixtures/mock_data.py`:

```python
# Mock HTML responses for scrapers
JAVDB_SEARCH_RESPONSE = """
<html>
    <body>
        <div class="movie-list">
            <a href="/v/abc123" class="box">
                <div class="uid">ABC-123</div>
                <div class="video-title">Test Movie Title</div>
            </a>
        </div>
    </body>
</html>
"""

JAVDB_MOVIE_RESPONSE = """
<html>
    <body>
        <h2 class="title">Test Movie Title</h2>
        <div class="panel-block">
            <strong>演員:</strong>
            <a href="/actors/123">Test Actress</a>
        </div>
        <img class="video-cover" src="/covers/abc123.jpg">
    </body>
</html>
"""

# Test configuration
def create_test_config():
    return Config(
        source_directory=Path("/tmp/test_source"),
        target_directory=Path("/tmp/test_target"),
        max_concurrent_files=1,
        headless_browser=True
    )

# Test video files
def create_test_video_files(directory: Path):
    """Create test video files for testing."""
    test_files = [
        "ABC-123.mp4",
        "DEF-456.mkv",
        "GHI-789.avi"
    ]
    
    for filename in test_files:
        file_path = directory / filename
        file_path.write_bytes(b"fake video content")
```

## Code Style

### Python Style Guide

Follow PEP 8 with these specific guidelines:

#### Formatting
- Use Black for code formatting
- Line length: 88 characters (Black default)
- Use double quotes for strings
- Use trailing commas in multi-line structures

#### Imports
- Use isort with Black profile
- Group imports: standard library, third-party, local
- Use absolute imports when possible

```python
# Standard library
import asyncio
import logging
from pathlib import Path
from typing import List, Optional

# Third-party
import aiohttp
from bs4 import BeautifulSoup

# Local
from ..models.config import Config
from ..utils.logging_config import get_logger
```

#### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

#### Type Hints
Use type hints for all public methods:

```python
from typing import List, Optional, Dict, Any

async def process_files(
    self, 
    source_dir: Optional[Path] = None,
    target_dir: Optional[Path] = None
) -> ProcessingResult:
    """Process video files with type hints."""
    pass
```

#### Documentation
Use Google-style docstrings:

```python
def extract_code_from_filename(self, filename: str) -> Optional[str]:
    """
    Extract video code from filename using pattern matching.
    
    Args:
        filename: The video filename to analyze
        
    Returns:
        The extracted video code, or None if no code found
        
    Raises:
        ValueError: If filename is empty or invalid
        
    Example:
        >>> scanner.extract_code_from_filename("ABC-123.mp4")
        "ABC-123"
    """
    pass
```

### Configuration Files

#### Pre-commit Configuration (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
```

#### PyProject Configuration (`pyproject.toml`)

```toml
[tool.black]
line-length = 88
target-version = ['py39']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["src"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short --strict-markers"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "performance: marks tests as performance tests",
]
```

## Debugging

### Logging Configuration

Use structured logging throughout the application:

```python
import logging
from ..utils.logging_config import get_logger

class YourClass:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def some_method(self):
        self.logger.info("Starting operation", extra={
            "operation": "some_method",
            "context": {"key": "value"}
        })
        
        try:
            # Your code here
            pass
        except Exception as e:
            self.logger.error("Operation failed", extra={
                "operation": "some_method",
                "error": str(e),
                "error_type": type(e).__name__
            }, exc_info=True)
```

### Debug Mode

Enable debug mode for detailed logging:

```python
# In config.yaml
logging:
  level: "DEBUG"

# Or via environment variable
DEBUG_MODE=true
```

### Browser Debugging

For scraper debugging, disable headless mode:

```python
# In config.yaml
browser:
  headless: false
  
# Enable Chrome DevTools
chrome_options:
  - "--remote-debugging-port=9222"
```

Access DevTools at `http://localhost:9222`

### Performance Profiling

Use cProfile for performance analysis:

```bash
# Profile the application
python -m cProfile -o profile.stats main.py

# Analyze results
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats(20)
"
```

### Memory Debugging

Use memory_profiler for memory analysis:

```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
python -m memory_profiler main.py

# Line-by-line profiling
@profile
def your_function():
    # Your code here
    pass
```

## Performance Optimization

### Async/Await Best Practices

1. **Use async for I/O operations:**
   ```python
   async def fetch_data(self, url: str) -> str:
       async with aiohttp.ClientSession() as session:
           async with session.get(url) as response:
               return await response.text()
   ```

2. **Batch operations:**
   ```python
   async def process_multiple_files(self, files: List[Path]) -> List[Result]:
       tasks = [self.process_file(file) for file in files]
       return await asyncio.gather(*tasks, return_exceptions=True)
   ```

3. **Use semaphores for concurrency control:**
   ```python
   async def controlled_processing(self, files: List[Path]) -> None:
       semaphore = asyncio.Semaphore(self.config.max_concurrent_files)
       
       async def process_with_semaphore(file: Path):
           async with semaphore:
               return await self.process_file(file)
       
       tasks = [process_with_semaphore(file) for file in files]
       await asyncio.gather(*tasks)
   ```

### Caching Strategies

1. **In-memory caching:**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def expensive_operation(self, input_data: str) -> str:
       # Expensive computation
       return result
   ```

2. **Async caching:**
   ```python
   import asyncio
   from typing import Dict, Any
   
   class AsyncCache:
       def __init__(self, max_size: int = 1000):
           self._cache: Dict[str, Any] = {}
           self._max_size = max_size
       
       async def get_or_compute(self, key: str, compute_func):
           if key in self._cache:
               return self._cache[key]
           
           result = await compute_func()
           
           if len(self._cache) >= self._max_size:
               # Remove oldest entry
               oldest_key = next(iter(self._cache))
               del self._cache[oldest_key]
           
           self._cache[key] = result
           return result
   ```

### Database Optimization

For future database integration:

1. **Use connection pooling**
2. **Implement batch operations**
3. **Add database indexes**
4. **Use prepared statements**

### Resource Management

1. **Context managers for resources:**
   ```python
   from contextlib import asynccontextmanager
   
   @asynccontextmanager
   async def managed_webdriver():
       driver = None
       try:
           driver = create_webdriver()
           yield driver
       finally:
           if driver:
               driver.quit()
   ```

2. **Cleanup on shutdown:**
   ```python
   import atexit
   import signal
   
   class Application:
       def __init__(self):
           self.resources = []
           atexit.register(self.cleanup)
           signal.signal(signal.SIGTERM, self._signal_handler)
       
       def cleanup(self):
           for resource in self.resources:
               resource.close()
       
       def _signal_handler(self, signum, frame):
           self.cleanup()
           sys.exit(0)
   ```

## Release Process

### Version Management

Use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Update version numbers:**
   ```bash
   # Update version in setup.py, __init__.py, etc.
   ```

2. **Update CHANGELOG.md:**
   ```markdown
   ## [1.2.0] - 2023-12-01
   
   ### Added
   - New scraper for example.com
   - Configuration validation
   
   ### Changed
   - Improved error handling
   
   ### Fixed
   - Fixed memory leak in image downloader
   ```

3. **Run full test suite:**
   ```bash
   pytest tests/
   pytest tests/integration/
   pytest tests/performance/
   ```

4. **Build and test Docker image:**
   ```bash
   docker build -t av-metadata-scraper:latest .
   docker run --rm av-metadata-scraper:latest --version
   ```

5. **Create release:**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

6. **Build distribution packages:**
   ```bash
   python setup.py sdist bdist_wheel
   ```

7. **Update documentation:**
   - Update README.md
   - Update API documentation
   - Update user guide

### Continuous Integration

Example GitHub Actions workflow (`.github/workflows/ci.yml`):

```yaml
name: CI

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
    
    - name: Lint with flake8
      run: |
        flake8 src/ tests/
    
    - name: Check formatting with black
      run: |
        black --check src/ tests/
    
    - name: Check imports with isort
      run: |
        isort --check-only src/ tests/
    
    - name: Type check with mypy
      run: |
        mypy src/
    
    - name: Test with pytest
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  docker:
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
```

---

This developer guide provides comprehensive information for contributing to the AV Metadata Scraper project. For questions or clarifications, please create an issue in the project repository.