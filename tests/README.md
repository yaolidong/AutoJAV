# AV Metadata Scraper Test Suite

This directory contains the comprehensive test suite for the AV Metadata Scraper project. The test suite is designed to ensure code quality, functionality, performance, and reliability.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── fixtures/                # Test data and mock objects
│   ├── __init__.py
│   └── mock_data.py        # Mock data generators
├── integration/             # End-to-end integration tests
│   ├── __init__.py
│   └── test_end_to_end.py  # Complete workflow tests
├── performance/             # Performance and load tests
│   ├── __init__.py
│   └── test_performance.py # Performance benchmarks
├── test_*.py               # Unit tests for individual components
└── README.md               # This file
```

## Test Categories

### Unit Tests
- **Location**: `tests/test_*.py`
- **Purpose**: Test individual components in isolation
- **Marker**: `@pytest.mark.unit`
- **Coverage**: All core functionality, edge cases, error handling

### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test complete workflows and component interactions
- **Marker**: `@pytest.mark.integration`
- **Coverage**: End-to-end scenarios, configuration validation, error recovery

### Performance Tests
- **Location**: `tests/performance/`
- **Purpose**: Validate system performance under various conditions
- **Marker**: `@pytest.mark.performance`
- **Coverage**: Throughput, memory usage, concurrency, scalability

### Load Tests
- **Location**: `tests/performance/`
- **Purpose**: Test system behavior under high load
- **Marker**: `@pytest.mark.load`
- **Coverage**: Sustained load, burst scenarios, resource limits

## Running Tests

### Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install system dependencies (for Selenium tests):
```bash
# Ubuntu/Debian
sudo apt-get install -y google-chrome-stable

# macOS
brew install --cask google-chrome
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run performance tests only
pytest -m performance

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_file_scanner.py

# Run specific test function
pytest tests/test_file_scanner.py::TestFileScanner::test_scan_directory_success
```

### Using the Test Runner Script

The project includes a comprehensive test runner script:

```bash
# Run unit tests with coverage
python scripts/run_tests.py unit --coverage

# Run integration tests
python scripts/run_tests.py integration

# Run performance tests
python scripts/run_tests.py performance

# Run all tests
python scripts/run_tests.py all --verbose

# Run code quality checks
python scripts/run_tests.py quality

# Generate comprehensive report
python scripts/run_tests.py report

# Run full CI pipeline
python scripts/run_tests.py ci
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings
- Markers definition
- Warning filters

### Coverage Configuration (`.coveragerc`)
- Source code paths
- Exclusion patterns
- Report formats
- Minimum coverage thresholds

### Fixtures (`conftest.py`)
- Shared test fixtures
- Mock configurations
- Test environment setup
- Custom assertions

## Mock Data and Fixtures

### MockDataGenerator
The `MockDataGenerator` class provides realistic test data:

```python
from tests.fixtures.mock_data import MockDataGenerator

# Generate mock video files
video_files = MockDataGenerator.generate_video_file_batch(10)

# Generate mock metadata
metadata = MockDataGenerator.generate_movie_metadata(code="SSIS-001")

# Create test environment
test_env = MockDataGenerator.generate_test_directory_structure(base_path, 50)
```

### Available Fixtures
- `temp_directory`: Temporary directory for tests
- `test_environment`: Complete test environment with files and config
- `mock_video_files`: Sample video file objects
- `mock_metadata`: Sample metadata objects
- `mock_scrapers`: Mock scraper functions
- `mock_image_downloader`: Mock image download functionality

## Test Markers

Use pytest markers to categorize and run specific test types:

```python
@pytest.mark.unit
def test_unit_functionality():
    """Unit test example."""
    pass

@pytest.mark.integration
def test_integration_workflow():
    """Integration test example."""
    pass

@pytest.mark.performance
def test_performance_benchmark():
    """Performance test example."""
    pass

@pytest.mark.slow
def test_long_running_operation():
    """Slow test that may be skipped in quick runs."""
    pass

@pytest.mark.network
def test_network_dependent():
    """Test requiring network access."""
    pass
```

## Performance Testing

### Benchmarks Included
- File scanning performance (1000+ files)
- Metadata scraping throughput
- Memory usage monitoring
- Concurrent processing efficiency
- Cache performance
- Startup/shutdown times

### Performance Assertions
Tests include performance assertions to catch regressions:

```python
# File scanning should process 100+ files per second
assert files_per_second > 100

# Memory usage should not exceed limits
assert memory_increase < 500  # MB

# Cache retrieval should be fast
assert avg_cache_time < 0.001  # 1ms
```

## Continuous Integration

### GitHub Actions Workflow
The project includes a comprehensive CI/CD pipeline:

1. **Code Quality**: flake8, mypy, isort, black
2. **Unit Tests**: Multi-Python version testing with coverage
3. **Integration Tests**: End-to-end workflow validation
4. **Performance Tests**: Scheduled performance monitoring
5. **Security Scan**: Safety and bandit security checks
6. **Docker Tests**: Container integration testing

### Coverage Requirements
- Minimum coverage: 80%
- Coverage reports: HTML, XML, terminal
- Coverage uploaded to Codecov

## Writing New Tests

### Unit Test Example
```python
import pytest
from src.scanner.file_scanner import FileScanner

class TestFileScanner:
    def test_scan_directory_success(self, temp_directory):
        """Test successful directory scanning."""
        # Create test files
        (temp_directory / "test.mp4").touch()
        
        # Test scanning
        scanner = FileScanner(str(temp_directory), ['.mp4'])
        results = scanner.scan_directory()
        
        # Assertions
        assert len(results) == 1
        assert results[0].filename == "test.mp4"
```

### Integration Test Example
```python
@pytest.mark.asyncio
async def test_complete_processing_pipeline(test_environment):
    """Test complete processing from scan to organization."""
    env = test_environment
    
    # Mock external dependencies
    with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata'):
        app = AVMetadataScraper(str(env['config_file']))
        
        # Run processing
        await app.start()
        await asyncio.sleep(2)
        await app.stop()
        
        # Verify results
        stats = app.get_status()['processing_stats']
        assert stats['files_processed'] > 0
```

### Performance Test Example
```python
@pytest.mark.performance
def test_file_scanning_performance(large_file_set):
    """Test file scanning performance with large dataset."""
    scanner = FileScanner(str(large_file_set['source_dir']), ['.mp4'])
    
    start_time = time.time()
    results = scanner.scan_directory()
    scan_time = time.time() - start_time
    
    # Performance assertions
    files_per_second = len(results) / scan_time
    assert files_per_second > 100
```

## Test Data Management

### Mock Data Guidelines
- Use realistic but fake data
- Avoid real personal information
- Include edge cases and error conditions
- Maintain consistency across tests

### Test File Management
- Use temporary directories for file operations
- Clean up resources after tests
- Mock network requests to avoid external dependencies
- Use fixtures for common test data

## Debugging Tests

### Running Tests in Debug Mode
```bash
# Run with detailed output
pytest -v -s

# Run with Python debugger
pytest --pdb

# Run specific test with debugging
pytest tests/test_file_scanner.py::test_specific_function -v -s --pdb
```

### Common Issues
1. **Import Errors**: Ensure PYTHONPATH includes project root
2. **Async Test Issues**: Use `@pytest.mark.asyncio` for async tests
3. **Mock Issues**: Verify mock patches target correct modules
4. **File Permission Issues**: Use temporary directories with proper permissions

## Contributing to Tests

### Test Guidelines
1. Write tests for all new functionality
2. Maintain or improve code coverage
3. Include both positive and negative test cases
4. Use descriptive test names and docstrings
5. Follow existing test patterns and conventions

### Code Review Checklist
- [ ] Tests cover new functionality
- [ ] Tests include error cases
- [ ] Performance impact considered
- [ ] Mock dependencies appropriately
- [ ] Tests are deterministic and reliable
- [ ] Documentation updated if needed

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Async Testing with Pytest](https://pytest-asyncio.readthedocs.io/)