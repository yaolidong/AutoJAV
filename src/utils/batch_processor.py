"""Batch processing and scheduling system."""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

from .logging_config import get_logger
from .progress_tracker import ProgressTracker, ProgressContext, get_progress_tracker
from .progress_persistence import ProgressPersistence, get_progress_persistence
from ..models.video_file import VideoFile


class BatchMode(Enum):
    """Batch processing modes."""
    SEQUENTIAL = "sequential"  # Process files one by one
    PARALLEL = "parallel"  # Process files in parallel
    ADAPTIVE = "adaptive"  # Adapt based on system resources


class ScheduleType(Enum):
    """Types of scheduled tasks."""
    INTERVAL = "interval"  # Run at regular intervals
    DAILY = "daily"  # Run daily at specific time
    WEEKLY = "weekly"  # Run weekly on specific day/time
    CRON = "cron"  # Cron-like scheduling


@dataclass
class BatchJob:
    """Represents a batch processing job."""
    job_id: str
    name: str
    source_directories: List[str]
    target_directory: str
    mode: BatchMode = BatchMode.PARALLEL
    max_concurrent: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'job_id': self.job_id,
            'name': self.name,
            'source_directories': self.source_directories,
            'target_directory': self.target_directory,
            'mode': self.mode.value,
            'max_concurrent': self.max_concurrent,
            'created_at': self.created_at.isoformat(),
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'enabled': self.enabled,
            'config': self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchJob':
        """Create from dictionary."""
        return cls(
            job_id=data['job_id'],
            name=data['name'],
            source_directories=data['source_directories'],
            target_directory=data['target_directory'],
            mode=BatchMode(data['mode']),
            max_concurrent=data['max_concurrent'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_run=datetime.fromisoformat(data['last_run']) if data['last_run'] else None,
            next_run=datetime.fromisoformat(data['next_run']) if data['next_run'] else None,
            enabled=data['enabled'],
            config=data['config']
        )


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    task_id: str
    name: str
    job_id: str
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    run_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'job_id': self.job_id,
            'schedule_type': self.schedule_type.value,
            'schedule_config': self.schedule_config,
            'created_at': self.created_at.isoformat(),
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'enabled': self.enabled,
            'run_count': self.run_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduledTask':
        """Create from dictionary."""
        return cls(
            task_id=data['task_id'],
            name=data['name'],
            job_id=data['job_id'],
            schedule_type=ScheduleType(data['schedule_type']),
            schedule_config=data['schedule_config'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_run=datetime.fromisoformat(data['last_run']) if data['last_run'] else None,
            next_run=datetime.fromisoformat(data['next_run']) if data['next_run'] else None,
            enabled=data['enabled'],
            run_count=data['run_count']
        )


class BatchProcessor:
    """
    Advanced batch processing and scheduling system.
    
    Provides batch processing capabilities with scheduling,
    resource management, and progress tracking.
    """
    
    def __init__(
        self,
        storage_dir: Path = Path("./batch"),
        max_concurrent_jobs: int = 2,
        resource_monitor_interval: float = 30.0
    ):
        """
        Initialize batch processor.
        
        Args:
            storage_dir: Directory to store batch job configurations
            max_concurrent_jobs: Maximum concurrent batch jobs
            resource_monitor_interval: Resource monitoring interval in seconds
        """
        self.storage_dir = Path(storage_dir)
        self.max_concurrent_jobs = max_concurrent_jobs
        self.resource_monitor_interval = resource_monitor_interval
        
        self.logger = get_logger(__name__)
        self.progress_tracker = get_progress_tracker()
        self.progress_persistence = get_progress_persistence()
        
        # Job and task storage
        self.jobs: Dict[str, BatchJob] = {}
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        
        # Runtime state
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.scheduler_running = False
        
        # Resource monitoring
        self.system_resources = {
            'cpu_percent': 0.0,
            'memory_percent': 0.0,
            'disk_usage_percent': 0.0,
            'available_memory_gb': 0.0
        }
        
        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing jobs and tasks
        self._load_jobs_and_tasks()
        
        self.logger.info("Batch processor initialized")
    
    def create_job(
        self,
        name: str,
        source_directories: List[str],
        target_directory: str,
        mode: BatchMode = BatchMode.PARALLEL,
        max_concurrent: int = 3,
        config: Optional[Dict[str, Any]] = None
    ) -> BatchJob:
        """
        Create a new batch job.
        
        Args:
            name: Job name
            source_directories: List of source directories to process
            target_directory: Target directory for organized files
            mode: Processing mode
            max_concurrent: Maximum concurrent files to process
            config: Additional job configuration
            
        Returns:
            Created BatchJob
        """
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.jobs)}"
        
        job = BatchJob(
            job_id=job_id,
            name=name,
            source_directories=source_directories,
            target_directory=target_directory,
            mode=mode,
            max_concurrent=max_concurrent,
            config=config or {}
        )
        
        self.jobs[job_id] = job
        self._save_job(job)
        
        self.logger.info(f"Created batch job: {name} ({job_id})")
        return job
    
    def schedule_job(
        self,
        job_id: str,
        schedule_type: ScheduleType,
        schedule_config: Dict[str, Any],
        task_name: Optional[str] = None
    ) -> ScheduledTask:
        """
        Schedule a batch job to run automatically.
        
        Args:
            job_id: ID of the job to schedule
            schedule_type: Type of scheduling
            schedule_config: Schedule configuration
            task_name: Optional task name
            
        Returns:
            Created ScheduledTask
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.scheduled_tasks)}"
        task_name = task_name or f"Scheduled {self.jobs[job_id].name}"
        
        task = ScheduledTask(
            task_id=task_id,
            name=task_name,
            job_id=job_id,
            schedule_type=schedule_type,
            schedule_config=schedule_config
        )
        
        # Calculate next run time
        task.next_run = self._calculate_next_run(task)
        
        self.scheduled_tasks[task_id] = task
        self._save_task(task)
        
        # Start scheduler if not running
        if not self.scheduler_running:
            self.start_scheduler()
        
        self.logger.info(f"Scheduled job {job_id}: {task_name} ({task_id})")
        return task
    
    async def run_job(self, job_id: str, resume_session: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a batch job.
        
        Args:
            job_id: ID of the job to run
            resume_session: Optional session ID to resume
            
        Returns:
            Job execution results
        """
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.jobs[job_id]
        
        if job_id in self.running_jobs:
            raise ValueError(f"Job {job_id} is already running")
        
        self.logger.info(f"Starting batch job: {job.name} ({job_id})")
        
        # Create job task
        job_task = asyncio.create_task(
            self._execute_job(job, resume_session),
            name=f"batch_job_{job_id}"
        )
        
        self.running_jobs[job_id] = job_task
        
        try:
            result = await job_task
            job.last_run = datetime.now()
            self._save_job(job)
            return result
        finally:
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
    
    async def _execute_job(self, job: BatchJob, resume_session: Optional[str] = None) -> Dict[str, Any]:
        """Execute a batch job with progress tracking."""
        from ..main_application import AVMetadataScraper
        
        # Start or resume processing session
        if resume_session:
            session = self.progress_persistence.resume_session(resume_session)
            if not session:
                raise ValueError(f"Session {resume_session} not found")
        else:
            session = self.progress_persistence.start_session(
                total_files=0,  # Will be updated after scanning
                metadata={'job_id': job.job_id, 'job_name': job.name}
            )
        
        with ProgressContext(
            f"batch_job_{job.job_id}",
            f"Batch Job: {job.name}",
            tracker=self.progress_tracker
        ) as ctx:
            
            try:
                # Create application instance with job configuration
                app_config = {
                    'scanner': {
                        'source_directory': job.source_directories[0],  # Use first directory
                        'recursive': True
                    },
                    'organizer': {
                        'target_directory': job.target_directory
                    },
                    'processing': {
                        'max_concurrent_files': job.max_concurrent
                    }
                }
                app_config.update(job.config)
                
                # Initialize application
                app = AVMetadataScraper()
                
                # Override configuration
                app.config.update(app_config)
                app._initialize_components()
                
                # Run processing
                await app.start()
                
                # Get final statistics
                status = app.get_status()
                
                ctx.set_metadata(
                    files_processed=status['processing_stats']['files_processed'],
                    success_rate=status['processing_stats']['success_rate']
                )
                
                return {
                    'success': True,
                    'session_id': session.session_id if session else None,
                    'statistics': status['processing_stats']
                }
                
            except Exception as e:
                self.logger.error(f"Batch job {job.job_id} failed: {e}")
                ctx.set_metadata(error=str(e))
                
                return {
                    'success': False,
                    'error': str(e),
                    'session_id': session.session_id if session else None
                }
    
    def stop_job(self, job_id: str) -> bool:
        """
        Stop a running batch job.
        
        Args:
            job_id: ID of the job to stop
            
        Returns:
            True if job was stopped successfully
        """
        if job_id not in self.running_jobs:
            self.logger.warning(f"Job {job_id} is not running")
            return False
        
        job_task = self.running_jobs[job_id]
        job_task.cancel()
        
        self.logger.info(f"Stopped batch job: {job_id}")
        return True
    
    def start_scheduler(self) -> None:
        """Start the task scheduler."""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="batch_scheduler"
        )
        self.scheduler_thread.start()
        
        self.logger.info("Batch scheduler started")
    
    def stop_scheduler(self) -> None:
        """Stop the task scheduler."""
        self.scheduler_running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        
        self.logger.info("Batch scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self.scheduler_running:
            try:
                # Check for tasks that need to run
                current_time = datetime.now()
                
                for task in self.scheduled_tasks.values():
                    if (task.enabled and task.next_run and 
                        current_time >= task.next_run and
                        task.job_id not in self.running_jobs):
                        
                        # Run the task
                        asyncio.run_coroutine_threadsafe(
                            self._run_scheduled_task(task),
                            asyncio.get_event_loop()
                        )
                
                # Update system resources
                self._update_system_resources()
                
                # Sleep for a short interval
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(30)  # Wait longer on error
    
    async def _run_scheduled_task(self, task: ScheduledTask) -> None:
        """Run a scheduled task."""
        try:
            self.logger.info(f"Running scheduled task: {task.name}")
            
            # Update task state
            task.last_run = datetime.now()
            task.run_count += 1
            task.next_run = self._calculate_next_run(task)
            self._save_task(task)
            
            # Run the job
            result = await self.run_job(task.job_id)
            
            if result['success']:
                self.logger.info(f"Scheduled task completed successfully: {task.name}")
            else:
                self.logger.error(f"Scheduled task failed: {task.name} - {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error running scheduled task {task.name}: {e}")
    
    def _calculate_next_run(self, task: ScheduledTask) -> Optional[datetime]:
        """Calculate next run time for a scheduled task."""
        config = task.schedule_config
        current_time = datetime.now()
        
        if task.schedule_type == ScheduleType.INTERVAL:
            # Run at regular intervals
            interval_minutes = config.get('interval_minutes', 60)
            return current_time + timedelta(minutes=interval_minutes)
        
        elif task.schedule_type == ScheduleType.DAILY:
            # Run daily at specific time
            hour = config.get('hour', 0)
            minute = config.get('minute', 0)
            
            next_run = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= current_time:
                next_run += timedelta(days=1)
            
            return next_run
        
        elif task.schedule_type == ScheduleType.WEEKLY:
            # Run weekly on specific day/time
            weekday = config.get('weekday', 0)  # 0 = Monday
            hour = config.get('hour', 0)
            minute = config.get('minute', 0)
            
            days_ahead = weekday - current_time.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            next_run = current_time + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return next_run
        
        # For CRON type, would need more complex parsing
        return None
    
    def _update_system_resources(self) -> None:
        """Update system resource information."""
        try:
            import psutil
            
            self.system_resources.update({
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'available_memory_gb': psutil.virtual_memory().available / (1024**3)
            })
            
        except ImportError:
            # psutil not available, use placeholder values
            pass
        except Exception as e:
            self.logger.warning(f"Failed to update system resources: {e}")
    
    def _load_jobs_and_tasks(self) -> None:
        """Load jobs and tasks from storage."""
        try:
            # Load jobs
            jobs_file = self.storage_dir / "jobs.json"
            if jobs_file.exists():
                import json
                with open(jobs_file, 'r') as f:
                    jobs_data = json.load(f)
                
                for job_data in jobs_data:
                    job = BatchJob.from_dict(job_data)
                    self.jobs[job.job_id] = job
                
                self.logger.info(f"Loaded {len(self.jobs)} batch jobs")
            
            # Load tasks
            tasks_file = self.storage_dir / "tasks.json"
            if tasks_file.exists():
                import json
                with open(tasks_file, 'r') as f:
                    tasks_data = json.load(f)
                
                for task_data in tasks_data:
                    task = ScheduledTask.from_dict(task_data)
                    self.scheduled_tasks[task.task_id] = task
                
                self.logger.info(f"Loaded {len(self.scheduled_tasks)} scheduled tasks")
                
        except Exception as e:
            self.logger.error(f"Failed to load jobs and tasks: {e}")
    
    def _save_job(self, job: BatchJob) -> None:
        """Save a single job to storage."""
        self._save_all_jobs()
    
    def _save_task(self, task: ScheduledTask) -> None:
        """Save a single task to storage."""
        self._save_all_tasks()
    
    def _save_all_jobs(self) -> None:
        """Save all jobs to storage."""
        try:
            jobs_file = self.storage_dir / "jobs.json"
            jobs_data = [job.to_dict() for job in self.jobs.values()]
            
            import json
            with open(jobs_file, 'w') as f:
                json.dump(jobs_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save jobs: {e}")
    
    def _save_all_tasks(self) -> None:
        """Save all tasks to storage."""
        try:
            tasks_file = self.storage_dir / "tasks.json"
            tasks_data = [task.to_dict() for task in self.scheduled_tasks.values()]
            
            import json
            with open(tasks_file, 'w') as f:
                json.dump(tasks_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save tasks: {e}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a specific job."""
        if job_id not in self.jobs:
            return {'error': 'Job not found'}
        
        job = self.jobs[job_id]
        is_running = job_id in self.running_jobs
        
        return {
            'job_id': job_id,
            'name': job.name,
            'is_running': is_running,
            'last_run': job.last_run.isoformat() if job.last_run else None,
            'enabled': job.enabled,
            'source_directories': job.source_directories,
            'target_directory': job.target_directory,
            'mode': job.mode.value,
            'max_concurrent': job.max_concurrent
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            'total_jobs': len(self.jobs),
            'running_jobs': len(self.running_jobs),
            'scheduled_tasks': len(self.scheduled_tasks),
            'scheduler_running': self.scheduler_running,
            'system_resources': self.system_resources.copy(),
            'max_concurrent_jobs': self.max_concurrent_jobs
        }
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all batch jobs."""
        return [
            {
                'job_id': job.job_id,
                'name': job.name,
                'created_at': job.created_at.isoformat(),
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'enabled': job.enabled,
                'is_running': job.job_id in self.running_jobs
            }
            for job in self.jobs.values()
        ]
    
    def list_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        return [
            {
                'task_id': task.task_id,
                'name': task.name,
                'job_id': task.job_id,
                'schedule_type': task.schedule_type.value,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'run_count': task.run_count,
                'enabled': task.enabled
            }
            for task in self.scheduled_tasks.values()
        ]


# Global batch processor instance
_global_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """
    Get global batch processor instance.
    
    Returns:
        Global BatchProcessor instance
    """
    global _global_batch_processor
    
    if _global_batch_processor is None:
        _global_batch_processor = BatchProcessor()
    
    return _global_batch_processor