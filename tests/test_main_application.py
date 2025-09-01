"""Integration tests for the main application."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date

from src.main_application import AVMetadataScraper, ProcessingStats
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata


class TestProcessingStats:
    """Test cases for ProcessingStats."""
    
    def test_init(self):
        """Test ProcessingStats initialization."""
        stats = ProcessingStats()
        
        assert stats.files_scanned == 0
        assert stats.files_processed == 0
        assert stats.files_organized == 0
        assert stats.metadata_scraped == 0
        assert stats.images_downloaded == 0
        assert stats.errors_encountered == 0
        assert stats.start_time is None
        assert stats.end_time is None
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        start_time = datetime.now()
        end_time = datetime.now()
        
        stats = ProcessingStats(start_time=start_time, end_time=end_time)
        
        assert stats.duration is not None
        assert stats.duration >= 0
    
    def test_duration_no_times(self):
        """Test duration when times are not set."""
        stats = ProcessingStats()
        
        assert stats.duration is None
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = ProcessingStats(files_scanned=10, files_processed=8)
        
        assert stats.success_rate == 80.0
    
    def test_success_rate_no_files(self):
        """Test success rate when no files scanned."""
        stats = ProcessingStats()
        
        assert stats.success_rate == 0.0


class TestAVMetadataScraper:
    """Test cases for AVMetadataScraper."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory with config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create test configuration
            config_data = {
                'logging': {
                    'level': 'INFO',
                    'directory': str(config_dir / 'logs'),
                    'console': True,
                    'file': False  # Disable file logging for tests
                },
                'scanner': {
                    'source_directory': str(config_dir / 'source'),
                    'supported_formats': ['.mp4', '.mkv'],
                    'recursive': True
                },
                'organizer': {
                    'target_directory': str(config_dir / 'target'),
                    'naming_pattern': '{code}.{ext}',
                    'safe_mode': True
                },
                'downloader': {
                    'enabled': False,  # Disable for tests
                    'max_concurrent': 1
                },
                'processing': {
                    'max_concurrent_files': 2
                }
            }
            
            config_file = config_dir / 'config.yaml'
            with open(config_file, 'w') as f:
                import yaml
                yaml.dump(config_data, f)
            
            yield config_file
    
    @pytest.fixture
    def mock_components(self):
        """Mock all external components."""
        with patch.multiple(
            'src.main_application',
            FileScanner=Mock(),
            ScraperFactory=Mock(),
            FileOrganizer=Mock(),
            ImageDownloader=Mock()
        ) as mocks:
            yield mocks
    
    def test_init_with_config(self, temp_config_dir, mock_components):
        """Test initialization with configuration file."""
        app = AVMetadataScraper(temp_config_dir)
        
        assert app.config_manager is not None
        assert app.config is not None
        assert app.is_running is False
        assert app.should_stop is False
        assert isinstance(app.processing_stats, ProcessingStats)
    
    def test_init_without_config(self, mock_components):
        """Test initialization without configuration file."""
        with patch('src.main_application.ConfigManager') as mock_config_manager:
            mock_config_manager.return_value.get_config.return_value = {
                'logging': {},
                'scanner': {},
                'organizer': {},
                'downloader': {},
                'processing': {}
            }
            
            app = AVMetadataScraper()
            
            assert app.config_manager is not None
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self, temp_config_dir, mock_components):
        """Test application start and stop."""
        # Mock file scanner to return no files
        mock_components['FileScanner'].return_value.scan_files.return_value = []
        
        app = AVMetadataScraper(temp_config_dir)
        
        # Mock the processing pipeline to avoid actual processing
        app._run_processing_pipeline = AsyncMock()
        
        # Start application
        start_task = asyncio.create_task(app.start())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        assert app.is_running is True
        
        # Stop application
        await app.stop()
        
        # Wait for start task to complete
        await start_task
        
        assert app.is_running is False
    
    @pytest.mark.asyncio
    async def test_scan_files_success(self, temp_config_dir, mock_components):
        """Test successful file scanning."""
        # Create test video files
        test_files = [
            VideoFile(
                file_path="/test/movie1.mp4",
                filename="movie1.mp4",
                file_size=1000,
                extension=".mp4",
                detected_code="SSIS-001"
            ),
            VideoFile(
                file_path="/test/movie2.mkv",
                filename="movie2.mkv",
                file_size=2000,
                extension=".mkv",
                detected_code="SSIS-002"
            )
        ]
        
        mock_components['FileScanner'].return_value.scan_files.return_value = test_files
        
        app = AVMetadataScraper(temp_config_dir)
        
        result = await app._scan_files()
        
        assert len(result) == 2
        assert app.processing_stats.files_scanned == 2
    
    @pytest.mark.asyncio
    async def test_scan_files_no_files(self, temp_config_dir, mock_components):
        """Test file scanning when no files found."""
        mock_components['FileScanner'].return_value.scan_files.return_value = []
        
        app = AVMetadataScraper(temp_config_dir)
        
        result = await app._scan_files()
        
        assert len(result) == 0
        assert app.processing_stats.files_scanned == 0
    
    @pytest.mark.asyncio
    async def test_scan_files_error(self, temp_config_dir, mock_components):
        """Test file scanning with error."""
        mock_components['FileScanner'].return_value.scan_files.side_effect = Exception("Scan error")
        
        app = AVMetadataScraper(temp_config_dir)
        
        result = await app._scan_files()
        
        assert len(result) == 0
        assert app.processing_stats.files_scanned == 0
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_success(self, temp_config_dir, mock_components):
        """Test successful metadata scraping."""
        # Mock metadata scraper
        mock_metadata = MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            actresses=["Test Actress"]
        )
        
        mock_scraper = Mock()
        mock_scraper.scrape_metadata = AsyncMock(return_value=mock_metadata)
        mock_components['ScraperFactory'].return_value.create_metadata_scraper.return_value = mock_scraper
        
        app = AVMetadataScraper(temp_config_dir)
        
        video_file = VideoFile(
            file_path="/test/movie.mp4",
            filename="movie.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code="SSIS-001"
        )
        
        result = await app._scrape_metadata(video_file)
        
        assert result is not None
        assert result.code == "SSIS-001"
        assert result.title == "Test Movie"
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_no_code(self, temp_config_dir, mock_components):
        """Test metadata scraping when no code detected."""
        app = AVMetadataScraper(temp_config_dir)
        
        video_file = VideoFile(
            file_path="/test/movie.mp4",
            filename="movie.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code=None  # No code detected
        )
        
        result = await app._scrape_metadata(video_file)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_scrape_metadata_scraper_error(self, temp_config_dir, mock_components):
        """Test metadata scraping with scraper error."""
        # Mock metadata scraper to raise exception
        mock_scraper = Mock()
        mock_scraper.scrape_metadata = AsyncMock(side_effect=Exception("Scraper error"))
        mock_components['ScraperFactory'].return_value.create_metadata_scraper.return_value = mock_scraper
        
        app = AVMetadataScraper(temp_config_dir)
        
        video_file = VideoFile(
            file_path="/test/movie.mp4",
            filename="movie.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code="SSIS-001"
        )
        
        result = await app._scrape_metadata(video_file)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_organize_file_success(self, temp_config_dir, mock_components):
        """Test successful file organization."""
        # Mock file organizer
        mock_organizer = Mock()
        mock_organizer.organize_file.return_value = {
            'success': True,
            'details': {'target_path': '/target/movie.mp4'}
        }
        mock_components['FileOrganizer'].return_value = mock_organizer
        
        app = AVMetadataScraper(temp_config_dir)
        
        video_file = VideoFile(
            file_path="/test/movie.mp4",
            filename="movie.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code="SSIS-001"
        )
        
        metadata = MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            actresses=["Test Actress"]
        )
        
        result = await app._organize_file(video_file, metadata)
        
        assert result['success'] is True
        assert 'target_path' in result['details']
    
    @pytest.mark.asyncio
    async def test_organize_file_error(self, temp_config_dir, mock_components):
        """Test file organization with error."""
        # Mock file organizer to raise exception
        mock_organizer = Mock()
        mock_organizer.organize_file.side_effect = Exception("Organization error")
        mock_components['FileOrganizer'].return_value = mock_organizer
        
        app = AVMetadataScraper(temp_config_dir)
        
        video_file = VideoFile(
            file_path="/test/movie.mp4",
            filename="movie.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code="SSIS-001"
        )
        
        metadata = MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            actresses=["Test Actress"]
        )
        
        result = await app._organize_file(video_file, metadata)
        
        assert result['success'] is False
        assert 'Organization error' in result['message']
    
    @pytest.mark.asyncio
    async def test_download_images_success(self, temp_config_dir, mock_components):
        """Test successful image downloading."""
        # Mock image downloader
        mock_downloader = Mock()
        mock_downloader.download_movie_images = AsyncMock(return_value={
            'success': True,
            'downloaded_files': ['cover.jpg', 'poster.jpg']
        })
        mock_components['ImageDownloader'].return_value = mock_downloader
        
        app = AVMetadataScraper(temp_config_dir)
        
        metadata = MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            cover_url="https://example.com/cover.jpg"
        )
        
        target_dir = Path("/target")
        
        await app._download_images(metadata, target_dir)
        
        assert app.processing_stats.images_downloaded == 2
    
    @pytest.mark.asyncio
    async def test_download_images_disabled(self, temp_config_dir, mock_components):
        """Test image downloading when disabled."""
        app = AVMetadataScraper(temp_config_dir)
        
        # Disable image downloading in config
        app.config['downloader']['enabled'] = False
        
        metadata = MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            cover_url="https://example.com/cover.jpg"
        )
        
        target_dir = Path("/target")
        
        await app._download_images(metadata, target_dir)
        
        # Should not download anything
        assert app.processing_stats.images_downloaded == 0
    
    @pytest.mark.asyncio
    async def test_process_single_file_complete_success(self, temp_config_dir, mock_components):
        """Test complete single file processing success."""
        # Mock all components for success
        mock_metadata = MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            actresses=["Test Actress"]
        )
        
        mock_scraper = Mock()
        mock_scraper.scrape_metadata = AsyncMock(return_value=mock_metadata)
        mock_components['ScraperFactory'].return_value.create_metadata_scraper.return_value = mock_scraper
        
        mock_organizer = Mock()
        mock_organizer.organize_file.return_value = {
            'success': True,
            'details': {'target_path': '/target/SSIS-001.mp4'}
        }
        mock_components['FileOrganizer'].return_value = mock_organizer
        
        mock_downloader = Mock()
        mock_downloader.download_movie_images = AsyncMock(return_value={
            'success': True,
            'downloaded_files': ['cover.jpg']
        })
        mock_components['ImageDownloader'].return_value = mock_downloader
        
        app = AVMetadataScraper(temp_config_dir)
        
        video_file = VideoFile(
            file_path="/test/SSIS-001.mp4",
            filename="SSIS-001.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code="SSIS-001"
        )
        
        await app._process_single_file(video_file, "test-worker")
        
        assert app.processing_stats.files_processed == 1
        assert app.processing_stats.metadata_scraped == 1
        assert app.processing_stats.files_organized == 1
        assert app.processing_stats.images_downloaded == 1
        assert app.processing_stats.errors_encountered == 0
    
    @pytest.mark.asyncio
    async def test_process_single_file_no_metadata(self, temp_config_dir, mock_components):
        """Test single file processing when no metadata found."""
        # Mock scraper to return no metadata
        mock_scraper = Mock()
        mock_scraper.scrape_metadata = AsyncMock(return_value=None)
        mock_components['ScraperFactory'].return_value.create_metadata_scraper.return_value = mock_scraper
        
        app = AVMetadataScraper(temp_config_dir)
        
        video_file = VideoFile(
            file_path="/test/movie.mp4",
            filename="movie.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code="UNKNOWN-001"
        )
        
        await app._process_single_file(video_file, "test-worker")
        
        assert app.processing_stats.files_processed == 0
        assert app.processing_stats.errors_encountered == 1
    
    def test_get_status(self, temp_config_dir, mock_components):
        """Test getting application status."""
        app = AVMetadataScraper(temp_config_dir)
        
        # Set some processing stats
        app.processing_stats.files_scanned = 10
        app.processing_stats.files_processed = 8
        app.processing_stats.errors_encountered = 2
        
        status = app.get_status()
        
        assert status['is_running'] is False
        assert status['processing_stats']['files_scanned'] == 10
        assert status['processing_stats']['files_processed'] == 8
        assert status['processing_stats']['errors_encountered'] == 2
        assert status['processing_stats']['success_rate'] == 80.0
        assert 'active_tasks' in status
        assert 'queue_size' in status
        assert 'progress' in status
        assert 'component_stats' in status
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, temp_config_dir, mock_components):
        """Test health check when all components are healthy."""
        # Mock healthy components
        mock_scraper = Mock()
        mock_scraper.health_check = AsyncMock(return_value={'all_scrapers': 'healthy'})
        mock_components['ScraperFactory'].return_value.create_metadata_scraper.return_value = mock_scraper
        
        mock_organizer = Mock()
        mock_organizer.validate_target_directory.return_value = {'valid': True, 'errors': []}
        mock_components['FileOrganizer'].return_value = mock_organizer
        
        app = AVMetadataScraper(temp_config_dir)
        
        # Mock config validation
        app.config_manager.validate_config = Mock(return_value={'errors': [], 'warnings': []})
        
        health = await app.health_check()
        
        assert health['status'] == 'healthy'
        assert 'components' in health
        assert 'scrapers' in health['components']
        assert 'organizer' in health['components']
        assert 'configuration' in health['components']
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, temp_config_dir, mock_components):
        """Test health check when some components have issues."""
        # Mock components with issues
        mock_scraper = Mock()
        mock_scraper.health_check = AsyncMock(return_value={'errors': ['scraper error']})
        mock_components['ScraperFactory'].return_value.create_metadata_scraper.return_value = mock_scraper
        
        mock_organizer = Mock()
        mock_organizer.validate_target_directory.return_value = {
            'valid': False, 
            'errors': ['Directory not writable']
        }
        mock_components['FileOrganizer'].return_value = mock_organizer
        
        app = AVMetadataScraper(temp_config_dir)
        
        # Mock config validation
        app.config_manager.validate_config = Mock(return_value={'errors': [], 'warnings': []})
        
        health = await app.health_check()
        
        assert health['status'] == 'degraded'
        assert 'issues' in health
    
    @pytest.mark.asyncio
    async def test_health_check_exception(self, temp_config_dir, mock_components):
        """Test health check when exception occurs."""
        # Mock scraper to raise exception
        mock_scraper = Mock()
        mock_scraper.health_check = AsyncMock(side_effect=Exception("Health check error"))
        mock_components['ScraperFactory'].return_value.create_metadata_scraper.return_value = mock_scraper
        
        app = AVMetadataScraper(temp_config_dir)
        
        health = await app.health_check()
        
        assert health['status'] == 'unhealthy'
        assert 'error' in health
    
    @pytest.mark.asyncio
    async def test_worker_loop_processing(self, temp_config_dir, mock_components):
        """Test worker loop processing files."""
        app = AVMetadataScraper(temp_config_dir)
        
        # Mock process_single_file
        app._process_single_file = AsyncMock()
        
        # Add test files to queue
        video_file = VideoFile(
            file_path="/test/movie.mp4",
            filename="movie.mp4",
            file_size=1000,
            extension=".mp4",
            detected_code="SSIS-001"
        )
        
        await app.processing_queue.put(video_file)
        await app.processing_queue.put(None)  # Sentinel to stop worker
        
        # Run worker loop
        await app._worker_loop("test-worker")
        
        # Verify file was processed
        app._process_single_file.assert_called_once_with(video_file, "test-worker")
    
    @pytest.mark.asyncio
    async def test_worker_loop_cancellation(self, temp_config_dir, mock_components):
        """Test worker loop cancellation."""
        app = AVMetadataScraper(temp_config_dir)
        
        # Start worker loop
        worker_task = asyncio.create_task(app._worker_loop("test-worker"))
        
        # Cancel the task
        worker_task.cancel()
        
        # Wait for cancellation
        with pytest.raises(asyncio.CancelledError):
            await worker_task
    
    def test_log_final_statistics(self, temp_config_dir, mock_components):
        """Test logging of final statistics."""
        app = AVMetadataScraper(temp_config_dir)
        
        # Set some statistics
        app.processing_stats.files_scanned = 10
        app.processing_stats.files_processed = 8
        app.processing_stats.start_time = datetime.now()
        app.processing_stats.end_time = datetime.now()
        
        # Mock component statistics
        app.metadata_scraper.get_scraper_stats = Mock(return_value={'success_rate': 90.0})
        app.file_organizer.get_statistics = Mock(return_value={'success_rate': 95.0})
        app.image_downloader.get_statistics = Mock(return_value={'success_rate': 85.0})
        app.error_handler.get_error_statistics = Mock(return_value={'total_errors': 2})
        
        # Should not raise exception
        app._log_final_statistics()


if __name__ == "__main__":
    pytest.main([__file__])