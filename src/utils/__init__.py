"""Utility functions and classes."""

from .logging_config import get_logger, LogLevel, setup_application_logging
from .error_handler import (
    ErrorHandler, AVScraperError, ScrapingError, NetworkError,
    FileOperationError, ConfigurationError, LoginError, ValidationError
)
from .progress_tracker import ProgressTracker, TaskProgress, TaskStatus, ProgressUnit
from .batch_processor import BatchProcessor
from .duplicate_detector import DuplicateDetector
from .performance_monitor import PerformanceMonitor
from .progress_persistence import ProgressPersistence

# Import optional utilities that may have external dependencies
__all__ = [
    'get_logger',
    'LogLevel', 
    'setup_application_logging',
    'ErrorHandler',
    'AVScraperError',
    'ScrapingError', 
    'NetworkError',
    'FileOperationError',
    'ConfigurationError',
    'LoginError',
    'ValidationError',
    'ProgressTracker',
    'TaskProgress',
    'TaskStatus',
    'ProgressUnit',
    'BatchProcessor',
    'DuplicateDetector',
    'PerformanceMonitor',
    'ProgressPersistence'
]

try:
    from .http_client import HttpClient
    __all__.append('HttpClient')
except ImportError:
    pass

try:
    from .webdriver_manager import WebDriverManager
    __all__.append('WebDriverManager')
except ImportError:
    pass

try:
    from .login_manager import LoginManager
    __all__.append('LoginManager')
except ImportError:
    pass