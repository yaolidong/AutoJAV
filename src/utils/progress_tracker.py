"""Progress tracking and status reporting system."""

import time
import threading
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from .logging_config import get_logger


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ProgressUnit(Enum):
    """Units for progress measurement."""
    COUNT = "count"
    BYTES = "bytes"
    PERCENTAGE = "percentage"
    FILES = "files"
    ITEMS = "items"


@dataclass
class TaskProgress:
    """Progress information for a task."""
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    current: int = 0
    total: Optional[int] = None
    unit: ProgressUnit = ProgressUnit.COUNT
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> Optional[float]:
        """Calculate progress percentage."""
        if self.total is None or self.total == 0:
            return None
        return (self.current / self.total) * 100
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Calculate elapsed time."""
        if self.start_time is None:
            return None
        
        end_time = self.end_time or datetime.now()
        return end_time - self.start_time
    
    @property
    def estimated_remaining_time(self) -> Optional[timedelta]:
        """Estimate remaining time based on current progress."""
        if (self.total is None or self.current == 0 or 
            self.start_time is None or self.status != TaskStatus.RUNNING):
            return None
        
        elapsed = self.elapsed_time
        if elapsed is None:
            return None
        
        progress_ratio = self.current / self.total
        if progress_ratio == 0:
            return None
        
        total_estimated_time = elapsed / progress_ratio
        return total_estimated_time - elapsed
    
    @property
    def rate(self) -> Optional[float]:
        """Calculate processing rate (items per second)."""
        elapsed = self.elapsed_time
        if elapsed is None or elapsed.total_seconds() == 0 or self.current == 0:
            return None
        
        return self.current / elapsed.total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': self.status.value,
            'current': self.current,
            'total': self.total,
            'unit': self.unit.value,
            'progress_percentage': self.progress_percentage,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'elapsed_time': str(self.elapsed_time) if self.elapsed_time else None,
            'estimated_remaining_time': str(self.estimated_remaining_time) if self.estimated_remaining_time else None,
            'rate': self.rate,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


class ProgressTracker:
    """
    Centralized progress tracking and status reporting system.
    
    Tracks progress of multiple concurrent tasks with real-time updates,
    statistics, and reporting capabilities.
    """
    
    def __init__(
        self,
        update_interval: float = 1.0,
        max_history_size: int = 1000,
        enable_logging: bool = True
    ):
        """
        Initialize progress tracker.
        
        Args:
            update_interval: Interval for progress updates in seconds
            max_history_size: Maximum number of completed tasks to keep in history
            enable_logging: Enable progress logging
        """
        self.update_interval = update_interval
        self.max_history_size = max_history_size
        self.enable_logging = enable_logging
        
        self.logger = get_logger(__name__)
        
        # Task tracking
        self.active_tasks: Dict[str, TaskProgress] = {}
        self.completed_tasks: List[TaskProgress] = []
        
        # Callbacks for progress updates
        self.progress_callbacks: List[Callable[[TaskProgress], None]] = []
        
        # Statistics
        self.stats = {
            'total_tasks_started': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'total_tasks_cancelled': 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Auto-update thread
        self._update_thread: Optional[threading.Thread] = None
        self._stop_updates = threading.Event()
        
        if self.enable_logging:
            self.logger.info("Progress tracker initialized")
    
    def start_task(
        self,
        task_id: str,
        name: str,
        total: Optional[int] = None,
        unit: ProgressUnit = ProgressUnit.COUNT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskProgress:
        """
        Start tracking a new task.
        
        Args:
            task_id: Unique task identifier
            name: Human-readable task name
            total: Total number of items to process
            unit: Unit of measurement
            metadata: Additional task metadata
            
        Returns:
            TaskProgress object for the new task
        """
        with self._lock:
            if task_id in self.active_tasks:
                raise ValueError(f"Task {task_id} is already active")
            
            task_progress = TaskProgress(
                task_id=task_id,
                name=name,
                status=TaskStatus.RUNNING,
                total=total,
                unit=unit,
                start_time=datetime.now(),
                metadata=metadata or {}
            )
            
            self.active_tasks[task_id] = task_progress
            self.stats['total_tasks_started'] += 1
            
            if self.enable_logging:
                self.logger.info(f"Started task '{name}' ({task_id})")
            
            self._notify_callbacks(task_progress)
            
            return task_progress
    
    def update_progress(
        self,
        task_id: str,
        current: Optional[int] = None,
        increment: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskProgress]:
        """
        Update task progress.
        
        Args:
            task_id: Task identifier
            current: New current value (absolute)
            increment: Amount to increment current value
            metadata: Additional metadata to update
            
        Returns:
            Updated TaskProgress object or None if task not found
        """
        with self._lock:
            if task_id not in self.active_tasks:
                self.logger.warning(f"Attempted to update non-existent task: {task_id}")
                return None
            
            task_progress = self.active_tasks[task_id]
            
            if current is not None:
                task_progress.current = current
            elif increment is not None:
                task_progress.current += increment
            
            if metadata:
                task_progress.metadata.update(metadata)
            
            self._notify_callbacks(task_progress)
            
            return task_progress
    
    def complete_task(
        self,
        task_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        final_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskProgress]:
        """
        Mark task as completed.
        
        Args:
            task_id: Task identifier
            success: Whether task completed successfully
            error_message: Error message if task failed
            final_metadata: Final metadata to add
            
        Returns:
            Completed TaskProgress object or None if task not found
        """
        with self._lock:
            if task_id not in self.active_tasks:
                self.logger.warning(f"Attempted to complete non-existent task: {task_id}")
                return None
            
            task_progress = self.active_tasks.pop(task_id)
            task_progress.end_time = datetime.now()
            task_progress.error_message = error_message
            
            if final_metadata:
                task_progress.metadata.update(final_metadata)
            
            if success:
                task_progress.status = TaskStatus.COMPLETED
                self.stats['total_tasks_completed'] += 1
                
                if self.enable_logging:
                    elapsed = task_progress.elapsed_time
                    self.logger.info(f"Completed task '{task_progress.name}' in {elapsed}")
            else:
                task_progress.status = TaskStatus.FAILED
                self.stats['total_tasks_failed'] += 1
                
                if self.enable_logging:
                    self.logger.error(f"Task '{task_progress.name}' failed: {error_message}")
            
            # Add to completed tasks history
            self.completed_tasks.append(task_progress)
            
            # Maintain history size limit
            if len(self.completed_tasks) > self.max_history_size:
                self.completed_tasks = self.completed_tasks[-self.max_history_size:]
            
            self._notify_callbacks(task_progress)
            
            return task_progress
    
    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> Optional[TaskProgress]:
        """
        Cancel an active task.
        
        Args:
            task_id: Task identifier
            reason: Cancellation reason
            
        Returns:
            Cancelled TaskProgress object or None if task not found
        """
        with self._lock:
            if task_id not in self.active_tasks:
                return None
            
            task_progress = self.active_tasks.pop(task_id)
            task_progress.status = TaskStatus.CANCELLED
            task_progress.end_time = datetime.now()
            task_progress.error_message = reason
            
            self.stats['total_tasks_cancelled'] += 1
            
            if self.enable_logging:
                self.logger.info(f"Cancelled task '{task_progress.name}': {reason}")
            
            self.completed_tasks.append(task_progress)
            self._notify_callbacks(task_progress)
            
            return task_progress
    
    def pause_task(self, task_id: str) -> Optional[TaskProgress]:
        """
        Pause an active task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Paused TaskProgress object or None if task not found
        """
        with self._lock:
            if task_id not in self.active_tasks:
                return None
            
            task_progress = self.active_tasks[task_id]
            task_progress.status = TaskStatus.PAUSED
            
            if self.enable_logging:
                self.logger.info(f"Paused task '{task_progress.name}'")
            
            self._notify_callbacks(task_progress)
            
            return task_progress
    
    def resume_task(self, task_id: str) -> Optional[TaskProgress]:
        """
        Resume a paused task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Resumed TaskProgress object or None if task not found
        """
        with self._lock:
            if task_id not in self.active_tasks:
                return None
            
            task_progress = self.active_tasks[task_id]
            if task_progress.status == TaskStatus.PAUSED:
                task_progress.status = TaskStatus.RUNNING
                
                if self.enable_logging:
                    self.logger.info(f"Resumed task '{task_progress.name}'")
                
                self._notify_callbacks(task_progress)
            
            return task_progress
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """
        Get progress for a specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskProgress object or None if not found
        """
        with self._lock:
            return self.active_tasks.get(task_id)
    
    def get_all_active_tasks(self) -> List[TaskProgress]:
        """
        Get all active tasks.
        
        Returns:
            List of active TaskProgress objects
        """
        with self._lock:
            return list(self.active_tasks.values())
    
    def get_completed_tasks(self, limit: Optional[int] = None) -> List[TaskProgress]:
        """
        Get completed tasks.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of completed TaskProgress objects
        """
        with self._lock:
            tasks = self.completed_tasks.copy()
            if limit:
                tasks = tasks[-limit:]
            return tasks
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """
        Get overall progress summary.
        
        Returns:
            Dictionary with overall progress information
        """
        with self._lock:
            active_tasks = list(self.active_tasks.values())
            
            # Calculate aggregate statistics
            total_items = sum(task.total or 0 for task in active_tasks if task.total)
            completed_items = sum(task.current for task in active_tasks)
            
            overall_percentage = None
            if total_items > 0:
                overall_percentage = (completed_items / total_items) * 100
            
            # Calculate average rate
            rates = [task.rate for task in active_tasks if task.rate is not None]
            average_rate = sum(rates) / len(rates) if rates else None
            
            return {
                'active_tasks': len(active_tasks),
                'completed_tasks': len(self.completed_tasks),
                'total_items': total_items,
                'completed_items': completed_items,
                'overall_percentage': overall_percentage,
                'average_rate': average_rate,
                'statistics': self.stats.copy()
            }
    
    def add_progress_callback(self, callback: Callable[[TaskProgress], None]) -> None:
        """
        Add callback for progress updates.
        
        Args:
            callback: Function to call on progress updates
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[TaskProgress], None]) -> None:
        """
        Remove progress callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def _notify_callbacks(self, task_progress: TaskProgress) -> None:
        """Notify all registered callbacks of progress update."""
        for callback in self.progress_callbacks:
            try:
                callback(task_progress)
            except Exception as e:
                self.logger.error(f"Error in progress callback: {e}")
    
    def start_auto_updates(self) -> None:
        """Start automatic progress updates thread."""
        if self._update_thread is not None and self._update_thread.is_alive():
            return
        
        self._stop_updates.clear()
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        
        if self.enable_logging:
            self.logger.debug("Started auto-update thread")
    
    def stop_auto_updates(self) -> None:
        """Stop automatic progress updates thread."""
        self._stop_updates.set()
        
        if self._update_thread is not None:
            self._update_thread.join(timeout=5.0)
            
        if self.enable_logging:
            self.logger.debug("Stopped auto-update thread")
    
    def _update_loop(self) -> None:
        """Main loop for automatic progress updates."""
        while not self._stop_updates.wait(self.update_interval):
            try:
                with self._lock:
                    for task_progress in self.active_tasks.values():
                        if task_progress.status == TaskStatus.RUNNING:
                            self._notify_callbacks(task_progress)
            except Exception as e:
                self.logger.error(f"Error in update loop: {e}")
    
    def clear_completed_tasks(self) -> int:
        """
        Clear completed tasks history.
        
        Returns:
            Number of tasks cleared
        """
        with self._lock:
            count = len(self.completed_tasks)
            self.completed_tasks.clear()
            
            if self.enable_logging:
                self.logger.info(f"Cleared {count} completed tasks")
            
            return count
    
    def export_progress_report(self) -> Dict[str, Any]:
        """
        Export comprehensive progress report.
        
        Returns:
            Dictionary with complete progress information
        """
        with self._lock:
            return {
                'timestamp': datetime.now().isoformat(),
                'active_tasks': [task.to_dict() for task in self.active_tasks.values()],
                'completed_tasks': [task.to_dict() for task in self.completed_tasks],
                'overall_progress': self.get_overall_progress(),
                'statistics': self.stats.copy()
            }


# Global progress tracker instance
_global_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """
    Get global progress tracker instance.
    
    Returns:
        Global ProgressTracker instance
    """
    global _global_progress_tracker
    
    if _global_progress_tracker is None:
        _global_progress_tracker = ProgressTracker()
    
    return _global_progress_tracker


class ProgressContext:
    """Context manager for automatic progress tracking."""
    
    def __init__(
        self,
        task_id: str,
        name: str,
        total: Optional[int] = None,
        unit: ProgressUnit = ProgressUnit.COUNT,
        tracker: Optional[ProgressTracker] = None
    ):
        """
        Initialize progress context.
        
        Args:
            task_id: Unique task identifier
            name: Task name
            total: Total items to process
            unit: Progress unit
            tracker: Progress tracker instance
        """
        self.task_id = task_id
        self.name = name
        self.total = total
        self.unit = unit
        self.tracker = tracker or get_progress_tracker()
        self.task_progress: Optional[TaskProgress] = None
    
    def __enter__(self) -> 'ProgressContext':
        """Enter context and start task tracking."""
        self.task_progress = self.tracker.start_task(
            self.task_id, self.name, self.total, self.unit
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and complete task tracking."""
        if self.task_progress:
            success = exc_type is None
            error_message = str(exc_val) if exc_val else None
            self.tracker.complete_task(self.task_id, success, error_message)
    
    def update(self, current: Optional[int] = None, increment: Optional[int] = None) -> None:
        """Update progress."""
        if self.task_progress:
            self.tracker.update_progress(self.task_id, current, increment)
    
    def set_metadata(self, **metadata) -> None:
        """Set task metadata."""
        if self.task_progress:
            self.tracker.update_progress(self.task_id, metadata=metadata)