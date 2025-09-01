"""Tests for ImageDownloader."""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import date

from src.downloaders.image_downloader import ImageDownloader, ImageType, ImageFormat
from src.models.movie_metadata import MovieMetadata
from src.utils.http_client import HttpClient


class TestImageDownloader:
    """Test cases for ImageDownloader."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client."""
        client = Mock(spec=HttpClient)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client
    
    @pytest.fixture
    def downloader(self, mock_http_client):
        """Create ImageDownloader instance."""
        return ImageDownloader(
            http_client=mock_http_client,
            max_concurrent_downloads=2,
            timeout_seconds=10,
            retry_attempts=1
        )
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample movie metadata with image URLs."""
        return MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            actresses=["Test Actress"],
            cover_url="https://example.com/cover.jpg",
            poster_url="https://example.com/poster.jpg",
            screenshots=[
                "https://example.com/screenshot1.jpg",
                "https://example.com/screenshot2.jpg"
            ]
        )
    
    @pytest.fixture
    def sample_image_data(self):
        """Create sample image data."""
        # Simple 1x1 pixel JPEG data
        return bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01,
            0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0xFF, 0xC4,
            0x00, 0x14, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xDA, 0x00, 0x0C,
            0x03, 0x01, 0x00, 0x02, 0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0x8A, 0xFF, 0xD9
        ])
    
    def test_init_default_params(self):
        """Test ImageDownloader initialization with default parameters."""
        downloader = ImageDownloader()
        
        assert downloader.max_concurrent_downloads == 3
        assert downloader.timeout_seconds == 30
        assert downloader.retry_attempts == 3
        assert downloader.convert_format == ImageFormat.AUTO
        assert downloader.resize_images is False
        assert downloader.create_thumbnails is False
    
    def test_init_custom_params(self, mock_http_client):
        """Test ImageDownloader initialization with custom parameters."""
        downloader = ImageDownloader(
            http_client=mock_http_client,
            max_concurrent_downloads=5,
            timeout_seconds=60,
            retry_attempts=5,
            convert_format=ImageFormat.JPEG,
            resize_images=True,
            max_width=800,
            max_height=600,
            create_thumbnails=True
        )
        
        assert downloader.max_concurrent_downloads == 5
        assert downloader.timeout_seconds == 60
        assert downloader.retry_attempts == 5
        assert downloader.convert_format == ImageFormat.JPEG
        assert downloader.resize_images is True
        assert downloader.max_width == 800
        assert downloader.max_height == 600
        assert downloader.create_thumbnails is True
    
    def test_generate_filename_cover(self, downloader):
        """Test filename generation for cover images."""
        filename = downloader._generate_filename(
            "SSIS-001", ImageType.COVER, "https://example.com/image.jpg"
        )
        
        assert filename == "SSIS-001_cover.jpg"
    
    def test_generate_filename_poster(self, downloader):
        """Test filename generation for poster images."""
        filename = downloader._generate_filename(
            "SSIS-001", ImageType.POSTER, "https://example.com/image.png"
        )
        
        assert filename == "SSIS-001_poster.png"
    
    def test_generate_filename_screenshot(self, downloader):
        """Test filename generation for screenshot images."""
        filename = downloader._generate_filename(
            "SSIS-001", ImageType.SCREENSHOT, "https://example.com/image.jpg", index=3
        )
        
        assert filename == "SSIS-001_screenshot_03.jpg"
    
    def test_generate_filename_no_extension(self, downloader):
        """Test filename generation with no extension in URL."""
        filename = downloader._generate_filename(
            "SSIS-001", ImageType.COVER, "https://example.com/image"
        )
        
        assert filename == "SSIS-001_cover.jpg"  # Default to .jpg
    
    def test_generate_filename_with_format_conversion(self, mock_http_client):
        """Test filename generation with format conversion."""
        downloader = ImageDownloader(
            http_client=mock_http_client,
            convert_format=ImageFormat.PNG
        )
        
        filename = downloader._generate_filename(
            "SSIS-001", ImageType.COVER, "https://example.com/image.jpg"
        )
        
        assert filename == "SSIS-001_cover.png"
    
    @pytest.mark.asyncio
    async def test_fetch_image_data_success(self, downloader, sample_image_data):
        """Test successful image data fetching."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'image/jpeg', 'content-length': str(len(sample_image_data))}
        mock_response.read = AsyncMock(return_value=sample_image_data)
        
        downloader.http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await downloader._fetch_image_data("https://example.com/image.jpg")
        
        assert result == sample_image_data
    
    @pytest.mark.asyncio
    async def test_fetch_image_data_http_error(self, downloader):
        """Test image data fetching with HTTP error."""
        # Mock HTTP response with error
        mock_response = Mock()
        mock_response.status = 404
        
        downloader.http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await downloader._fetch_image_data("https://example.com/image.jpg")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_image_data_invalid_content_type(self, downloader):
        """Test image data fetching with invalid content type."""
        # Mock HTTP response with invalid content type
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html'}
        
        downloader.http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await downloader._fetch_image_data("https://example.com/image.jpg")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_image_data_too_large(self, downloader):
        """Test image data fetching with file too large."""
        # Mock HTTP response with large content length
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {
            'content-type': 'image/jpeg',
            'content-length': str(downloader.max_file_size_bytes + 1)
        }
        
        downloader.http_client.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        
        result = await downloader._fetch_image_data("https://example.com/image.jpg")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_save_image_data(self, downloader, temp_dir, sample_image_data):
        """Test saving image data to file."""
        target_path = Path(temp_dir) / "test_image.jpg"
        
        await downloader._save_image_data(sample_image_data, target_path)
        
        assert target_path.exists()
        assert target_path.read_bytes() == sample_image_data
    
    @pytest.mark.asyncio
    async def test_save_image_data_creates_directory(self, downloader, temp_dir, sample_image_data):
        """Test that saving image data creates parent directories."""
        target_path = Path(temp_dir) / "subdir" / "test_image.jpg"
        
        await downloader._save_image_data(sample_image_data, target_path)
        
        assert target_path.exists()
        assert target_path.parent.exists()
    
    @pytest.mark.asyncio
    async def test_download_single_image_success(self, downloader, temp_dir, sample_image_data):
        """Test successful single image download."""
        target_path = Path(temp_dir) / "test_image.jpg"
        
        # Mock fetch_image_data
        downloader._fetch_image_data = AsyncMock(return_value=sample_image_data)
        
        # Mock process_image_data
        downloader._process_image_data = AsyncMock(return_value=sample_image_data)
        
        result = await downloader._download_single_image(
            "https://example.com/image.jpg",
            target_path,
            ImageType.COVER
        )
        
        assert result['success'] is True
        assert result['file_path'] == str(target_path)
        assert result['image_type'] == 'cover'
        assert target_path.exists()
    
    @pytest.mark.asyncio
    async def test_download_single_image_fetch_failure(self, downloader, temp_dir):
        """Test single image download with fetch failure."""
        target_path = Path(temp_dir) / "test_image.jpg"
        
        # Mock fetch_image_data to return None (failure)
        downloader._fetch_image_data = AsyncMock(return_value=None)
        
        result = await downloader._download_single_image(
            "https://example.com/image.jpg",
            target_path,
            ImageType.COVER
        )
        
        assert result['success'] is False
        assert "Failed to download" in result['message']
    
    @pytest.mark.asyncio
    async def test_download_movie_images_success(self, downloader, temp_dir, sample_metadata, sample_image_data):
        """Test successful movie images download."""
        target_directory = Path(temp_dir)
        
        # Mock successful downloads
        downloader._download_single_image = AsyncMock(return_value={
            'success': True,
            'file_path': str(target_directory / "test.jpg"),
            'file_size': len(sample_image_data),
            'image_type': 'cover'
        })
        
        result = await downloader.download_movie_images(sample_metadata, target_directory)
        
        assert result['success'] is True
        assert len(result['downloaded_files']) > 0
        assert result['total_requested'] == 4  # cover + poster + 2 screenshots
    
    @pytest.mark.asyncio
    async def test_download_movie_images_no_urls(self, downloader, temp_dir):
        """Test movie images download with no image URLs."""
        metadata = MovieMetadata(code="TEST", title="Test")
        target_directory = Path(temp_dir)
        
        result = await downloader.download_movie_images(metadata, target_directory)
        
        assert result['success'] is True
        assert result['message'] == "No images available"
        assert len(result['downloaded_files']) == 0
    
    @pytest.mark.asyncio
    async def test_download_movie_images_partial_failure(self, downloader, temp_dir, sample_metadata):
        """Test movie images download with partial failures."""
        target_directory = Path(temp_dir)
        
        # Mock mixed success/failure results
        call_count = 0
        
        async def mock_download(url, path, image_type):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'success': True, 'file_path': str(path)}
            else:
                return {'success': False, 'error': 'Download failed'}
        
        downloader._download_single_image = mock_download
        
        result = await downloader.download_movie_images(sample_metadata, target_directory)
        
        assert result['success'] is True  # At least one succeeded
        assert len(result['downloaded_files']) == 1
        assert len(result['failed_downloads']) == 3
    
    @pytest.mark.asyncio
    async def test_download_movie_images_specific_types(self, downloader, temp_dir, sample_metadata):
        """Test downloading specific image types only."""
        target_directory = Path(temp_dir)
        
        downloader._download_single_image = AsyncMock(return_value={
            'success': True,
            'file_path': str(target_directory / "test.jpg")
        })
        
        # Download only cover images
        result = await downloader.download_movie_images(
            sample_metadata,
            target_directory,
            image_types=[ImageType.COVER]
        )
        
        assert result['success'] is True
        assert result['total_requested'] == 1  # Only cover
    
    def test_get_statistics(self, downloader):
        """Test statistics retrieval."""
        # Modify some statistics
        downloader.stats['images_downloaded'] = 10
        downloader.stats['download_failures'] = 2
        downloader.stats['total_bytes_downloaded'] = 1024 * 1024  # 1MB
        
        stats = downloader.get_statistics()
        
        assert stats['images_downloaded'] == 10
        assert stats['download_failures'] == 2
        assert stats['total_mb_downloaded'] == 1.0
        assert stats['success_rate'] == (10 / 12) * 100  # 10 success out of 12 total
    
    def test_reset_statistics(self, downloader):
        """Test statistics reset."""
        # Set some statistics
        downloader.stats['images_downloaded'] = 5
        downloader.stats['download_failures'] = 2
        
        downloader.reset_statistics()
        
        assert downloader.stats['images_downloaded'] == 0
        assert downloader.stats['download_failures'] == 0
    
    @pytest.mark.asyncio
    async def test_verify_image_integrity_valid(self, downloader, temp_dir):
        """Test image integrity verification with valid image."""
        # Create a simple test image file
        image_path = Path(temp_dir) / "test.jpg"
        
        # Write some basic JPEG header bytes
        with open(image_path, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0')  # JPEG magic bytes
            f.write(b'0' * 100)  # Some content
            f.write(b'\xFF\xD9')  # JPEG end marker
        
        # Mock PIL availability check
        with patch('src.downloaders.image_downloader.PIL_AVAILABLE', False):
            result = await downloader.verify_image_integrity(image_path)
            assert result is True  # Should pass basic file check
    
    @pytest.mark.asyncio
    async def test_verify_image_integrity_invalid(self, downloader, temp_dir):
        """Test image integrity verification with invalid image."""
        image_path = Path(temp_dir) / "invalid.jpg"
        
        # Create empty file
        image_path.touch()
        
        with patch('src.downloaders.image_downloader.PIL_AVAILABLE', False):
            result = await downloader.verify_image_integrity(image_path)
            assert result is False  # Empty file should fail
    
    @pytest.mark.asyncio
    async def test_cleanup_failed_downloads(self, downloader, temp_dir):
        """Test cleanup of failed/corrupted downloads."""
        directory = Path(temp_dir)
        
        # Create test files
        good_image = directory / "good.jpg"
        empty_image = directory / "empty.jpg"
        non_image = directory / "text.txt"
        
        good_image.write_bytes(b"fake image data")
        empty_image.touch()  # Empty file
        non_image.write_text("not an image")
        
        # Mock verify_image_integrity
        async def mock_verify(path):
            return path.name == "good.jpg"
        
        downloader.verify_image_integrity = mock_verify
        
        result = await downloader.cleanup_failed_downloads(directory)
        
        assert result['checked_files'] == 2  # Only .jpg files
        assert len(result['corrupted_files']) == 1
        assert len(result['removed_files']) == 1
        assert not empty_image.exists()  # Should be removed
        assert good_image.exists()  # Should remain
        assert non_image.exists()  # Not checked (not image extension)
    
    def test_create_result(self, downloader):
        """Test result dictionary creation."""
        result = downloader._create_result(True, "Success", {"key": "value"})
        
        assert result['success'] is True
        assert result['message'] == "Success"
        assert 'timestamp' in result
        assert result['key'] == "value"
    
    def test_create_result_no_data(self, downloader):
        """Test result dictionary creation without additional data."""
        result = downloader._create_result(False, "Error")
        
        assert result['success'] is False
        assert result['message'] == "Error"
        assert 'timestamp' in result
        assert len(result) == 3  # Only success, message, timestamp
    
    @pytest.mark.skipif(not hasattr(pytest, 'importorskip'), reason="PIL tests require PIL")
    def test_pil_features_disabled_without_pil(self, mock_http_client):
        """Test that PIL-dependent features are disabled when PIL is not available."""
        with patch('src.downloaders.image_downloader.PIL_AVAILABLE', False):
            downloader = ImageDownloader(
                http_client=mock_http_client,
                resize_images=True,
                convert_format=ImageFormat.JPEG,
                create_thumbnails=True
            )
            
            # Features should be disabled
            assert downloader.resize_images is False
            assert downloader.convert_format == ImageFormat.AUTO
            assert downloader.create_thumbnails is False
    
    @pytest.mark.asyncio
    async def test_process_image_data_no_pil(self, downloader, temp_dir, sample_image_data):
        """Test image processing when PIL is not available."""
        target_path = Path(temp_dir) / "test.jpg"
        
        with patch('src.downloaders.image_downloader.PIL_AVAILABLE', False):
            result = await downloader._process_image_data(
                sample_image_data, target_path, ImageType.COVER
            )
            
            # Should return original data unchanged
            assert result == sample_image_data
    
    def test_determine_output_format_auto(self, downloader):
        """Test output format determination in AUTO mode."""
        # Test various extensions
        test_cases = [
            (Path("test.jpg"), "JPEG"),
            (Path("test.jpeg"), "JPEG"),
            (Path("test.png"), "PNG"),
            (Path("test.webp"), "WEBP"),
            (Path("test.unknown"), "JPEG"),  # Default
        ]
        
        for path, expected in test_cases:
            with patch('src.downloaders.image_downloader.PIL_AVAILABLE', True):
                # Mock image object
                mock_image = Mock()
                result = downloader._determine_output_format(path, mock_image)
                assert result == expected
    
    def test_determine_output_format_specific(self, mock_http_client):
        """Test output format determination with specific format."""
        downloader = ImageDownloader(
            http_client=mock_http_client,
            convert_format=ImageFormat.PNG
        )
        
        with patch('src.downloaders.image_downloader.PIL_AVAILABLE', True):
            mock_image = Mock()
            result = downloader._determine_output_format(Path("test.jpg"), mock_image)
            assert result == "PNG"


if __name__ == "__main__":
    pytest.main([__file__])