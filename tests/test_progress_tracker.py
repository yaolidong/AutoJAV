"""Tests for progress tracking system."""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.utils.progress_tracker import (
    ProgressTracker, TaskProgress, TaskStatus, ProgressUnit,
    ProgressContext, get_progress_tracker
)


class TestTaskProgress:
    """Test cases for TaskProgress."""
    
    def test_init(self):
        """Test TaskProgress initialization."""
        progress = TaskProgress(
            task_id="test_task",
            name="Test Task",
            total=100,
            unit=ProgressUnit.FILES
        )
        
        assert progress.task_id == "test_task"
        assert progress.name == "Test Task"
        assert progress.status == TaskStatus.PENDING
        assert progress.current == 0
        assert progress.total == 100
        assert progress.unit == ProgressUnit.FILES
        assert progress.start_time is None
        assert progress.end_time is None
    
    def test_progress_percentage_with_total(self):
        """Test progress percentage calculation with total."""
        progress = TaskProgress("test", "Test", total=100)
        progress.current = 25
        
        assert progress.progress_percentage == 25.0
    
    def test_progress_percentage_without_total(self):
        """Test progress percentage calculation without total."""
        progress = TaskProgress("test", "Test")
        progress.current = 25
        
        assert progress.progress_percentage is None
    
    def test_progress_percentage_zero_total(self):
        """Test progress percentage calculation with zero total."""
        progress = TaskProgress("test", "Test", total=0)
        progress.current = 25
        
        assert progress.progress_percentage is None
    
    def test_elapsed_time_not_started(self):
        """Test elapsed time when task not started."""
        progress = TaskProgress("test", "Test")
        
        assert progress.elapsed_time is None
    
    def test_elapsed_time_running(self):
        """Test elapsed time for running task."""
        start_time = datetime.now() - timedelta(seconds=30)
        progress = TaskProgress("test", "Test", start_time=start_time)
        
        elapsed = progress.elapsed_time
        assert elapsed is not None
        assert elapsed.total_seconds() >= 29  # Allow for small timing differences
    
    def test_elapsed_time_completed(self):
        """Test elapsed time for completed task."""
        start_time = datetime.now() - timedelta(seconds=60)
        end_time = datetime.now() - timedelta(seconds=30)
        
        progress = TaskProgress("test", "Test", start_time=start_time, end_time=end_time)
        
        elapsed = progress.elapsed_time
        assert elapsed is not None
        assert abs(elapsed.total_seconds() - 30) < 1  # Should be ~30 seconds
    
    def test_estimated_remaining_time(self):
        """Test estimated remaining time calculation."""
        start_time = datetime.now() - timedelta(seconds=30)
        progress = TaskProgress(
            "test", "Test", 
            total=100, 
            start_time=start_time,
            status=TaskStatus.RUNNING
        )
        progress.current = 25  # 25% complete
        
        remaining = progress.estimated_remaining_time
        assert remaining is not None
        # Should estimate ~90 seconds remaining (30s for 25%, so 120s total - 30s elapsed)
        assert 80 <= remaining.total_seconds() <= 100
    
    def test_estimated_remaining_time_no_progress(self):
        """Test estimated remaining time with no progress."""
        progress = TaskProgress("test", "Test", total=100, start_time=datetime.now())
        progress.current = 0
        
        assert progress.estimated_remaining_time is None
    
    def test_rate_calculation(self):
        """Test processing rate calculation."""
        start_time = datetime.now() - timedelta(seconds=10)
        progress = TaskProgress("test", "Test", start_time=start_time)
        progress.current = 50
        
        rate = progress.rate
        assert rate is not None
        assert 4.5 <= rate <= 5.5  # Should be ~5 items per second
    
    def test_rate_no_time(self):
        """Test rate calculation with no elapsed time."""
        progress = TaskProgress("test", "Test")
        progress.current = 50
        
        assert progress.rate is None
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        start_time = datetime.now()
        progress = TaskProgress(
            task_id="test_task",
            name="Test Task",
            status=TaskStatus.RUNNING,
            current=25,
            total=100,
            unit=ProgressUnit.FILES,
            start_time=start_time,
            metadata={"key": "value"}
        )
        
        result = progress.to_dict()
        
        assert result['task_id'] == "test_task"
        assert result['name'] == "Test Task"
        assert result['status'] == "running"
        assert result['current'] == 25
        assert result['total'] == 100
        assert result['unit'] == "files"
        assert result['progress_percentage'] == 25.0
        assert result['start_time'] == start_time.isoformat()
        assert result['metadata'] == {"key": "value"}


class TestProgressTracker:
    """Test cases for ProgressTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create ProgressTracker instance for testing."""
        return ProgressTracker(enable_logging=False)  # Disable logging for tests
    
    def test_init_default(self):
        """Test ProgressTracker initialization with defaults."""
        tracker = ProgressTracker()
        
        assert tracker.update_interval == 1.0
        assert tracker.max_history_size == 1000
        assert tracker.enable_logging is True
        assert len(tracker.active_tasks) == 0
        assert len(tracker.completed_tasks) == 0
    
    def test_init_custom(self):
        """Test ProgressTracker initialization with custom parameters."""
        tracker = ProgressTracker(
            update_interval=0.5,
            max_history_size=500,
            enable_logging=False
        )
        
        assert tracker.update_interval == 0.5
        assert tracker.max_history_size == 500
        assert tracker.enable_logging is False
    
    def test_start_task(self, tracker):
        """Test starting a new task."""
        task_progress = tracker.start_task(
            "task1",
            "Test Task",
            total=100,
            unit=ProgressUnit.FILES,
            metadata={"key": "value"}
        )
        
        assert isinstance(task_progress, TaskProgress)
        assert task_progress.task_id == "task1"
        assert task_progress.name == "Test Task"
        assert task_progress.status == TaskStatus.RUNNING
        assert task_progress.total == 100
        assert task_progress.unit == ProgressUnit.FILES
        assert task_progress.metadata == {"key": "value"}
        assert task_progress.start_time is not None
        
        assert "task1" in tracker.active_tasks
        assert tracker.stats['total_tasks_started'] == 1
    
    def test_start_duplicate_task(self, tracker):
        """Test starting task with duplicate ID."""
        tracker.start_task("task1", "First Task")
        
        with pytest.raises(ValueError, match="Task task1 is already active"):
            tracker.start_task("task1", "Second Task")
    
    def test_update_progress_absolute(self, tracker):
        """Test updating progress with absolute value."""
        tracker.start_task("task1", "Test Task", total=100)
        
        updated_progress = tracker.update_progress("task1", current=25)
        
        assert updated_progress is not None
        assert updated_progress.current == 25
    
    def test_update_progress_increment(self, tracker):
        """Test updating progress with increment."""
        tracker.start_task("task1", "Test Task", total=100)
        tracker.update_progress("task1", current=20)
        
        updated_progress = tracker.update_progress("task1", increment=5)
        
        assert updated_progress.current == 25
    
    def test_update_progress_with_metadata(self, tracker):
        """Test updating progress with metadata."""
        tracker.start_task("task1", "Test Task")
        
        updated_progress = tracker.update_progress(
            "task1", 
            current=10, 
            metadata={"step": "processing"}
        )
        
        assert updated_progress.current == 10
        assert updated_progress.metadata["step"] == "processing"
    
    def test_update_nonexistent_task(self, tracker):
        """Test updating non-existent task."""
        result = tracker.update_progress("nonexistent", current=10)
        
        assert result is None
    
    def test_complete_task_success(self, tracker):
        """Test completing task successfully."""
        tracker.start_task("task1", "Test Task")
        
        completed_progress = tracker.complete_task(
            "task1", 
            success=True, 
            final_metadata={"result": "success"}
        )
        
        assert completed_progress is not None
        assert completed_progress.status == TaskStatus.COMPLETED
        assert completed_progress.end_time is not None
        assert completed_progress.metadata["result"] == "success"
        
        assert "task1" not in tracker.active_tasks
        assert len(tracker.completed_tasks) == 1
        assert tracker.stats['total_tasks_completed'] == 1
    
    def test_complete_task_failure(self, tracker):
        """Test completing task with failure."""
        tracker.start_task("task1", "Test Task")
        
        completed_progress = tracker.complete_task(
            "task1", 
            success=False, 
            error_message="Task failed"
        )
        
        assert completed_progress.status == TaskStatus.FAILED
        assert completed_progress.error_message == "Task failed"
        assert tracker.stats['total_tasks_failed'] == 1
    
    def test_complete_nonexistent_task(self, tracker):
        """Test completing non-existent task."""
        result = tracker.complete_task("nonexistent")
        
        assert result is None
    
    def test_cancel_task(self, tracker):
        """Test cancelling a task."""
        tracker.start_task("task1", "Test Task")
        
        cancelled_progress = tracker.cancel_task("task1", "User cancelled")
        
        assert cancelled_progress is not None
        assert cancelled_progress.status == TaskStatus.CANCELLED
        assert cancelled_progress.error_message == "User cancelled"
        assert cancelled_progress.end_time is not None
        
        assert "task1" not in tracker.active_tasks
        assert len(tracker.completed_tasks) == 1
        assert tracker.stats['total_tasks_cancelled'] == 1
    
    def test_pause_and_resume_task(self, tracker):
        """Test pausing and resuming a task."""
        tracker.start_task("task1", "Test Task")
        
        # Pause task
        paused_progress = tracker.pause_task("task1")
        assert paused_progress.status == TaskStatus.PAUSED
        
        # Resume task
        resumed_progress = tracker.resume_task("task1")
        assert resumed_progress.status == TaskStatus.RUNNING
    
    def test_get_task_progress(self, tracker):
        """Test getting task progress."""
        tracker.start_task("task1", "Test Task")
        
        progress = tracker.get_task_progress("task1")
        
        assert progress is not None
        assert progress.task_id == "task1"
    
    def test_get_task_progress_nonexistent(self, tracker):
        """Test getting progress for non-existent task."""
        progress = tracker.get_task_progress("nonexistent")
        
        assert progress is None
    
    def test_get_all_active_tasks(self, tracker):
        """Test getting all active tasks."""
        tracker.start_task("task1", "Task 1")
        tracker.start_task("task2", "Task 2")
        
        active_tasks = tracker.get_all_active_tasks()
        
        assert len(active_tasks) == 2
        task_ids = [task.task_id for task in active_tasks]
        assert "task1" in task_ids
        assert "task2" in task_ids
    
    def test_get_completed_tasks(self, tracker):
        """Test getting completed tasks."""
        tracker.start_task("task1", "Task 1")
        tracker.start_task("task2", "Task 2")
        
        tracker.complete_task("task1", success=True)
        tracker.complete_task("task2", success=False)
        
        completed_tasks = tracker.get_completed_tasks()
        
        assert len(completed_tasks) == 2
    
    def test_get_completed_tasks_with_limit(self, tracker):
        """Test getting completed tasks with limit."""
        for i in range(5):
            tracker.start_task(f"task{i}", f"Task {i}")
            tracker.complete_task(f"task{i}", success=True)
        
        completed_tasks = tracker.get_completed_tasks(limit=3)
        
        assert len(completed_tasks) == 3
    
    def test_get_overall_progress(self, tracker):
        """Test getting overall progress summary."""
        tracker.start_task("task1", "Task 1", total=100)
        tracker.start_task("task2", "Task 2", total=50)
        
        tracker.update_progress("task1", current=25)
        tracker.update_progress("task2", current=10)
        
        overall = tracker.get_overall_progress()
        
        assert overall['active_tasks'] == 2
        assert overall['total_items'] == 150
        assert overall['completed_items'] == 35
        assert overall['overall_percentage'] == (35 / 150) * 100
    
    def test_progress_callbacks(self, tracker):
        """Test progress update callbacks."""
        callback_calls = []
        
        def test_callback(task_progress):
            callback_calls.append(task_progress.task_id)
        
        tracker.add_progress_callback(test_callback)
        
        tracker.start_task("task1", "Test Task")
        tracker.update_progress("task1", current=10)
        
        assert len(callback_calls) == 2  # Start + update
        assert callback_calls[0] == "task1"
        assert callback_calls[1] == "task1"
    
    def test_remove_progress_callback(self, tracker):
        """Test removing progress callback."""
        callback_calls = []
        
        def test_callback(task_progress):
            callback_calls.append(task_progress.task_id)
        
        tracker.add_progress_callback(test_callback)
        tracker.remove_progress_callback(test_callback)
        
        tracker.start_task("task1", "Test Task")
        
        assert len(callback_calls) == 0  # Callback was removed
    
    def test_callback_error_handling(self, tracker):
        """Test error handling in callbacks."""
        def failing_callback(task_progress):
            raise Exception("Callback error")
        
        tracker.add_progress_callback(failing_callback)
        
        # Should not raise exception
        tracker.start_task("task1", "Test Task")
    
    def test_completed_tasks_history_limit(self):
        """Test completed tasks history size limit."""
        tracker = ProgressTracker(max_history_size=3, enable_logging=False)
        
        # Complete more tasks than the limit
        for i in range(5):
            tracker.start_task(f"task{i}", f"Task {i}")
            tracker.complete_task(f"task{i}", success=True)
        
        # Should only keep the last 3 tasks
        assert len(tracker.completed_tasks) == 3
        
        # Should keep the most recent tasks
        task_ids = [task.task_id for task in tracker.completed_tasks]
        assert "task2" in task_ids
        assert "task3" in task_ids
        assert "task4" in task_ids
    
    def test_clear_completed_tasks(self, tracker):
        """Test clearing completed tasks."""
        tracker.start_task("task1", "Task 1")
        tracker.start_task("task2", "Task 2")
        
        tracker.complete_task("task1", success=True)
        tracker.complete_task("task2", success=True)
        
        assert len(tracker.completed_tasks) == 2
        
        cleared_count = tracker.clear_completed_tasks()
        
        assert cleared_count == 2
        assert len(tracker.completed_tasks) == 0
    
    def test_export_progress_report(self, tracker):
        """Test exporting progress report."""
        tracker.start_task("task1", "Active Task", total=100)
        tracker.update_progress("task1", current=25)
        
        tracker.start_task("task2", "Completed Task")
        tracker.complete_task("task2", success=True)
        
        report = tracker.export_progress_report()
        
        assert 'timestamp' in report
        assert len(report['active_tasks']) == 1
        assert len(report['completed_tasks']) == 1
        assert 'overall_progress' in report
        assert 'statistics' in report
        
        # Check active task data
        active_task = report['active_tasks'][0]
        assert active_task['task_id'] == "task1"
        assert active_task['current'] == 25
        assert active_task['total'] == 100


class TestProgressContext:
    """Test cases for ProgressContext."""
    
    def test_context_manager_success(self):
        """Test progress context manager with successful execution."""
        tracker = ProgressTracker(enable_logging=False)
        
        with ProgressContext("task1", "Test Task", total=100, tracker=tracker) as ctx:
            assert "task1" in tracker.active_tasks
            ctx.update(current=50)
            
            task_progress = tracker.get_task_progress("task1")
            assert task_progress.current == 50
        
        # Task should be completed after context exit
        assert "task1" not in tracker.active_tasks
        assert len(tracker.completed_tasks) == 1
        assert tracker.completed_tasks[0].status == TaskStatus.COMPLETED
    
    def test_context_manager_with_exception(self):
        """Test progress context manager with exception."""
        tracker = ProgressTracker(enable_logging=False)
        
        with pytest.raises(ValueError):
            with ProgressContext("task1", "Test Task", tracker=tracker):
                raise ValueError("Test error")
        
        # Task should be marked as failed
        assert "task1" not in tracker.active_tasks
        assert len(tracker.completed_tasks) == 1
        assert tracker.completed_tasks[0].status == TaskStatus.FAILED
        assert "Test error" in tracker.completed_tasks[0].error_message
    
    def test_context_manager_metadata(self):
        """Test setting metadata in context manager."""
        tracker = ProgressTracker(enable_logging=False)
        
        with ProgressContext("task1", "Test Task", tracker=tracker) as ctx:
            ctx.set_metadata(step="processing", file="test.txt")
            
            task_progress = tracker.get_task_progress("task1")
            assert task_progress.metadata["step"] == "processing"
            assert task_progress.metadata["file"] == "test.txt"


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_progress_tracker(self):
        """Test getting global progress tracker."""
        tracker1 = get_progress_tracker()
        tracker2 = get_progress_tracker()
        
        assert isinstance(tracker1, ProgressTracker)
        assert tracker1 is tracker2  # Should return same instance


if __name__ == "__main__":
    pytest.main([__file__])