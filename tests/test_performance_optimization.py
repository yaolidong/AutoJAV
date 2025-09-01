"""Tests for performance optimization features."""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.utils.progress_persistence import (
    ProgressPersistence, ProcessingSession, PersistenceFormat
)
from src.utils.duplicate_detector import (
    DuplicateDetector, DuplicateStrategy, HashAlgorithm, DuplicateGroup
)
from src.utils.batch_processor import (
    BatchProcessor, BatchJob, ScheduledTask, BatchMode, ScheduleType
)
from src.utils.performance_monitor import (
    PerformanceMonitor, ResourceSnapshot, PerformanceMetrics, PerformanceContext
)
from src.models.video_file import VideoFile


class TestProgressPersistence:
    """Test progress persistence functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def persistence(self, temp_dir):
        """Create progress persistence instance."""
        return ProgressPersistence(
            persistence_dir=temp_dir / "progress",
            format=PersistenceFormat.JSON,
            auto_save_interval=1.0
        )
    
    def test_start_session(self, persistence):
        """Test starting a new processing session."""
        session = persistence.start_session(
            session_id="test_session",
            total_files=100,
            metadata={"test": "data"}
        )
        
        assert session.session_id == "test_session"
        assert session.total_files == 100
        assert session.session_metadata["test"] == "data"
        assert persistence.current_session == session
    
    def test_update_session(self, persistence):
        """Test updating session progress."""
        session = persistence.start_session(total_files=10)
        
        # Update with processed file
        persistence.update_session(processed_file="file1.mp4")
        assert "file1.mp4" in session.processed_files
        
        # Update with failed file
        persistence.update_session(failed_file="file2.mp4")
        assert "file2.mp4" in session.failed_files
        
        # Update with skipped file
        persistence.update_session(skipped_file="file3.mp4")
        assert "file3.mp4" in session.skipped_files
    
    def test_save_and_load_session(self, persistence):
        """Test saving and loading sessions."""
        # Create and save session
        original_session = persistence.start_session(
            session_id="save_test",
            total_files=50
        )
        persistence.update_session(processed_file="test.mp4")
        persistence.save_session()
        
        # Load session
        loaded_session = persistence.load_session("save_test")
        
        assert loaded_session is not None
        assert loaded_session.session_id == "save_test"
        assert loaded_session.total_files == 50
        assert "test.mp4" in loaded_session.processed_files
    
    def test_resume_session(self, persistence):
        """Test resuming a previous session."""
        # Create and save session
        persistence.start_session(session_id="resume_test", total_files=25)
        persistence.update_session(processed_file="file1.mp4")
        persistence.save_session()
        persistence.current_session = None
        
        # Resume session
        resumed_session = persistence.resume_session("resume_test")
        
        assert resumed_session is not None
        assert resumed_session.session_id == "resume_test"
        assert persistence.current_session == resumed_session
        assert "file1.mp4" in resumed_session.processed_files
    
    def test_list_sessions(self, persistence):
        """Test listing available sessions."""
        # Create multiple sessions
        persistence.start_session(session_id="session1", total_files=10)
        persistence.save_session()
        persistence.current_session = None
        
        persistence.start_session(session_id="session2", total_files=20)
        persistence.update_session(processed_file="file1.mp4")
        persistence.save_session()
        persistence.current_session = None
        
        # List sessions
        sessions = persistence.list_sessions()
        
        assert len(sessions) == 2
        session_ids = [s['session_id'] for s in sessions]
        assert "session1" in session_ids
        assert "session2" in session_ids
    
    def test_get_session_progress(self, persistence):
        """Test getting session progress information."""
        session = persistence.start_session(total_files=100)
        persistence.update_session(processed_file="file1.mp4")
        persistence.update_session(processed_file="file2.mp4")
        persistence.update_session(failed_file="file3.mp4")
        
        progress = persistence.get_session_progress()
        
        assert progress is not None
        assert progress['total_files'] == 100
        assert progress['processed_files'] == 2
        assert progress['failed_files'] == 1
        assert progress['progress_percentage'] == 3.0  # (2+1)/100 * 100
    
    @pytest.mark.asyncio
    async def test_auto_save(self, persistence):
        """Test automatic session saving."""
        session = persistence.start_session(total_files=10)
        persistence.update_session(processed_file="auto_save_test.mp4")
        
        # Wait for auto-save
        await asyncio.sleep(1.5)
        
        # Load session from disk to verify auto-save worked
        loaded_session = persistence.load_session(session.session_id)
        assert "auto_save_test.mp4" in loaded_session.processed_files


class TestDuplicateDetector:
    """Test duplicate file detection functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def detector(self, temp_dir):
        """Create duplicate detector instance."""
        return DuplicateDetector(
            hash_algorithm=HashAlgorithm.SHA256,
            cache_file=temp_dir / "hash_cache.json"
        )
    
    @pytest.fixture
    def sample_files(self, temp_dir):
        """Create sample video files for testing."""
        files = []
        
        # Create test files with different content
        for i in range(5):
            file_path = temp_dir / f"video_{i}.mp4"
            content = f"test content {i}" * 100  # Different content
            file_path.write_text(content)
            
            video_file = VideoFile(
                file_path=str(file_path),
                filename=f"video_{i}.mp4",
                file_size=len(content),
                extension=".mp4"
            )
            files.append(video_file)
        
        # Create duplicate files (same content as video_1)
        for i in [6, 7]:
            file_path = temp_dir / f"video_{i}.mp4"
            content = "test content 1" * 100  # Same as video_1
            file_path.write_text(content)
            
            video_file = VideoFile(
                file_path=str(file_path),
                filename=f"video_{i}.mp4",
                file_size=len(content),
                extension=".mp4"
            )
            files.append(video_file)
        
        return files
    
    @pytest.mark.asyncio
    async def test_detect_duplicates(self, detector, sample_files):
        """Test duplicate detection."""
        report = await detector.detect_duplicates(sample_files)
        
        assert report.total_files_scanned == 7
        assert len(report.duplicate_groups) == 1  # One group of duplicates
        assert report.total_duplicates == 2  # 2 duplicate files (video_6, video_7)
        
        # Check duplicate group
        duplicate_group = report.duplicate_groups[0]
        assert duplicate_group.file_count == 3  # video_1, video_6, video_7
        assert duplicate_group.wasted_space > 0
    
    def test_group_by_size(self, detector, sample_files):
        """Test grouping files by size."""
        size_groups = detector._group_by_size(sample_files)
        
        # Files with same content should have same size
        duplicate_size = len("test content 1" * 100)
        assert duplicate_size in size_groups
        assert len(size_groups[duplicate_size]) == 3  # video_1, video_6, video_7
    
    @pytest.mark.asyncio
    async def test_hash_caching(self, detector, sample_files):
        """Test hash caching functionality."""
        # First detection should cache hashes
        await detector.detect_duplicates(sample_files[:2])
        assert len(detector.hash_cache) == 2
        
        # Second detection should use cached hashes
        with patch.object(detector, '_calculate_file_hash') as mock_hash:
            await detector.detect_duplicates(sample_files[:2])
            # Should not call hash calculation for cached files
            mock_hash.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_handle_duplicates_keep_larger(self, detector, sample_files):
        """Test handling duplicates with keep larger strategy."""
        report = await detector.detect_duplicates(sample_files)
        
        result = await detector.handle_duplicates(
            report.duplicate_groups,
            DuplicateStrategy.KEEP_LARGER,
            dry_run=True
        )
        
        assert result['files_processed'] > 0
        assert result['files_deleted'] == 2  # Should delete 2 duplicates
        assert len(result['actions']) > 0
    
    @pytest.mark.asyncio
    async def test_handle_duplicates_keep_both(self, detector, sample_files):
        """Test handling duplicates with keep both strategy."""
        report = await detector.detect_duplicates(sample_files)
        
        result = await detector.handle_duplicates(
            report.duplicate_groups,
            DuplicateStrategy.KEEP_BOTH,
            dry_run=True
        )
        
        assert result['files_processed'] > 0
        assert result['files_renamed'] == 2  # Should rename 2 duplicates
        assert result['files_deleted'] == 0  # Should not delete any files


class TestBatchProcessor:
    """Test batch processing functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def batch_processor(self, temp_dir):
        """Create batch processor instance."""
        return BatchProcessor(
            storage_dir=temp_dir / "batch",
            max_concurrent_jobs=1
        )
    
    def test_create_job(self, batch_processor):
        """Test creating a batch job."""
        job = batch_processor.create_job(
            name="Test Job",
            source_directories=["/source1", "/source2"],
            target_directory="/target",
            mode=BatchMode.PARALLEL,
            max_concurrent=5
        )
        
        assert job.name == "Test Job"
        assert job.source_directories == ["/source1", "/source2"]
        assert job.target_directory == "/target"
        assert job.mode == BatchMode.PARALLEL
        assert job.max_concurrent == 5
        assert job.job_id in batch_processor.jobs
    
    def test_schedule_job(self, batch_processor):
        """Test scheduling a batch job."""
        # Create job first
        job = batch_processor.create_job(
            name="Scheduled Job",
            source_directories=["/source"],
            target_directory="/target"
        )
        
        # Schedule job
        task = batch_processor.schedule_job(
            job.job_id,
            ScheduleType.DAILY,
            {"hour": 2, "minute": 30}
        )
        
        assert task.job_id == job.job_id
        assert task.schedule_type == ScheduleType.DAILY
        assert task.schedule_config["hour"] == 2
        assert task.schedule_config["minute"] == 30
        assert task.next_run is not None
    
    def test_calculate_next_run_daily(self, batch_processor):
        """Test calculating next run time for daily schedule."""
        task = ScheduledTask(
            task_id="test",
            name="Test Task",
            job_id="job1",
            schedule_type=ScheduleType.DAILY,
            schedule_config={"hour": 10, "minute": 30}
        )
        
        next_run = batch_processor._calculate_next_run(task)
        
        assert next_run is not None
        assert next_run.hour == 10
        assert next_run.minute == 30
        assert next_run > datetime.now()
    
    def test_calculate_next_run_interval(self, batch_processor):
        """Test calculating next run time for interval schedule."""
        task = ScheduledTask(
            task_id="test",
            name="Test Task",
            job_id="job1",
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={"interval_minutes": 60}
        )
        
        next_run = batch_processor._calculate_next_run(task)
        
        assert next_run is not None
        expected_time = datetime.now() + timedelta(minutes=60)
        # Allow 1 minute tolerance
        assert abs((next_run - expected_time).total_seconds()) < 60
    
    def test_get_job_status(self, batch_processor):
        """Test getting job status."""
        job = batch_processor.create_job(
            name="Status Test Job",
            source_directories=["/source"],
            target_directory="/target"
        )
        
        status = batch_processor.get_job_status(job.job_id)
        
        assert status['job_id'] == job.job_id
        assert status['name'] == "Status Test Job"
        assert status['is_running'] is False
        assert status['enabled'] is True
    
    def test_list_jobs(self, batch_processor):
        """Test listing batch jobs."""
        # Create multiple jobs
        job1 = batch_processor.create_job("Job 1", ["/src1"], "/tgt1")
        job2 = batch_processor.create_job("Job 2", ["/src2"], "/tgt2")
        
        jobs = batch_processor.list_jobs()
        
        assert len(jobs) == 2
        job_names = [job['name'] for job in jobs]
        assert "Job 1" in job_names
        assert "Job 2" in job_names
    
    def test_list_scheduled_tasks(self, batch_processor):
        """Test listing scheduled tasks."""
        # Create job and schedule it
        job = batch_processor.create_job("Scheduled Job", ["/src"], "/tgt")
        task = batch_processor.schedule_job(
            job.job_id,
            ScheduleType.WEEKLY,
            {"weekday": 1, "hour": 9, "minute": 0}
        )
        
        tasks = batch_processor.list_scheduled_tasks()
        
        assert len(tasks) == 1
        assert tasks[0]['task_id'] == task.task_id
        assert tasks[0]['schedule_type'] == "weekly"


class TestPerformanceMonitor:
    """Test performance monitoring functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def monitor(self, temp_dir):
        """Create performance monitor instance."""
        return PerformanceMonitor(
            monitoring_interval=0.1,  # Fast interval for testing
            storage_dir=temp_dir / "performance"
        )
    
    def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping monitoring."""
        assert not monitor.monitoring_active
        
        monitor.start_monitoring()
        assert monitor.monitoring_active
        assert monitor.baseline_snapshot is not None
        
        monitor.stop_monitoring()
        assert not monitor.monitoring_active
    
    def test_operation_tracking(self, monitor):
        """Test tracking operation performance."""
        tracking_id = monitor.start_operation_tracking("test_operation")
        
        assert tracking_id in monitor.active_metrics
        assert monitor.active_metrics[tracking_id].operation_name == "test_operation"
        
        # Update metrics
        monitor.update_operation_metrics(
            tracking_id,
            files_processed=10,
            bytes_processed=1024,
            success_count=9,
            error_count=1
        )
        
        metrics = monitor.active_metrics[tracking_id]
        assert metrics.files_processed == 10
        assert metrics.bytes_processed == 1024
        assert metrics.success_count == 9
        assert metrics.error_count == 1
        
        # Finish tracking
        final_metrics = monitor.finish_operation_tracking(tracking_id)
        
        assert final_metrics is not None
        assert final_metrics.duration_seconds > 0
        assert final_metrics.success_rate == 90.0  # 9/10 * 100
        assert tracking_id not in monitor.active_metrics
        assert final_metrics in monitor.completed_metrics
    
    def test_performance_context(self, monitor):
        """Test performance context manager."""
        with PerformanceContext("context_test", monitor) as ctx:
            ctx.update_metrics(files_processed=5, success_count=5)
        
        # Should have completed metrics after context exit
        assert len(monitor.completed_metrics) == 1
        metrics = monitor.completed_metrics[0]
        assert metrics.operation_name == "context_test"
        assert metrics.files_processed == 5
        assert metrics.success_count == 5
    
    def test_resource_snapshot(self, monitor):
        """Test taking resource snapshots."""
        snapshot = monitor.get_current_resources()
        
        assert isinstance(snapshot, ResourceSnapshot)
        assert snapshot.timestamp is not None
        assert snapshot.cpu_percent >= 0
        assert snapshot.memory_percent >= 0
    
    def test_resource_history(self, monitor):
        """Test resource history tracking."""
        monitor.start_monitoring()
        
        # Wait for some snapshots
        import time
        time.sleep(0.3)
        
        monitor.stop_monitoring()
        
        history = monitor.get_resource_history(hours=1)
        assert len(history) > 0
        
        # Test statistics
        stats = monitor.get_resource_statistics(hours=1)
        assert 'cpu' in stats
        assert 'memory' in stats
        assert 'disk' in stats
    
    def test_performance_summary(self, monitor):
        """Test performance summary generation."""
        # Add some completed metrics
        tracking_id = monitor.start_operation_tracking("summary_test")
        monitor.update_operation_metrics(tracking_id, files_processed=100, success_count=95, error_count=5)
        monitor.finish_operation_tracking(tracking_id)
        
        summary = monitor.get_performance_summary()
        
        assert summary['completed_operations'] == 1
        assert summary['total_files_processed'] == 100
        assert 'avg_success_rate' in summary
        assert 'system_info' in summary
    
    def test_export_performance_report(self, monitor):
        """Test exporting performance report."""
        # Add some data
        tracking_id = monitor.start_operation_tracking("report_test")
        monitor.finish_operation_tracking(tracking_id)
        
        report = monitor.export_performance_report(include_raw_data=True)
        
        assert 'report_timestamp' in report
        assert 'system_info' in report
        assert 'performance_summary' in report
        assert 'completed_operations' in report
        assert 'raw_data' in report
    
    def test_save_performance_report(self, monitor):
        """Test saving performance report to file."""
        report_file = monitor.save_performance_report("test_report.json")
        
        assert report_file.exists()
        assert report_file.name == "test_report.json"
        
        # Verify file content
        with open(report_file) as f:
            report_data = json.load(f)
        
        assert 'report_timestamp' in report_data
        assert 'system_info' in report_data


class TestIntegration:
    """Integration tests for performance optimization features."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_progress_persistence(self, temp_dir):
        """Test batch processing with progress persistence integration."""
        # Create batch processor and progress persistence
        batch_processor = BatchProcessor(storage_dir=temp_dir / "batch")
        progress_persistence = ProgressPersistence(persistence_dir=temp_dir / "progress")
        
        # Create a job
        job = batch_processor.create_job(
            name="Integration Test Job",
            source_directories=[str(temp_dir / "source")],
            target_directory=str(temp_dir / "target")
        )
        
        # Start a session
        session = progress_persistence.start_session(
            total_files=10,
            metadata={"job_id": job.job_id}
        )
        
        # Simulate some progress
        progress_persistence.update_session(processed_file="file1.mp4")
        progress_persistence.update_session(processed_file="file2.mp4")
        
        # Verify integration
        progress = progress_persistence.get_session_progress()
        assert progress['session_metadata']['job_id'] == job.job_id
        assert progress['processed_files'] == 2
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_with_duplicate_detection(self, temp_dir):
        """Test performance monitoring during duplicate detection."""
        # Create performance monitor and duplicate detector
        monitor = PerformanceMonitor(storage_dir=temp_dir / "performance")
        detector = DuplicateDetector(cache_file=temp_dir / "cache.json")
        
        # Create sample files
        sample_files = []
        for i in range(3):
            file_path = temp_dir / f"test_{i}.mp4"
            file_path.write_text(f"content {i}")
            
            video_file = VideoFile(
                file_path=str(file_path),
                filename=f"test_{i}.mp4",
                file_size=file_path.stat().st_size,
                extension=".mp4"
            )
            sample_files.append(video_file)
        
        # Monitor duplicate detection
        with PerformanceContext("duplicate_detection", monitor):
            report = await detector.detect_duplicates(sample_files)
        
        # Verify monitoring captured the operation
        assert len(monitor.completed_metrics) == 1
        metrics = monitor.completed_metrics[0]
        assert metrics.operation_name == "duplicate_detection"
        assert metrics.duration_seconds > 0
    
    def test_comprehensive_system_status(self, temp_dir):
        """Test getting comprehensive system status from all components."""
        # Initialize all components
        batch_processor = BatchProcessor(storage_dir=temp_dir / "batch")
        progress_persistence = ProgressPersistence(persistence_dir=temp_dir / "progress")
        monitor = PerformanceMonitor(storage_dir=temp_dir / "performance")
        detector = DuplicateDetector(cache_file=temp_dir / "cache.json")
        
        # Create some data
        job = batch_processor.create_job("Status Test", ["/src"], "/tgt")
        session = progress_persistence.start_session(total_files=5)
        tracking_id = monitor.start_operation_tracking("status_test")
        
        # Get status from all components
        batch_status = batch_processor.get_system_status()
        progress_status = progress_persistence.get_session_progress()
        performance_status = monitor.get_performance_summary()
        cache_status = detector.get_cache_stats()
        
        # Verify all components provide status
        assert batch_status['total_jobs'] == 1
        assert progress_status['total_files'] == 5
        assert performance_status['active_operations'] == 1
        assert 'cached_files' in cache_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])