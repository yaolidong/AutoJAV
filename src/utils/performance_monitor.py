"""Performance monitoring and resource usage statistics system."""

import asyncio
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import json

from .logging_config import get_logger


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0
    thread_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_gb": self.memory_used_gb,
            "memory_available_gb": self.memory_available_gb,
            "disk_usage_percent": self.disk_usage_percent,
            "disk_free_gb": self.disk_free_gb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "process_count": self.process_count,
            "thread_count": self.thread_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceSnapshot":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            cpu_percent=data["cpu_percent"],
            memory_percent=data["memory_percent"],
            memory_used_gb=data["memory_used_gb"],
            memory_available_gb=data["memory_available_gb"],
            disk_usage_percent=data["disk_usage_percent"],
            disk_free_gb=data["disk_free_gb"],
            network_bytes_sent=data.get("network_bytes_sent", 0),
            network_bytes_recv=data.get("network_bytes_recv", 0),
            process_count=data.get("process_count", 0),
            thread_count=data.get("thread_count", 0),
        )


@dataclass
class PerformanceMetrics:
    """Performance metrics for a specific operation or time period."""

    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    files_processed: int = 0
    bytes_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0

    @property
    def throughput_files_per_second(self) -> float:
        """Calculate files processed per second."""
        if self.duration_seconds <= 0:
            return 0.0
        return self.files_processed / self.duration_seconds

    @property
    def throughput_mb_per_second(self) -> float:
        """Calculate MB processed per second."""
        if self.duration_seconds <= 0:
            return 0.0
        return (self.bytes_processed / (1024 * 1024)) / self.duration_seconds

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "files_processed": self.files_processed,
            "bytes_processed": self.bytes_processed,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_cpu_percent": self.avg_cpu_percent,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "throughput_files_per_second": self.throughput_files_per_second,
            "throughput_mb_per_second": self.throughput_mb_per_second,
            "success_rate": self.success_rate,
        }


class PerformanceMonitor:
    """
    Comprehensive performance monitoring and resource usage tracking system.

    Monitors system resources, tracks performance metrics, and provides
    detailed statistics for optimization and troubleshooting.
    """

    def __init__(
        self,
        monitoring_interval: float = 5.0,
        max_snapshots: int = 1000,
        enable_detailed_monitoring: bool = True,
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize performance monitor.

        Args:
            monitoring_interval: Interval between resource snapshots in seconds
            max_snapshots: Maximum number of snapshots to keep in memory
            enable_detailed_monitoring: Enable detailed system monitoring
            storage_dir: Directory to store performance data
        """
        self.monitoring_interval = monitoring_interval
        self.max_snapshots = max_snapshots
        self.enable_detailed_monitoring = enable_detailed_monitoring
        self.storage_dir = Path(storage_dir) if storage_dir else Path("./performance")

        self.logger = get_logger(__name__)

        # Resource snapshots (circular buffer)
        self.resource_snapshots: deque = deque(maxlen=max_snapshots)

        # Performance metrics
        self.active_metrics: Dict[str, PerformanceMetrics] = {}
        self.completed_metrics: List[PerformanceMetrics] = []

        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring_event = threading.Event()

        # Callbacks for real-time monitoring
        self.resource_callbacks: List[Callable[[ResourceSnapshot], None]] = []
        self.metrics_callbacks: List[Callable[[PerformanceMetrics], None]] = []

        # System information
        self.system_info = self._get_system_info()

        # Baseline measurements
        self.baseline_snapshot: Optional[ResourceSnapshot] = None

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("Performance monitor initialized")

    def start_monitoring(self) -> None:
        """Start continuous resource monitoring."""
        if self.monitoring_active:
            self.logger.warning("Monitoring is already active")
            return

        self.monitoring_active = True
        self.stop_monitoring_event.clear()

        # Take baseline snapshot
        self.baseline_snapshot = self._take_resource_snapshot()

        # Start monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True, name="performance_monitor"
        )
        self.monitor_thread.start()

        self.logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop continuous resource monitoring."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self.stop_monitoring_event.set()

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        self.logger.info("Performance monitoring stopped")

    def start_operation_tracking(self, operation_name: str) -> str:
        """
        Start tracking performance metrics for an operation.

        Args:
            operation_name: Name of the operation to track

        Returns:
            Tracking ID for the operation
        """
        tracking_id = f"{operation_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        metrics = PerformanceMetrics(
            operation_name=operation_name, start_time=datetime.now()
        )

        self.active_metrics[tracking_id] = metrics

        self.logger.debug(
            f"Started tracking operation: {operation_name} ({tracking_id})"
        )
        return tracking_id

    def update_operation_metrics(
        self,
        tracking_id: str,
        files_processed: Optional[int] = None,
        bytes_processed: Optional[int] = None,
        success_count: Optional[int] = None,
        error_count: Optional[int] = None,
    ) -> None:
        """
        Update metrics for an active operation.

        Args:
            tracking_id: Operation tracking ID
            files_processed: Number of files processed
            bytes_processed: Number of bytes processed
            success_count: Number of successful operations
            error_count: Number of failed operations
        """
        if tracking_id not in self.active_metrics:
            self.logger.warning(f"Unknown tracking ID: {tracking_id}")
            return

        metrics = self.active_metrics[tracking_id]

        if files_processed is not None:
            metrics.files_processed = files_processed
        if bytes_processed is not None:
            metrics.bytes_processed = bytes_processed
        if success_count is not None:
            metrics.success_count = success_count
        if error_count is not None:
            metrics.error_count = error_count

    def finish_operation_tracking(
        self, tracking_id: str
    ) -> Optional[PerformanceMetrics]:
        """
        Finish tracking an operation and calculate final metrics.

        Args:
            tracking_id: Operation tracking ID

        Returns:
            Final PerformanceMetrics or None if not found
        """
        if tracking_id not in self.active_metrics:
            self.logger.warning(f"Unknown tracking ID: {tracking_id}")
            return None

        metrics = self.active_metrics.pop(tracking_id)
        metrics.end_time = datetime.now()
        metrics.duration_seconds = (
            metrics.end_time - metrics.start_time
        ).total_seconds()

        # Calculate average CPU and peak memory from snapshots during operation
        operation_snapshots = [
            snapshot
            for snapshot in self.resource_snapshots
            if metrics.start_time <= snapshot.timestamp <= metrics.end_time
        ]

        if operation_snapshots:
            metrics.avg_cpu_percent = sum(
                s.cpu_percent for s in operation_snapshots
            ) / len(operation_snapshots)
            metrics.peak_memory_mb = max(
                s.memory_used_gb * 1024 for s in operation_snapshots
            )

            # Network usage during operation
            if len(operation_snapshots) > 1:
                first_snapshot = operation_snapshots[0]
                last_snapshot = operation_snapshots[-1]
                metrics.network_bytes_sent = (
                    last_snapshot.network_bytes_sent - first_snapshot.network_bytes_sent
                )
                metrics.network_bytes_recv = (
                    last_snapshot.network_bytes_recv - first_snapshot.network_bytes_recv
                )

        self.completed_metrics.append(metrics)

        # Notify callbacks
        for callback in self.metrics_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                self.logger.error(f"Error in metrics callback: {e}")

        self.logger.info(
            f"Completed operation tracking: {metrics.operation_name} "
            f"({metrics.duration_seconds:.2f}s, {metrics.throughput_files_per_second:.2f} files/s)"
        )

        return metrics

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active and not self.stop_monitoring_event.wait(
            self.monitoring_interval
        ):
            try:
                snapshot = self._take_resource_snapshot()
                self.resource_snapshots.append(snapshot)

                # Notify callbacks
                for callback in self.resource_callbacks:
                    try:
                        callback(snapshot)
                    except Exception as e:
                        self.logger.error(f"Error in resource callback: {e}")

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")

    def _take_resource_snapshot(self) -> ResourceSnapshot:
        """Take a snapshot of current system resources."""
        try:
            import psutil

            # Memory information
            memory = psutil.virtual_memory()

            # Disk information
            disk = psutil.disk_usage("/")

            # Network information
            network = psutil.net_io_counters()

            # Process information
            process_count = len(psutil.pids())

            # Current process thread count
            current_process = psutil.Process()
            thread_count = current_process.num_threads()

            return ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_used_gb=memory.used / (1024**3),
                memory_available_gb=memory.available / (1024**3),
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_free_gb=disk.free / (1024**3),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                process_count=process_count,
                thread_count=thread_count,
            )

        except ImportError:
            # psutil not available, return minimal snapshot
            return ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_gb=0.0,
                memory_available_gb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
            )
        except Exception as e:
            self.logger.error(f"Error taking resource snapshot: {e}")
            return ResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_gb=0.0,
                memory_available_gb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
            )

    def _get_system_info(self) -> Dict[str, Any]:
        """Get static system information."""
        try:
            import psutil
            import platform

            return {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "disk_total_gb": psutil.disk_usage("/").total / (1024**3),
                "python_version": platform.python_version(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            }

        except ImportError:
            import platform

            return {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "python_version": platform.python_version(),
            }
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {}

    def get_current_resources(self) -> ResourceSnapshot:
        """Get current resource usage snapshot."""
        return self._take_resource_snapshot()

    def get_resource_history(self, hours: int = 1) -> List[ResourceSnapshot]:
        """
        Get resource history for specified time period.

        Args:
            hours: Number of hours of history to return

        Returns:
            List of resource snapshots
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        return [
            snapshot
            for snapshot in self.resource_snapshots
            if snapshot.timestamp >= cutoff_time
        ]

    def get_resource_statistics(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get statistical summary of resource usage.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary with resource statistics
        """
        snapshots = self.get_resource_history(hours)

        if not snapshots:
            return {}

        # Calculate statistics
        cpu_values = [s.cpu_percent for s in snapshots]
        memory_values = [s.memory_percent for s in snapshots]
        disk_values = [s.disk_usage_percent for s in snapshots]

        return {
            "time_period_hours": hours,
            "snapshot_count": len(snapshots),
            "cpu": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
                "current": snapshots[-1].cpu_percent if snapshots else 0,
            },
            "memory": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values),
                "current": snapshots[-1].memory_percent if snapshots else 0,
            },
            "disk": {
                "min": min(disk_values),
                "max": max(disk_values),
                "avg": sum(disk_values) / len(disk_values),
                "current": snapshots[-1].disk_usage_percent if snapshots else 0,
            },
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance metrics."""
        active_operations = len(self.active_metrics)
        completed_operations = len(self.completed_metrics)

        if self.completed_metrics:
            # Calculate aggregate statistics
            total_files = sum(m.files_processed for m in self.completed_metrics)
            total_bytes = sum(m.bytes_processed for m in self.completed_metrics)
            total_duration = sum(m.duration_seconds for m in self.completed_metrics)

            avg_throughput_files = total_files / max(1, total_duration)
            avg_throughput_mb = (total_bytes / (1024 * 1024)) / max(1, total_duration)

            success_rates = [
                m.success_rate
                for m in self.completed_metrics
                if m.success_count + m.error_count > 0
            ]
            avg_success_rate = (
                sum(success_rates) / len(success_rates) if success_rates else 0
            )

        else:
            total_files = total_bytes = total_duration = 0
            avg_throughput_files = avg_throughput_mb = avg_success_rate = 0

        return {
            "monitoring_active": self.monitoring_active,
            "active_operations": active_operations,
            "completed_operations": completed_operations,
            "total_files_processed": total_files,
            "total_bytes_processed": total_bytes,
            "total_processing_time": total_duration,
            "avg_throughput_files_per_second": avg_throughput_files,
            "avg_throughput_mb_per_second": avg_throughput_mb,
            "avg_success_rate": avg_success_rate,
            "resource_snapshots": len(self.resource_snapshots),
            "system_info": self.system_info,
        }

    def export_performance_report(
        self, include_raw_data: bool = False
    ) -> Dict[str, Any]:
        """
        Export comprehensive performance report.

        Args:
            include_raw_data: Include raw snapshot and metrics data

        Returns:
            Performance report dictionary
        """
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "monitoring_period": {
                "start": self.baseline_snapshot.timestamp.isoformat()
                if self.baseline_snapshot
                else None,
                "end": datetime.now().isoformat(),
                "duration_hours": (
                    (datetime.now() - self.baseline_snapshot.timestamp).total_seconds()
                    / 3600
                    if self.baseline_snapshot
                    else 0
                ),
            },
            "system_info": self.system_info,
            "performance_summary": self.get_performance_summary(),
            "resource_statistics": self.get_resource_statistics(24),  # Last 24 hours
            "completed_operations": [
                m.to_dict() for m in self.completed_metrics[-50:]
            ],  # Last 50 operations
        }

        if include_raw_data:
            report["raw_data"] = {
                "resource_snapshots": [
                    s.to_dict() for s in list(self.resource_snapshots)[-100:]
                ],  # Last 100 snapshots
                "all_completed_metrics": [m.to_dict() for m in self.completed_metrics],
            }

        return report

    def save_performance_report(self, filename: Optional[str] = None) -> Path:
        """
        Save performance report to file.

        Args:
            filename: Optional filename (auto-generated if None)

        Returns:
            Path to saved report file
        """
        if filename is None:
            filename = (
                f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        report_file = self.storage_dir / filename
        report = self.export_performance_report(include_raw_data=True)

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Performance report saved: {report_file}")
        return report_file

    def add_resource_callback(
        self, callback: Callable[[ResourceSnapshot], None]
    ) -> None:
        """Add callback for resource updates."""
        self.resource_callbacks.append(callback)

    def add_metrics_callback(
        self, callback: Callable[[PerformanceMetrics], None]
    ) -> None:
        """Add callback for metrics updates."""
        self.metrics_callbacks.append(callback)

    def clear_history(self) -> None:
        """Clear all monitoring history."""
        self.resource_snapshots.clear()
        self.completed_metrics.clear()
        self.baseline_snapshot = None

        self.logger.info("Performance monitoring history cleared")


class PerformanceContext:
    """Context manager for automatic performance tracking."""

    def __init__(
        self, operation_name: str, monitor: Optional[PerformanceMonitor] = None
    ):
        """
        Initialize performance context.

        Args:
            operation_name: Name of the operation to track
            monitor: Performance monitor instance
        """
        self.operation_name = operation_name
        self.monitor = monitor or get_performance_monitor()
        self.tracking_id: Optional[str] = None

    def __enter__(self) -> "PerformanceContext":
        """Enter context and start tracking."""
        self.tracking_id = self.monitor.start_operation_tracking(self.operation_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and finish tracking."""
        if self.tracking_id:
            self.monitor.finish_operation_tracking(self.tracking_id)

    def update_metrics(self, **kwargs) -> None:
        """Update operation metrics."""
        if self.tracking_id:
            self.monitor.update_operation_metrics(self.tracking_id, **kwargs)


# Global performance monitor instance
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get global performance monitor instance.

    Returns:
        Global PerformanceMonitor instance
    """
    global _global_performance_monitor

    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()

    return _global_performance_monitor
