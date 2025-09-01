"""Performance and load tests for AV Metadata Scraper."""

import pytest
import asyncio
import tempfile
import time
import psutil
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from src.main_application import AVMetadataScraper
from src.scanner.file_scanner import FileScanner
from src.scrapers.metadata_scraper import MetadataScraper
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata


class TestPerformance:
    """Performance test cases."""
    
    @pytest.fixture
    def large_file_set(self):
        """Create a large set of test files for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            
            # Create 1000 test video files
            file_paths = []
            for i in range(1000):
                filename = f"SSIS-{i:04d}.mp4"
                file_path = source_dir / filename
                file_path.write_bytes(b"fake content" * 100)  # Small files for speed
                file_paths.append(file_path)
            
            yield {
                'source_dir': source_dir,
                'file_paths': file_paths,
                'file_count': 1000
            }
    
    @pytest.fixture
    def performance_config(self, large_file_set):
        """Create performance test configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            target_dir = config_dir / "target"
            target_dir.mkdir()
            
            config_data = {
                'logging': {
                    'level': 'WARNING',  # Reduce logging for performance
                    'console': False,
                    'file': False
                },
                'scanner': {
                    'source_directory': str(large_file_set['source_dir']),
                    'supported_formats': ['.mp4', '.mkv', '.avi'],
                    'recursive': True
                },
                'organizer': {
                    'target_directory': str(target_dir),
                    'naming_pattern': '{code}.{ext}',
                    'safe_mode': False  # Disable for performance
                },
                'downloader': {
                    'enabled': False  # Disable for performance tests
                },
                'processing': {
                    'max_concurrent_files': 10,
                    'batch_size': 50
                }
            }
            
            import yaml
            config_file = config_dir / "config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            yield {
                'config_file': config_file,
                'target_dir': target_dir,
                'config_data': config_data
            }
    
    @pytest.mark.performance
    def test_file_scanning_performance(self, large_file_set):
        """Test file scanning performance with large number of files."""
        scanner = FileScanner(
            str(large_file_set['source_dir']),
            ['.mp4', '.mkv', '.avi']
        )
        
        # Measure scanning time
        start_time = time.time()
        video_files = scanner.scan_directory()
        scan_time = time.time() - start_time
        
        # Performance assertions
        assert len(video_files) == large_file_set['file_count']
        assert scan_time < 10.0  # Should scan 1000 files in under 10 seconds
        
        # Calculate performance metrics
        files_per_second = len(video_files) / scan_time
        assert files_per_second > 100  # Should process at least 100 files per second
        
        print(f"Scanned {len(video_files)} files in {scan_time:.2f}s ({files_per_second:.1f} files/s)")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_metadata_scraping_performance(self):
        """Test metadata scraping performance with concurrent requests."""
        # Mock fast scraper
        async def fast_mock_scraper(code: str):
            await asyncio.sleep(0.01)  # 10ms delay to simulate network
            return MovieMetadata(
                code=code,
                title=f"Test Movie {code}",
                actresses=['Test Actress']
            )
        
        # Test different concurrency levels
        codes = [f"SSIS-{i:04d}" for i in range(100)]
        
        for max_concurrent in [1, 5, 10, 20]:
            scraper = MetadataScraper(
                scrapers=[],  # We'll mock the scrape_metadata method
                max_concurrent_requests=max_concurrent
            )
            
            with patch.object(scraper, 'scrape_metadata', fast_mock_scraper):
                start_time = time.time()
                results = await scraper.scrape_multiple(codes, max_concurrent=max_concurrent)
                scrape_time = time.time() - start_time
                
                # All requests should succeed
                assert len(results) == 100
                assert all(result is not None for result in results.values())
                
                requests_per_second = 100 / scrape_time
                print(f"Concurrency {max_concurrent}: {scrape_time:.2f}s ({requests_per_second:.1f} req/s)")
                
                # Higher concurrency should be faster (up to a point)
                if max_concurrent == 1:
                    sequential_time = scrape_time
                elif max_concurrent >= 10:
                    # Should be significantly faster than sequential
                    assert scrape_time < sequential_time * 0.3
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_during_processing(self, performance_config):
        """Test memory usage during large batch processing."""
        config = performance_config
        
        # Mock lightweight scraper
        async def memory_test_scraper(code: str):
            await asyncio.sleep(0.001)  # Very fast
            return MovieMetadata(code=code, title=f"Movie {code}")
        
        with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', memory_test_scraper):
            
            # Monitor memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            app = AVMetadataScraper(str(config['config_file']))
            
            # Start processing
            await app.start()
            
            # Monitor memory during processing
            max_memory = initial_memory
            for _ in range(10):  # Check memory 10 times during processing
                await asyncio.sleep(0.5)
                current_memory = process.memory_info().rss / 1024 / 1024
                max_memory = max(max_memory, current_memory)
            
            await app.stop()
            
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = max_memory - initial_memory
            
            print(f"Memory usage: Initial={initial_memory:.1f}MB, Max={max_memory:.1f}MB, Final={final_memory:.1f}MB")
            print(f"Memory increase: {memory_increase:.1f}MB")
            
            # Memory increase should be reasonable (less than 500MB for 1000 files)
            assert memory_increase < 500
            
            # Memory should not continuously grow (memory leak check)
            memory_leak = final_memory - initial_memory
            assert memory_leak < 100  # Should not leak more than 100MB
    
    @pytest.mark.performance
    def test_concurrent_file_operations(self, large_file_set):
        """Test concurrent file operations performance."""
        source_files = large_file_set['file_paths'][:100]  # Use subset for faster test
        
        with tempfile.TemporaryDirectory() as target_temp:
            target_dir = Path(target_temp)
            
            def copy_file(source_path):
                """Copy file to target directory."""
                target_path = target_dir / source_path.name
                target_path.write_bytes(source_path.read_bytes())
                return target_path
            
            # Test sequential vs concurrent file operations
            
            # Sequential
            start_time = time.time()
            for source_file in source_files:
                copy_file(source_file)
            sequential_time = time.time() - start_time
            
            # Clean up
            for file in target_dir.iterdir():
                file.unlink()
            
            # Concurrent
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=10) as executor:
                list(executor.map(copy_file, source_files))
            concurrent_time = time.time() - start_time
            
            print(f"File operations: Sequential={sequential_time:.2f}s, Concurrent={concurrent_time:.2f}s")
            
            # Concurrent should be faster
            assert concurrent_time < sequential_time * 0.8
            
            # All files should be copied
            assert len(list(target_dir.iterdir())) == len(source_files)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_throughput_under_load(self, performance_config):
        """Test system throughput under various load conditions."""
        config = performance_config
        
        # Create different load scenarios
        load_scenarios = [
            {'files': 50, 'concurrency': 5, 'delay': 0.01},   # Light load
            {'files': 100, 'concurrency': 10, 'delay': 0.02}, # Medium load
            {'files': 200, 'concurrency': 15, 'delay': 0.05}, # Heavy load
        ]
        
        results = []
        
        for scenario in load_scenarios:
            # Mock scraper with configurable delay
            async def load_test_scraper(code: str):
                await asyncio.sleep(scenario['delay'])
                return MovieMetadata(code=code, title=f"Movie {code}")
            
            # Create subset of files for this scenario
            source_dir = Path(config['config_data']['scanner']['source_directory'])
            test_files = list(source_dir.glob("*.mp4"))[:scenario['files']]
            
            # Update config for this scenario
            scenario_config = config['config_data'].copy()
            scenario_config['processing']['max_concurrent_files'] = scenario['concurrency']
            
            import yaml
            scenario_config_file = config['config_file'].parent / f"scenario_config_{scenario['files']}.yaml"
            with open(scenario_config_file, 'w') as f:
                yaml.dump(scenario_config, f)
            
            with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', load_test_scraper):
                
                app = AVMetadataScraper(str(scenario_config_file))
                
                start_time = time.time()
                await app.start()
                
                # Wait for processing to complete
                while app.is_running and app.get_status()['processing_stats']['files_processed'] < len(test_files):
                    await asyncio.sleep(0.1)
                
                await app.stop()
                processing_time = time.time() - start_time
                
                stats = app.get_status()['processing_stats']
                throughput = stats['files_processed'] / processing_time
                
                results.append({
                    'scenario': scenario,
                    'processing_time': processing_time,
                    'throughput': throughput,
                    'stats': stats
                })
                
                print(f"Load test - Files: {scenario['files']}, Concurrency: {scenario['concurrency']}")
                print(f"  Time: {processing_time:.2f}s, Throughput: {throughput:.1f} files/s")
        
        # Verify that system handles increasing load reasonably
        for i, result in enumerate(results):
            # Should process all files successfully
            assert result['stats']['files_processed'] >= result['scenario']['files'] * 0.9  # Allow 10% failure
            
            # Throughput should be reasonable
            assert result['throughput'] > 1.0  # At least 1 file per second
    
    @pytest.mark.performance
    def test_cache_performance(self):
        """Test caching performance and effectiveness."""
        from src.scrapers.metadata_scraper import MetadataScraper
        
        scraper = MetadataScraper(scrapers=[], cache_duration_minutes=60)
        
        # Test cache hit performance
        test_metadata = MovieMetadata(code="TEST-001", title="Test Movie")
        
        # Cache the result
        scraper._cache_result("TEST-001", test_metadata)
        
        # Measure cache retrieval time
        cache_times = []
        for _ in range(1000):
            start_time = time.perf_counter()
            result = scraper._get_cached_result("TEST-001")
            cache_time = time.perf_counter() - start_time
            cache_times.append(cache_time)
            assert result is not None
        
        avg_cache_time = sum(cache_times) / len(cache_times)
        max_cache_time = max(cache_times)
        
        print(f"Cache performance: Avg={avg_cache_time*1000:.3f}ms, Max={max_cache_time*1000:.3f}ms")
        
        # Cache retrieval should be very fast
        assert avg_cache_time < 0.001  # Less than 1ms average
        assert max_cache_time < 0.01   # Less than 10ms maximum
        
        # Test cache size limits
        for i in range(1500):  # More than default limit of 1000
            code = f"TEST-{i:04d}"
            metadata = MovieMetadata(code=code, title=f"Test {i}")
            scraper._cache_result(code, metadata)
        
        # Cache should be limited
        assert len(scraper._metadata_cache) <= 1000
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test performance impact of error handling."""
        from src.scrapers.metadata_scraper import MetadataScraper
        
        # Mock scraper that fails frequently
        call_count = 0
        
        async def failing_scraper(code: str):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:  # Fail every 3rd request
                raise Exception("Mock failure")
            await asyncio.sleep(0.01)
            return MovieMetadata(code=code, title=f"Movie {code}")
        
        scraper = MetadataScraper(scrapers=[], retry_attempts=2)
        
        with patch.object(scraper, 'scrape_metadata', failing_scraper):
            
            codes = [f"FAIL-{i:03d}" for i in range(100)]
            
            start_time = time.time()
            results = await scraper.scrape_multiple(codes)
            error_handling_time = time.time() - start_time
            
            # Should handle errors without significant performance degradation
            successful_results = sum(1 for r in results.values() if r is not None)
            
            print(f"Error handling: {error_handling_time:.2f}s, Success rate: {successful_results/100:.1%}")
            
            # Should still achieve reasonable throughput despite errors
            throughput = len(codes) / error_handling_time
            assert throughput > 10  # At least 10 requests per second
            
            # Should have some successful results
            assert successful_results > 50  # At least 50% success rate
    
    @pytest.mark.performance
    def test_regex_performance(self):
        """Test performance of code extraction regex patterns."""
        from src.scanner.file_scanner import FileScanner
        
        scanner = FileScanner("/test", ['.mp4'])
        
        # Test with various filename patterns
        test_filenames = [
            "SSIS-001.mp4",
            "[Studio] SSIS-002 [1080p].mkv",
            "FC2-PPV-123456.avi",
            "1PON-654321.mp4",
            "random_filename_without_code.mp4",
            "VERY-LONG-STUDIO-NAME-WITH-MANY-PARTS-ABC-123.mp4"
        ] * 1000  # Test with 6000 filenames
        
        # Measure regex performance
        start_time = time.time()
        extracted_codes = []
        for filename in test_filenames:
            code = scanner.extract_code_from_filename(filename)
            extracted_codes.append(code)
        regex_time = time.time() - start_time
        
        filenames_per_second = len(test_filenames) / regex_time
        
        print(f"Regex performance: {regex_time:.2f}s for {len(test_filenames)} filenames ({filenames_per_second:.0f} files/s)")
        
        # Should process filenames very quickly
        assert filenames_per_second > 10000  # At least 10k filenames per second
        
        # Should extract codes correctly
        successful_extractions = sum(1 for code in extracted_codes if code is not None)
        assert successful_extractions > 4000  # Should extract codes from most files
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_startup_shutdown_performance(self, performance_config):
        """Test application startup and shutdown performance."""
        config = performance_config
        
        startup_times = []
        shutdown_times = []
        
        # Test multiple startup/shutdown cycles
        for _ in range(5):
            app = AVMetadataScraper(str(config['config_file']))
            
            # Measure startup time
            start_time = time.time()
            start_task = asyncio.create_task(app.start())
            await asyncio.sleep(0.1)  # Let it start
            startup_time = time.time() - start_time
            startup_times.append(startup_time)
            
            # Measure shutdown time
            start_time = time.time()
            await app.stop()
            await start_task
            shutdown_time = time.time() - start_time
            shutdown_times.append(shutdown_time)
        
        avg_startup = sum(startup_times) / len(startup_times)
        avg_shutdown = sum(shutdown_times) / len(shutdown_times)
        
        print(f"Startup/Shutdown: Avg startup={avg_startup:.2f}s, Avg shutdown={avg_shutdown:.2f}s")
        
        # Should start and stop quickly
        assert avg_startup < 5.0   # Should start in under 5 seconds
        assert avg_shutdown < 2.0  # Should shutdown in under 2 seconds


class TestLoadTesting:
    """Load testing scenarios."""
    
    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test system behavior under sustained load."""
        # This test simulates continuous processing for an extended period
        
        async def continuous_scraper(code: str):
            await asyncio.sleep(0.1)  # Simulate realistic processing time
            return MovieMetadata(code=code, title=f"Movie {code}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many test files
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            
            for i in range(500):  # 500 files for sustained load
                filename = f"LOAD-{i:04d}.mp4"
                (source_dir / filename).write_bytes(b"content" * 50)
            
            # Create config
            config_data = {
                'logging': {'level': 'ERROR', 'console': False, 'file': False},
                'scanner': {
                    'source_directory': str(source_dir),
                    'supported_formats': ['.mp4']
                },
                'organizer': {
                    'target_directory': str(Path(temp_dir) / "target"),
                    'naming_pattern': '{code}.{ext}'
                },
                'downloader': {'enabled': False},
                'processing': {'max_concurrent_files': 20}
            }
            
            import yaml
            config_file = Path(temp_dir) / "config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', continuous_scraper):
                
                app = AVMetadataScraper(str(config_file))
                
                # Monitor system resources during load test
                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss / 1024 / 1024
                
                start_time = time.time()
                await app.start()
                
                # Monitor for 30 seconds or until completion
                max_duration = 30
                while app.is_running and (time.time() - start_time) < max_duration:
                    await asyncio.sleep(1)
                    
                    current_memory = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent()
                    
                    # Log resource usage periodically
                    if int(time.time() - start_time) % 5 == 0:
                        stats = app.get_status()['processing_stats']
                        print(f"Load test progress: {stats['files_processed']}/500 files, "
                              f"Memory: {current_memory:.1f}MB, CPU: {cpu_percent:.1f}%")
                
                await app.stop()
                total_time = time.time() - start_time
                
                final_stats = app.get_status()['processing_stats']
                final_memory = process.memory_info().rss / 1024 / 1024
                
                print(f"Load test completed: {final_stats['files_processed']} files in {total_time:.1f}s")
                print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB")
                
                # Verify system handled the load well
                assert final_stats['files_processed'] >= 400  # Should process most files
                assert final_stats['success_rate'] >= 80.0    # Should maintain good success rate
                assert final_memory - initial_memory < 200    # Should not use excessive memory
    
    @pytest.mark.load
    @pytest.mark.asyncio
    async def test_burst_load(self):
        """Test system behavior under burst load conditions."""
        # Simulate sudden spikes in processing demand
        
        burst_scenarios = [
            {'burst_size': 50, 'burst_interval': 2},   # 50 files every 2 seconds
            {'burst_size': 100, 'burst_interval': 5},  # 100 files every 5 seconds
        ]
        
        for scenario in burst_scenarios:
            async def burst_scraper(code: str):
                await asyncio.sleep(0.05)  # Fast processing
                return MovieMetadata(code=code, title=f"Burst {code}")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                source_dir = Path(temp_dir) / "source"
                source_dir.mkdir()
                
                # Create files in bursts
                total_files = 0
                for burst in range(3):  # 3 bursts
                    for i in range(scenario['burst_size']):
                        filename = f"BURST-{burst}-{i:03d}.mp4"
                        (source_dir / filename).write_bytes(b"burst content")
                        total_files += 1
                
                config_data = {
                    'logging': {'level': 'ERROR', 'console': False, 'file': False},
                    'scanner': {'source_directory': str(source_dir), 'supported_formats': ['.mp4']},
                    'organizer': {'target_directory': str(Path(temp_dir) / "target"), 'naming_pattern': '{code}.{ext}'},
                    'downloader': {'enabled': False},
                    'processing': {'max_concurrent_files': 25}
                }
                
                import yaml
                config_file = Path(temp_dir) / "config.yaml"
                with open(config_file, 'w') as f:
                    yaml.dump(config_data, f)
                
                with patch('src.scrapers.metadata_scraper.MetadataScraper.scrape_metadata', burst_scraper):
                    
                    app = AVMetadataScraper(str(config_file))
                    
                    start_time = time.time()
                    await app.start()
                    
                    # Wait for burst processing
                    while app.is_running and (time.time() - start_time) < 20:
                        await asyncio.sleep(0.5)
                    
                    await app.stop()
                    
                    stats = app.get_status()['processing_stats']
                    
                    print(f"Burst test ({scenario}): Processed {stats['files_processed']}/{total_files} files")
                    
                    # Should handle bursts effectively
                    assert stats['files_processed'] >= total_files * 0.9  # Process at least 90%
                    assert stats['success_rate'] >= 85.0  # Maintain good success rate


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance"])