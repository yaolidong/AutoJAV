"""Comprehensive error handling and recovery system."""

import logging
import traceback
import asyncio
from typing import Optional, Dict, Any, Callable, List, Type, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

from .logging_config import get_logger


# Custom Exception Classes
class AVScraperError(Exception):
    """Base exception for AV Scraper errors."""
    pass


class ScrapingError(AVScraperError):
    """Exception raised during scraping operations."""
    pass


class NetworkError(AVScraperError):
    """Exception raised for network-related errors."""
    pass


class FileOperationError(AVScraperError):
    """Exception raised for file operation errors."""
    pass


class ConfigurationError(AVScraperError):
    """Exception raised for configuration-related errors."""
    pass


class LoginError(AVScraperError):
    """Exception raised for login-related errors."""
    pass


class ValidationError(AVScraperError):
    """Exception raised for validation errors."""
    pass


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    PARSING = "parsing"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Information about an error occurrence."""
    error_id: str
    timestamp: datetime
    exception: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False
    resolution_strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to dictionary."""
        return {
            'error_id': self.error_id,
            'timestamp': self.timestamp.isoformat(),
            'exception_type': type(self.exception).__name__,
            'exception_message': str(self.exception),
            'category': self.category.value,
            'severity': self.severity.value,
            'context': self.context,
            'retry_count': self.retry_count,
            'resolved': self.resolved,
            'resolution_strategy': self.resolution_strategy
        }


class RetryStrategy:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_backoff: bool = True,
        jitter: bool = True
    ):
        """
        Initialize retry strategy.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries
            exponential_backoff: Use exponential backoff
            jitter: Add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt.
        
        Args:
            attempt: Attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
        
        return delay


class ErrorHandler:
    """
    Comprehensive error handling and recovery system.
    
    Provides centralized error handling, classification, retry mechanisms,
    and recovery strategies for the application.
    """
    
    def __init__(
        self,
        default_retry_strategy: Optional[RetryStrategy] = None,
        max_error_history: int = 1000,
        error_reporting_enabled: bool = True
    ):
        """
        Initialize error handler.
        
        Args:
            default_retry_strategy: Default retry configuration
            max_error_history: Maximum number of errors to keep in history
            error_reporting_enabled: Enable error reporting and logging
        """
        self.default_retry_strategy = default_retry_strategy or RetryStrategy()
        self.max_error_history = max_error_history
        self.error_reporting_enabled = error_reporting_enabled
        
        self.logger = get_logger(__name__)
        
        # Error tracking
        self.error_history: List[ErrorInfo] = []
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[Type[Exception], Callable] = {}
        
        # Statistics
        self.stats = {
            'total_errors': 0,
            'resolved_errors': 0,
            'retry_attempts': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }
        
        # Register default recovery strategies
        self._register_default_strategies()
    
    def handle_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        retry_strategy: Optional[RetryStrategy] = None
    ) -> ErrorInfo:
        """
        Handle an error with classification and potential recovery.
        
        Args:
            exception: The exception that occurred
            context: Additional context information
            category: Error category (auto-detected if None)
            severity: Error severity (auto-detected if None)
            retry_strategy: Custom retry strategy
            
        Returns:
            ErrorInfo object with error details
        """
        # Generate unique error ID
        error_id = self._generate_error_id(exception)
        
        # Auto-detect category and severity if not provided
        if category is None:
            category = self._classify_error(exception)
        
        if severity is None:
            severity = self._assess_severity(exception, category)
        
        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            exception=exception,
            category=category,
            severity=severity,
            context=context or {}
        )
        
        # Update statistics
        self.stats['total_errors'] += 1
        self.error_counts[type(exception).__name__] = (
            self.error_counts.get(type(exception).__name__, 0) + 1
        )
        
        # Log error
        if self.error_reporting_enabled:
            self._log_error(error_info)
        
        # Add to history
        self._add_to_history(error_info)
        
        # Attempt recovery
        if self._should_attempt_recovery(error_info):
            self._attempt_recovery(error_info, retry_strategy)
        
        return error_info
    
    def retry_with_backoff(
        self,
        func: Callable,
        *args,
        retry_strategy: Optional[RetryStrategy] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with retry and backoff logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            retry_strategy: Custom retry strategy
            context: Error context information
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        strategy = retry_strategy or self.default_retry_strategy
        last_exception = None
        
        for attempt in range(strategy.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Handle the error
                error_info = self.handle_error(
                    e,
                    context={**(context or {}), 'attempt': attempt + 1, 'function': func.__name__},
                    retry_strategy=strategy
                )
                
                error_info.retry_count = attempt + 1
                self.stats['retry_attempts'] += 1
                
                # Don't retry on the last attempt
                if attempt == strategy.max_attempts - 1:
                    break
                
                # Calculate delay and wait
                delay = strategy.get_delay(attempt)
                self.logger.warning(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1})")
                
                import time
                time.sleep(delay)
        
        # All retries failed
        raise last_exception
    
    async def async_retry_with_backoff(
        self,
        func: Callable,
        *args,
        retry_strategy: Optional[RetryStrategy] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute async function with retry and backoff logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            retry_strategy: Custom retry strategy
            context: Error context information
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        strategy = retry_strategy or self.default_retry_strategy
        last_exception = None
        
        for attempt in range(strategy.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Handle the error
                error_info = self.handle_error(
                    e,
                    context={**(context or {}), 'attempt': attempt + 1, 'function': func.__name__},
                    retry_strategy=strategy
                )
                
                error_info.retry_count = attempt + 1
                self.stats['retry_attempts'] += 1
                
                # Don't retry on the last attempt
                if attempt == strategy.max_attempts - 1:
                    break
                
                # Calculate delay and wait
                delay = strategy.get_delay(attempt)
                self.logger.warning(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1})")
                
                await asyncio.sleep(delay)
        
        # All retries failed
        raise last_exception
    
    def register_recovery_strategy(
        self,
        exception_type: Type[Exception],
        recovery_func: Callable[[Exception, Dict[str, Any]], bool]
    ) -> None:
        """
        Register a recovery strategy for a specific exception type.
        
        Args:
            exception_type: Type of exception to handle
            recovery_func: Function that attempts recovery
        """
        self.recovery_strategies[exception_type] = recovery_func
        self.logger.debug(f"Registered recovery strategy for {exception_type.__name__}")
    
    def _generate_error_id(self, exception: Exception) -> str:
        """Generate unique error ID."""
        import hashlib
        
        error_string = f"{type(exception).__name__}:{str(exception)}:{datetime.now().isoformat()}"
        return hashlib.md5(error_string.encode()).hexdigest()[:8]
    
    def _classify_error(self, exception: Exception) -> ErrorCategory:
        """Classify error into category based on exception type."""
        exception_type = type(exception)
        
        # Network-related errors
        if any(name in exception_type.__name__.lower() for name in 
               ['connection', 'timeout', 'http', 'url', 'socket', 'network']):
            return ErrorCategory.NETWORK
        
        # File system errors
        if any(name in exception_type.__name__.lower() for name in 
               ['file', 'io', 'permission', 'path', 'directory']):
            return ErrorCategory.FILE_SYSTEM
        
        # Parsing errors
        if any(name in exception_type.__name__.lower() for name in 
               ['parse', 'json', 'xml', 'decode', 'format']):
            return ErrorCategory.PARSING
        
        # Authentication errors
        if any(name in exception_type.__name__.lower() for name in 
               ['auth', 'login', 'credential', 'token', 'unauthorized']):
            return ErrorCategory.AUTHENTICATION
        
        # Validation errors
        if any(name in exception_type.__name__.lower() for name in 
               ['validation', 'value', 'type', 'attribute']):
            return ErrorCategory.VALIDATION
        
        # Configuration errors
        if any(name in exception_type.__name__.lower() for name in 
               ['config', 'setting', 'parameter']):
            return ErrorCategory.CONFIGURATION
        
        # Resource errors
        if any(name in exception_type.__name__.lower() for name in 
               ['memory', 'resource', 'limit', 'quota']):
            return ErrorCategory.RESOURCE
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, exception: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity based on exception and category."""
        exception_name = type(exception).__name__.lower()
        
        # Critical errors
        if any(name in exception_name for name in ['critical', 'fatal', 'system']):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.HIGH
        
        if any(name in exception_name for name in ['permission', 'access', 'security']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.NETWORK, ErrorCategory.FILE_SYSTEM]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors (parsing, validation, etc.)
        return ErrorSeverity.LOW
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error information."""
        log_level = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"Error {error_info.error_id}: {error_info.exception}",
            extra={
                'error_id': error_info.error_id,
                'category': error_info.category.value,
                'severity': error_info.severity.value,
                'context': error_info.context,
                'exception_type': type(error_info.exception).__name__,
                'traceback': traceback.format_exc()
            }
        )
    
    def _add_to_history(self, error_info: ErrorInfo) -> None:
        """Add error to history with size limit."""
        self.error_history.append(error_info)
        
        # Maintain history size limit
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
    
    def _should_attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Determine if recovery should be attempted."""
        # Don't attempt recovery for critical errors
        if error_info.severity == ErrorSeverity.CRITICAL:
            return False
        
        # Check if we have a recovery strategy
        return type(error_info.exception) in self.recovery_strategies
    
    def _attempt_recovery(self, error_info: ErrorInfo, retry_strategy: Optional[RetryStrategy]) -> None:
        """Attempt to recover from error."""
        exception_type = type(error_info.exception)
        
        if exception_type not in self.recovery_strategies:
            return
        
        try:
            recovery_func = self.recovery_strategies[exception_type]
            success = recovery_func(error_info.exception, error_info.context)
            
            if success:
                error_info.resolved = True
                error_info.resolution_strategy = recovery_func.__name__
                self.stats['successful_recoveries'] += 1
                self.stats['resolved_errors'] += 1
                
                self.logger.info(f"Successfully recovered from error {error_info.error_id}")
            else:
                self.stats['failed_recoveries'] += 1
                self.logger.warning(f"Recovery failed for error {error_info.error_id}")
                
        except Exception as recovery_error:
            self.stats['failed_recoveries'] += 1
            self.logger.error(f"Recovery strategy failed: {recovery_error}")
    
    def _register_default_strategies(self) -> None:
        """Register default recovery strategies."""
        
        def network_recovery(exception: Exception, context: Dict[str, Any]) -> bool:
            """Basic network error recovery."""
            # Could implement connection reset, proxy switching, etc.
            self.logger.info("Attempting network recovery...")
            return False  # Placeholder - implement actual recovery logic
        
        def file_recovery(exception: Exception, context: Dict[str, Any]) -> bool:
            """Basic file system error recovery."""
            # Could implement directory creation, permission fixes, etc.
            self.logger.info("Attempting file system recovery...")
            return False  # Placeholder - implement actual recovery logic
        
        # Register strategies for common exception types
        import socket
        self.register_recovery_strategy(ConnectionError, network_recovery)
        self.register_recovery_strategy(socket.timeout, network_recovery)
        self.register_recovery_strategy(FileNotFoundError, file_recovery)
        self.register_recovery_strategy(PermissionError, file_recovery)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        recent_errors = [
            error for error in self.error_history
            if error.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        return {
            'total_errors': self.stats['total_errors'],
            'resolved_errors': self.stats['resolved_errors'],
            'retry_attempts': self.stats['retry_attempts'],
            'successful_recoveries': self.stats['successful_recoveries'],
            'failed_recoveries': self.stats['failed_recoveries'],
            'resolution_rate': (
                self.stats['resolved_errors'] / max(1, self.stats['total_errors'])
            ) * 100,
            'recent_errors_24h': len(recent_errors),
            'error_counts_by_type': self.error_counts.copy(),
            'error_history_size': len(self.error_history),
            'registered_strategies': len(self.recovery_strategies)
        }
    
    def get_recent_errors(self, hours: int = 24) -> List[ErrorInfo]:
        """
        Get recent errors within specified time window.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent error info objects
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            error for error in self.error_history
            if error.timestamp > cutoff_time
        ]
    
    def clear_error_history(self) -> None:
        """Clear error history and reset statistics."""
        self.error_history.clear()
        self.error_counts.clear()
        
        for key in self.stats:
            self.stats[key] = 0
        
        self.logger.info("Error history and statistics cleared")


def retry_on_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_backoff: bool = True,
    exceptions: Union[Type[Exception], tuple] = Exception
):
    """
    Decorator for automatic retry on error.
    
    Args:
        max_attempts: Maximum retry attempts
        base_delay: Base delay between retries
        exponential_backoff: Use exponential backoff
        exceptions: Exception types to retry on
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            retry_strategy = RetryStrategy(
                max_attempts=max_attempts,
                base_delay=base_delay,
                exponential_backoff=exponential_backoff
            )
            
            return error_handler.retry_with_backoff(
                func, *args, retry_strategy=retry_strategy, **kwargs
            )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            retry_strategy = RetryStrategy(
                max_attempts=max_attempts,
                base_delay=base_delay,
                exponential_backoff=exponential_backoff
            )
            
            return await error_handler.async_retry_with_backoff(
                func, *args, retry_strategy=retry_strategy, **kwargs
            )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """
    Get global error handler instance.
    
    Returns:
        Global ErrorHandler instance
    """
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    
    return _global_error_handler


def handle_error(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None
) -> ErrorInfo:
    """
    Handle error using global error handler.
    
    Args:
        exception: Exception to handle
        context: Error context
        category: Error category
        severity: Error severity
        
    Returns:
        ErrorInfo object
    """
    return get_error_handler().handle_error(exception, context, category, severity)