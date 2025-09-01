"""End-to-end integration tests for the AV Metadata Scraper."""

import pytest
import asyncio
import tempfile
import shutil
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date

from src.main_application import AVMetadataScraper
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def test_environment(self):
        """Create a complete test environment with directories and files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create directory structure
            source_dir = base_path / "source"
            target_dir = base_path / "target"
            config_dir = base_path / "config"
            logs_dir = base_path / "logs"
            
            for directory in [source_dir, target_dir, config_dir, logs_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            # Create test video files with various naming patterns
            test_files = [
                "SSIS-001.mp4",
                "SSIS-002_1080p.mkv",
                "[Studio] SSIS-003 [HD].avi",
                "FC2-PPV-123456.mp4",
                "1PON-654321.mkv",
                "random_video.mp4",  # No code
                "INVALID-FORMAT.txt"  # Not a video
            ]
            
            for filename in test_files:
                file_path = source_dir / filename
                file_path.write_bytes(b"fake video content" * 1000)  # Create some file size
            
            # Create subdirectory with more files
            subdir = source_dir / "subdirectory"
            subdir.mkdir()
            (subdir / "SSIS-004.mp4").write_bytes(b"more fake content" * 500)
            
            # Create configuration file
            config_data = {
                'logging': {
                    'level': 'INFO',
                    'directory': str(logs_dir),
                    'console': True,
                    'file': True
                },
                'scanner': {
                    'source_directory': str(source_dir),
                    'supported_formats': ['.mp4', '.mkv', '.avi'],
                    'recursive': True
                },
                'organizer': {
                    'target_directory': str(target_dir),
                    'naming_pattern': '{actress}/{code}/{code}.{ext}',
                    'safe_mode': True,
                    'create_metadata_files': True
                },
                'downloader': {
                    'enabled': True,
                    'max_concurrent': 2,
                    'timeout_seconds': 30
                },
                'scrapers': {
                    'priority': ['javdb', 'javlibrary'],
                    'timeout_seconds': 30,
                    'retry_attempts': 2
                },
                'processing': {
                    'max_concurrent_files': 2,
                    'batch_size': 10
                }
            }
            
            config_file = config_dir / "config.yaml"
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            yield {
                'base_path': base_path,
                'source_dir': source_dir,
                'target_dir': target_dir,
                'config_file': config_file,
                'logs_dir': logs_dir,
                'test_files': test_files
            }
    
    @pytest.fixture
    def mock_scrapers(self):
        """Mock scrapers that return realistic test data."""
        mock_metadata_db = {
            'SSIS-001': MovieMetadata(
                code='SSIS-001',
                title='Beautiful Actress First Work',
                title_en='Beautiful Actress First Work',
                actresses=['Yui Hatano'],
                release_date=date(2023, 1, 15),
                duration=120,
                studio='S1 NO.1 STYLE',
                series='First Impression',
                genres=['Drama', 'Beautiful Girl', 'Single Work'],
                cover_url='https://example.com/covers/ssis001_cover.jpg',
                poster_url='https://example.com/posters/ssis001_poster.jpg',
                screenshots=['https://example.com/screenshots/ssis001_1.jpg'],
                description='A beautiful debut work featuring amazing performance.',
                rating=4.5,
                source_url='https://javdb.com/v/abc123'
            ),
            'SSIS-002': MovieMetadata(
                code='SSIS-002',
                title='Passionate Love Story',
                actresses=['Mia Nanasawa'],
                release_date=date(2023, 2, 1),
                duration=150,
                studio='S1 NO.1 STYLE',
                cover_url='https://example.com/covers/ssis002_cover.jpg',
                source_url='https://javdb.com/v/def456'
            ),
            'SSIS-003': MovieMetadata(
                code='SSIS-003',
                title='Summer Romance',
                actresses=['Rika Aimi'],
                release_date=date(2023, 3, 10),
                duration=135,
                studio='S1 NO.1 STYLE',
                cover_url='https://example.com/covers/ssis003_cover.jpg',
                source_url='https://javlibrary.com/en/?v=javli123'
            ),
            'SSIS-004': MovieMetadata(
                code='SSIS-004',
                title='Office Lady Special',
                actresses=['Tsukasa Aoi'],
                release_date=date(2023, 4, 5),
                duration=140,
                studio='S1 NO.1 STYLE',
                cover_url='https://example.com/covers/ssis004_cover.jpg',
                source_url='https://javdb.com/v/ghi789'
            ),
            'FC2-PPV-123456': MovieMetadata(
                code='FC2-PPV-123456',
                title='Amateur Beauty Collection',
                actresses=['Amateur'],
                release_date=date(2023, 5, 20),
                duration=90,
                studio='FC2',
                cover_url='https://example.com/covers/fc2ppv123456_cover.jpg',
                source_url='https://javdb.com/v/fc2123'
            ),
            '1PON-654321': MovieMetadata(
                code='1PON-654321',
                title='Uncensored Beauty',
                actresses=['Rei Mizuna'],
                release_date=date(2023, 6, 15),
                duration=110,
                studio='1Pondo',
                cover_url='https://example.com/covers/1pon654321_cover.jpg',
                source_url='https://javlibrary.com/en/?v=1pon654'
            )
        }
        
        async def mock_scrape_metadata(code: str):
            """Mock metadata scraping."""
            await asyncio.sleep(0.1)  # Simulate network delay
            return mock_metadata_db.get(code)
        
        return mock_scrape_metadata
    
    @pytest.fixture
    def mock_image_downloader(self):
        """Mock image downloader that creates fake image files."""
        async def mock_download_images(metadata: MovieMetadata, target_dir: Path):
            """Mock image downloading."""
            await asyncio.sleep(0.05)  # Simulate download time
            
            downloaded_files = []
            
            if metadata.cover_url:
                cover_file = target_dir / f"{metadata.code}_cover.jpg"
                cover_file.write_bytes(b"fake cover image data")
                downloaded_files.append(str(cover_file))
            
            if metadata.poster_url:
                poster_file = target_dir / f"{metadata.code}_poster.jpg"
                poster_file.write_bytes(b"fake poster image data")
                downloaded_files.append(str(poster_file))
            
            return {
                'success': True,
                'downloaded_files': downloaded_files,
                'total_size': len(downloaded_files) * 1024
            }
        
        return mock_download_images
    
    @pytest.mark.asyncio
    async def test_complete_processing_pipeline(self, test_environment, mock_scrapers, mock_image_downloader):
        """Test the complete processing pipeline from start to finish."""
        env = test_environment
        
        with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', mock_scrapers), \
             patch('src.downloaders.image_downloader.ImageDownloader.download_movie_images', mock_image_downloader):
            
            # Initialize application
            app = AVMetadataScraper(str(env['config_file']))
            
            # Run the complete pipeline
            await app.start()
            
            # Wait for processing to complete
            await asyncio.sleep(2)
            
            # Stop the application
            await app.stop()
            
            # Verify results
            stats = app.get_status()['processing_stats']
            
            # Should have scanned video files (excluding .txt file)
            assert stats['files_scanned'] >= 6  # 6 video files
            
            # Should have processed files with valid codes
            assert stats['files_processed'] >= 5  # Files with detectable codes
            
            # Should have organized files
            assert stats['files_organized'] >= 5
            
            # Should have downloaded images
            assert stats['images_downloaded'] > 0
            
            # Check that target directory has organized files
            target_dir = env['target_dir']
            organized_files = list(target_dir.rglob("*.mp4")) + list(target_dir.rglob("*.mkv")) + list(target_dir.rglob("*.avi"))
            assert len(organized_files) >= 5
            
            # Check that metadata files were created
            metadata_files = list(target_dir.rglob("*.json"))
            assert len(metadata_files) >= 5
            
            # Check that image files were downloaded
            image_files = list(target_dir.rglob("*.jpg"))
            assert len(image_files) > 0
            
            # Verify directory structure (actress/code/file pattern)
            for organized_file in organized_files:
                # Should be in actress/code/ structure
                assert len(organized_file.parts) >= 3  # At least target/actress/code/file
                
                # Check that metadata file exists alongside video
                metadata_file = organized_file.parent / f"{organized_file.stem}.json"
                assert metadata_file.exists()
                
                # Verify metadata content
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    assert 'code' in metadata
                    assert 'title' in metadata
                    assert 'actresses' in metadata
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, test_environment):
        """Test error handling and recovery mechanisms."""
        env = test_environment
        
        # Mock scraper that fails for some codes
        async def failing_scraper(code: str):
            if code in ['SSIS-001', 'SSIS-003']:
                raise Exception(f"Network error for {code}")
            elif code == 'SSIS-002':
                return None  # No metadata found
            else:
                return MovieMetadata(
                    code=code,
                    title=f"Test Movie {code}",
                    actresses=['Test Actress']
                )
        
        with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', failing_scraper):
            
            app = AVMetadataScraper(str(env['config_file']))
            
            # Run processing
            await app.start()
            await asyncio.sleep(2)
            await app.stop()
            
            # Check error handling
            stats = app.get_status()['processing_stats']
            
            # Should have encountered errors but continued processing
            assert stats['errors_encountered'] > 0
            
            # Should still have processed some files successfully
            assert stats['files_processed'] > 0
            
            # Success rate should be less than 100%
            assert stats['success_rate'] < 100.0
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, test_environment, mock_scrapers, mock_image_downloader):
        """Test concurrent file processing capabilities."""
        env = test_environment
        
        # Create more test files to test concurrency
        source_dir = env['source_dir']
        for i in range(10, 20):
            filename = f"SSIS-{i:03d}.mp4"
            (source_dir / filename).write_bytes(b"test content" * 100)
        
        # Add metadata for new files
        async def extended_mock_scraper(code: str):
            await asyncio.sleep(0.2)  # Longer delay to test concurrency
            if code.startswith('SSIS-'):
                return MovieMetadata(
                    code=code,
                    title=f"Test Movie {code}",
                    actresses=['Test Actress'],
                    cover_url=f"https://example.com/{code}_cover.jpg"
                )
            return await mock_scrapers(code)
        
        with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', extended_mock_scraper), \
             patch('src.downloaders.image_downloader.ImageDownloader.download_movie_images', mock_image_downloader):
            
            app = AVMetadataScraper(str(env['config_file']))
            
            start_time = datetime.now()
            
            # Run processing
            await app.start()
            await asyncio.sleep(5)  # Allow more time for concurrent processing
            await app.stop()
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            stats = app.get_status()['processing_stats']
            
            # Should have processed multiple files
            assert stats['files_processed'] >= 10
            
            # With concurrency, should be faster than sequential processing
            # (This is a rough estimate - actual timing may vary)
            expected_sequential_time = stats['files_processed'] * 0.2  # 0.2s per file
            assert processing_time < expected_sequential_time * 0.8  # Should be at least 20% faster
    
    @pytest.mark.asyncio
    async def test_configuration_validation(self, test_environment):
        """Test configuration validation and error handling."""
        env = test_environment
        
        # Test with invalid configuration
        invalid_config = {
            'scanner': {
                'source_directory': '/nonexistent/path',
                'supported_formats': []  # Empty formats
            },
            'organizer': {
                'target_directory': '',  # Empty target
                'naming_pattern': ''  # Empty pattern
            }
        }
        
        invalid_config_file = env['base_path'] / "invalid_config.yaml"
        with open(invalid_config_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        # Should handle invalid configuration gracefully
        app = AVMetadataScraper(str(invalid_config_file))
        
        # Health check should report configuration issues
        health = await app.health_check()
        assert health['status'] in ['degraded', 'unhealthy']
        assert 'configuration' in health.get('issues', {})
    
    @pytest.mark.asyncio
    async def test_file_organization_patterns(self, test_environment, mock_scrapers, mock_image_downloader):
        """Test different file organization patterns."""
        env = test_environment
        
        # Test different naming patterns
        patterns_to_test = [
            '{code}.{ext}',
            '{actress}/{code}.{ext}',
            '{studio}/{actress}/{code}.{ext}',
            '{code} - {title}.{ext}'
        ]
        
        for pattern in patterns_to_test:
            # Update config with new pattern
            config_data = yaml.safe_load(open(env['config_file']))
            config_data['organizer']['naming_pattern'] = pattern
            
            # Create separate target directory for this test
            pattern_target = env['base_path'] / f"target_{pattern.replace('/', '_').replace('{', '').replace('}', '')}"
            pattern_target.mkdir(exist_ok=True)
            config_data['organizer']['target_directory'] = str(pattern_target)
            
            pattern_config_file = env['base_path'] / f"config_{pattern.replace('/', '_')}.yaml"
            with open(pattern_config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', mock_scrapers), \
                 patch('src.downloaders.image_downloader.ImageDownloader.download_movie_images', mock_image_downloader):
                
                app = AVMetadataScraper(str(pattern_config_file))
                
                # Process a single file to test pattern
                await app.start()
                await asyncio.sleep(1)
                await app.stop()
                
                # Verify files were organized according to pattern
                organized_files = list(pattern_target.rglob("*.mp4")) + list(pattern_target.rglob("*.mkv"))
                assert len(organized_files) > 0
                
                # Check that the file structure matches the expected pattern
                for organized_file in organized_files:
                    if '{actress}' in pattern:
                        # Should be in actress subdirectory
                        assert len(organized_file.parts) > len(pattern_target.parts) + 1
    
    @pytest.mark.asyncio
    async def test_duplicate_file_handling(self, test_environment, mock_scrapers, mock_image_downloader):
        """Test handling of duplicate files and conflicts."""
        env = test_environment
        
        # Create duplicate files in source
        source_dir = env['source_dir']
        duplicate_dir = source_dir / "duplicates"
        duplicate_dir.mkdir()
        
        # Copy existing file to create duplicate
        original_file = source_dir / "SSIS-001.mp4"
        duplicate_file = duplicate_dir / "SSIS-001.mp4"
        shutil.copy2(original_file, duplicate_file)
        
        with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', mock_scrapers), \
             patch('src.downloaders.image_downloader.ImageDownloader.download_movie_images', mock_image_downloader):
            
            app = AVMetadataScraper(str(env['config_file']))
            
            await app.start()
            await asyncio.sleep(2)
            await app.stop()
            
            stats = app.get_status()['processing_stats']
            
            # Should handle duplicates gracefully
            assert stats['errors_encountered'] >= 0  # May or may not be treated as error
            
            # Check that at least one version was processed
            target_files = list(env['target_dir'].rglob("*SSIS-001*"))
            assert len(target_files) > 0
    
    @pytest.mark.asyncio
    async def test_progress_persistence(self, test_environment, mock_scrapers):
        """Test progress saving and resumption."""
        env = test_environment
        
        # Mock scraper that processes slowly
        processed_codes = []
        
        async def slow_scraper(code: str):
            processed_codes.append(code)
            await asyncio.sleep(0.5)  # Slow processing
            return await mock_scrapers(code)
        
        with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', slow_scraper):
            
            app = AVMetadataScraper(str(env['config_file']))
            
            # Start processing
            start_task = asyncio.create_task(app.start())
            
            # Let it process some files
            await asyncio.sleep(2)
            
            # Stop abruptly (simulating interruption)
            await app.stop()
            await start_task
            
            # Check that some progress was made
            first_run_processed = len(processed_codes)
            assert first_run_processed > 0
            
            # Start again (should resume from where it left off)
            processed_codes.clear()
            
            app2 = AVMetadataScraper(str(env['config_file']))
            await app2.start()
            await asyncio.sleep(2)
            await app2.stop()
            
            # Should process remaining files
            second_run_processed = len(processed_codes)
            
            # Total processed should cover all files
            total_video_files = len([f for f in env['test_files'] if f.endswith(('.mp4', '.mkv', '.avi'))]) + 1  # +1 for subdirectory file
            assert first_run_processed + second_run_processed >= total_video_files
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, test_environment):
        """Test health monitoring and status reporting."""
        env = test_environment
        
        app = AVMetadataScraper(str(env['config_file']))
        
        # Test health check before starting
        health = await app.health_check()
        assert 'status' in health
        assert health['status'] in ['healthy', 'degraded', 'unhealthy']
        
        # Test status reporting
        status = app.get_status()
        assert 'is_running' in status
        assert 'processing_stats' in status
        assert 'component_stats' in status
        
        # Start application and check running status
        start_task = asyncio.create_task(app.start())
        await asyncio.sleep(0.5)
        
        running_status = app.get_status()
        assert running_status['is_running'] is True
        
        # Stop and check final status
        await app.stop()
        await start_task
        
        final_status = app.get_status()
        assert final_status['is_running'] is False
    
    def test_configuration_file_formats(self, test_environment):
        """Test support for different configuration file formats."""
        env = test_environment
        
        # Test YAML configuration (already tested above)
        yaml_config = yaml.safe_load(open(env['config_file']))
        app_yaml = AVMetadataScraper(str(env['config_file']))
        assert app_yaml.config is not None
        
        # Test JSON configuration
        json_config_file = env['base_path'] / "config.json"
        with open(json_config_file, 'w') as f:
            json.dump(yaml_config, f, indent=2, default=str)
        
        app_json = AVMetadataScraper(str(json_config_file))
        assert app_json.config is not None
        
        # Configurations should be equivalent
        assert app_yaml.config['scanner']['source_directory'] == app_json.config['scanner']['source_directory']
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, test_environment, mock_scrapers):
        """Test graceful shutdown during processing."""
        env = test_environment
        
        # Mock scraper with longer processing time
        async def long_running_scraper(code: str):
            await asyncio.sleep(2)  # Long processing time
            return await mock_scrapers(code)
        
        with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', long_running_scraper):
            
            app = AVMetadataScraper(str(env['config_file']))
            
            # Start processing
            start_task = asyncio.create_task(app.start())
            
            # Let it start processing
            await asyncio.sleep(0.5)
            
            # Request graceful shutdown
            shutdown_start = datetime.now()
            await app.stop()
            await start_task
            shutdown_time = (datetime.now() - shutdown_start).total_seconds()
            
            # Should shutdown within reasonable time (not wait for all long operations)
            assert shutdown_time < 10  # Should not take more than 10 seconds
            
            # Should have saved progress
            stats = app.get_status()['processing_stats']
            assert stats['files_scanned'] > 0  # Should have at least scanned files


if __name__ == "__main__":
    pytest.main([__file__, "-v"])