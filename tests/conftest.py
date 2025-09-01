"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import asyncio
import logging
from pathlib import Path
from unittest.mock import Mock, patch

from tests.fixtures.mock_data import MockDataGenerator, create_test_environment


# Configure logging for tests
logging.getLogger().setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_environment(temp_directory):
    """Create a complete test environment with files and configuration."""
    return create_test_environment(temp_directory, file_count=10)


@pytest.fixture
def mock_video_files():
    """Generate mock video files for testing."""
    return MockDataGenerator.generate_video_file_batch(5)


@pytest.fixture
def mock_metadata():
    """Generate mock metadata for testing."""
    return MockDataGenerator.generate_metadata_batch(5)


@pytest.fixture
def mock_config(temp_directory):
    """Generate mock configuration."""
    source_dir = temp_directory / "source"
    target_dir = temp_directory / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    
    return MockDataGenerator.create_mock_config(str(source_dir), str(target_dir))


@pytest.fixture
def mock_scrapers():
    """Mock scrapers that return test data."""
    async def mock_scrape_metadata(code: str):
        if code.startswith('FAIL'):
            return None
        return MockDataGenerator.generate_movie_metadata(code=code)
    
    return mock_scrape_metadata


@pytest.fixture
def mock_image_downloader():
    """Mock image downloader."""
    async def mock_download(metadata, target_dir):
        # Create fake image files
        cover_file = target_dir / f"{metadata.code}_cover.jpg"
        cover_file.parent.mkdir(parents=True, exist_ok=True)
        cover_file.write_bytes(b"fake image data")
        
        return {
            'success': True,
            'downloaded_files': [str(cover_file)],
            'total_size': 1024
        }
    
    return mock_download


@pytest.fixture(autouse=True)
def disable_network_requests():
    """Disable actual network requests during tests."""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post, \
         patch('aiohttp.ClientSession.get') as mock_aiohttp_get:
        
        # Configure mock responses
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = "<html><body>Mock response</body></html>"
        mock_post.return_value.status_code = 200
        
        yield {
            'requests_get': mock_get,
            'requests_post': mock_post,
            'aiohttp_get': mock_aiohttp_get
        }


@pytest.fixture
def mock_webdriver():
    """Mock Selenium WebDriver."""
    with patch('selenium.webdriver.Chrome') as mock_chrome:
        driver_mock = Mock()
        driver_mock.get.return_value = None
        driver_mock.find_element.return_value = Mock()
        driver_mock.find_elements.return_value = []
        driver_mock.page_source = "<html><body>Mock page</body></html>"
        driver_mock.current_url = "https://example.com"
        
        mock_chrome.return_value = driver_mock
        
        yield driver_mock


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests"
    )
    config.addinivalue_line(
        "markers", "load: Load tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )
    config.addinivalue_line(
        "markers", "network: Tests that require network access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "test_" in str(item.fspath) and "integration" not in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Mark slow tests
        if "load" in item.name or "performance" in item.name:
            item.add_marker(pytest.mark.slow)


# Custom assertions
def assert_video_file_valid(video_file):
    """Assert that a VideoFile object is valid."""
    assert video_file.file_path is not None
    assert video_file.filename is not None
    assert video_file.extension in ['.mp4', '.mkv', '.avi', '.wmv', '.mov']
    assert video_file.file_size >= 0


def assert_metadata_valid(metadata):
    """Assert that a MovieMetadata object is valid."""
    assert metadata.code is not None
    assert metadata.title is not None
    assert len(metadata.actresses) > 0
    assert metadata.source_url is not None


# Add custom assertions to pytest namespace
pytest.assert_video_file_valid = assert_video_file_valid
pytest.assert_metadata_valid = assert_metadata_valid