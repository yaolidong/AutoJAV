"""Tests for error handling system."""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.utils.error_handler import (
    ErrorHandler, ErrorInfo, ErrorSeverity, ErrorCategory,
    RetryStrategy, retry_on_error, get_error_handler, handle_error
)


class TestRetryStrategy:
    """Test cases for RetryStrategy."""
    
    def test_init_default(self):
        """Test RetryStrategy initialization with defaults."""
        strategy = RetryStrategy()
        
        assert strategy.max_attempts == 3
        assert strategy.base_delay == 1.0
        assert strategy.max_delay == 60.0
        assert strategy.exponential_backoff is True
        assert strategy.jitter is True
    
    def test_init_custom(self):
        """Test RetryStrategy initialization with custom values."""
        strategy = RetryStrategy(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_backoff=False,
            jitter=False
        )
        
        assert strategy.max_attempts == 5
        assert strategy.base_delay == 2.0
        assert strategy.max_delay == 120.0
        assert strategy.exponential_backoff is False
        assert strategy.jitter is False
    
    def test_get_delay_exponential(self):
        """Test delay calculation with exponential backoff."""
        strategy = RetryStrategy(
            base_delay=1.0,
            exponential_backoff=True,
            jitter=False
        )
        
        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 4.0
        assert strategy.get_delay(3) == 8.0
    
    def test_get_delay_linear(self):
        """Test delay calculation without exponential backoff."""
        strategy = RetryStrategy(
            base_delay=2.0,
            exponential_backoff=False,
            jitter=False
        )
        
        assert strategy.get_delay(0) == 2.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 2.0
    
    def test_get_delay_max_limit(self):
        """Test delay calculation with maximum limit."""
        strategy = RetryStrategy(
            base_delay=1.0,
            max_delay=5.0,
            exponential_backoff=True,
            jitter=False
        )
        
        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 4.0
        assert strategy.get_delay(3) == 5.0  # Capped at max_delay
        assert strategy.get_delay(10) == 5.0  # Still capped
    
    def test_get_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        strategy = RetryStrategy(
            base_delay=2.0,
            exponential_backoff=False,
            jitter=True
        )
        
        # With jitter, delay should be between 50-100% of base delay
        delay = strategy.get_delay(0)
        assert 1.0 <= delay <= 2.0


class TestErrorInfo:
    """Test cases for ErrorInfo."""
    
    def test_init(self):
        """Test ErrorInfo initialization."""
        exception = ValueError("Test error")
        timestamp = datetime.now()
        
        error_info = ErrorInfo(
            error_id="test123",
            timestamp=timestamp,
            exception=exception,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM
        )
        
        assert error_info.error_id == "test123"
        assert error_info.timestamp == timestamp
        assert error_info.exception == exception
        assert error_info.category == ErrorCategory.VALIDATION
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert error_info.retry_count == 0
        assert error_info.resolved is False
    
    def test_to_dict(self):
        """Test ErrorInfo conversion to dictionary."""
        exception = ValueError("Test error")
        timestamp = datetime.now()
        
        error_info = ErrorInfo(
            error_id="test123",
            timestamp=timestamp,
            exception=exception,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context={"key": "value"},
            retry_count=2,
            resolved=True,
            resolution_strategy="test_strategy"
        )
        
        result = error_info.to_dict()
        
        assert result['error_id'] == "test123"
        assert result['timestamp'] == timestamp.isoformat()
        assert result['exception_type'] == "ValueError"
        assert result['exception_message'] == "Test error"
        assert result['category'] == "validation"
        assert result['severity'] == "medium"
        assert result['context'] == {"key": "value"}
        assert result['retry_count'] == 2
        assert result['resolved'] is True
        assert result['resolution_strategy'] == "test_strategy"


class TestErrorHandler:
    """Test cases for ErrorHandler."""
    
    @pytest.fixture
    def error_handler(self):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler(error_reporting_enabled=False)  # Disable logging for tests
    
    def test_init_default(self):
        """Test ErrorHandler initialization with defaults."""
        handler = ErrorHandler()
        
        assert isinstance(handler.default_retry_strategy, RetryStrategy)
        assert handler.max_error_history == 1000
        assert handler.error_reporting_enabled is True
        assert len(handler.error_history) == 0
        assert len(handler.error_counts) == 0
    
    def test_init_custom(self):
        """Test ErrorHandler initialization with custom parameters."""
        retry_strategy = RetryStrategy(max_attempts=5)
        
        handler = ErrorHandler(
            default_retry_strategy=retry_strategy,
            max_error_history=500,
            error_reporting_enabled=False
        )
        
        assert handler.default_retry_strategy == retry_strategy
        assert handler.max_error_history == 500
        assert handler.error_reporting_enabled is False
    
    def test_handle_error_basic(self, error_handler):
        """Test basic error handling."""
        exception = ValueError("Test error")
        
        error_info = error_handler.handle_error(exception)
        
        assert isinstance(error_info, ErrorInfo)
        assert error_info.exception == exception
        assert error_info.category == ErrorCategory.VALIDATION
        assert error_info.severity == ErrorSeverity.LOW
        assert len(error_handler.error_history) == 1
        assert error_handler.stats['total_errors'] == 1
    
    def test_handle_error_with_context(self, error_handler):
        """Test error handling with context."""
        exception = ConnectionError("Network error")
        context = {"url": "https://example.com", "attempt": 1}
        
        error_info = error_handler.handle_error(
            exception,
            context=context,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH
        )
        
        assert error_info.context == context
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.HIGH
    
    def test_classify_error_network(self, error_handler):
        """Test error classification for network errors."""
        exceptions = [
            ConnectionError("Connection failed"),
            TimeoutError("Request timeout"),
            Exception("HTTP error occurred")  # Contains 'http'
        ]
        
        for exception in exceptions:
            category = error_handler._classify_error(exception)
            assert category == ErrorCategory.NETWORK
    
    def test_classify_error_file_system(self, error_handler):
        """Test error classification for file system errors."""
        exceptions = [
            FileNotFoundError("File not found"),
            PermissionError("Permission denied"),
            IOError("IO error")
        ]
        
        for exception in exceptions:
            category = error_handler._classify_error(exception)
            assert category == ErrorCategory.FILE_SYSTEM
    
    def test_classify_error_validation(self, error_handler):
        """Test error classification for validation errors."""
        exceptions = [
            ValueError("Invalid value"),
            TypeError("Wrong type"),
            AttributeError("Missing attribute")
        ]
        
        for exception in exceptions:
            category = error_handler._classify_error(exception)
            assert category == ErrorCategory.VALIDATION
    
    def test_assess_severity_critical(self, error_handler):
        """Test severity assessment for critical errors."""
        exception = Exception("Critical system failure")
        severity = error_handler._assess_severity(exception, ErrorCategory.UNKNOWN)
        
        assert severity == ErrorSeverity.CRITICAL
    
    def test_assess_severity_high(self, error_handler):
        """Test severity assessment for high severity errors."""
        exception = PermissionError("Access denied")
        severity = error_handler._assess_severity(exception, ErrorCategory.FILE_SYSTEM)
        
        assert severity == ErrorSeverity.HIGH
    
    def test_assess_severity_medium(self, error_handler):
        """Test severity assessment for medium severity errors."""
        exception = ConnectionError("Network error")
        severity = error_handler._assess_severity(exception, ErrorCategory.NETWORK)
        
        assert severity == ErrorSeverity.MEDIUM
    
    def test_assess_severity_low(self, error_handler):
        """Test severity assessment for low severity errors."""
        exception = ValueError("Invalid input")
        severity = error_handler._assess_severity(exception, ErrorCategory.VALIDATION)
        
        assert severity == ErrorSeverity.LOW
    
    def test_retry_with_backoff_success(self, error_handler):
        """Test retry with backoff when function succeeds."""
        call_count = 0
        
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = error_handler.retry_with_backoff(test_function)
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_with_backoff_eventual_success(self, error_handler):
        """Test retry with backoff when function eventually succeeds."""
        call_count = 0
        
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.01)
        result = error_handler.retry_with_backoff(test_function, retry_strategy=retry_strategy)
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_with_backoff_all_fail(self, error_handler):
        """Test retry with backoff when all attempts fail."""
        call_count = 0
        
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")
        
        retry_strategy = RetryStrategy(max_attempts=2, base_delay=0.01)
        
        with pytest.raises(ValueError, match="Persistent error"):
            error_handler.retry_with_backoff(test_function, retry_strategy=retry_strategy)
        
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_retry_with_backoff_success(self, error_handler):
        """Test async retry with backoff when function succeeds."""
        call_count = 0
        
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "async_success"
        
        result = await error_handler.async_retry_with_backoff(test_function)
        
        assert result == "async_success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry_with_backoff_eventual_success(self, error_handler):
        """Test async retry with backoff when function eventually succeeds."""
        call_count = 0
        
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary async error")
            return "async_success"
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.01)
        result = await error_handler.async_retry_with_backoff(
            test_function, retry_strategy=retry_strategy
        )
        
        assert result == "async_success"
        assert call_count == 3
    
    def test_register_recovery_strategy(self, error_handler):
        """Test registering recovery strategy."""
        def recovery_function(exception, context):
            return True
        
        error_handler.register_recovery_strategy(ValueError, recovery_function)
        
        assert ValueError in error_handler.recovery_strategies
        assert error_handler.recovery_strategies[ValueError] == recovery_function
    
    def test_recovery_strategy_execution(self, error_handler):
        """Test execution of recovery strategy."""
        recovery_called = False
        
        def recovery_function(exception, context):
            nonlocal recovery_called
            recovery_called = True
            return True
        
        error_handler.register_recovery_strategy(ValueError, recovery_function)
        
        exception = ValueError("Test error")
        error_info = error_handler.handle_error(exception)
        
        assert recovery_called is True
        assert error_info.resolved is True
        assert error_handler.stats['successful_recoveries'] == 1
    
    def test_get_error_statistics(self, error_handler):
        """Test getting error statistics."""
        # Generate some errors
        error_handler.handle_error(ValueError("Error 1"))
        error_handler.handle_error(ConnectionError("Error 2"))
        
        stats = error_handler.get_error_statistics()
        
        assert stats['total_errors'] == 2
        assert stats['error_counts_by_type']['ValueError'] == 1
        assert stats['error_counts_by_type']['ConnectionError'] == 1
        assert 'resolution_rate' in stats
        assert 'recent_errors_24h' in stats
    
    def test_get_recent_errors(self, error_handler):
        """Test getting recent errors."""
        # Add some errors
        error_handler.handle_error(ValueError("Recent error"))
        
        recent_errors = error_handler.get_recent_errors(hours=1)
        
        assert len(recent_errors) == 1
        assert recent_errors[0].exception.args[0] == "Recent error"
    
    def test_clear_error_history(self, error_handler):
        """Test clearing error history."""
        # Add some errors
        error_handler.handle_error(ValueError("Error 1"))
        error_handler.handle_error(ValueError("Error 2"))
        
        assert len(error_handler.error_history) == 2
        assert error_handler.stats['total_errors'] == 2
        
        error_handler.clear_error_history()
        
        assert len(error_handler.error_history) == 0
        assert error_handler.stats['total_errors'] == 0
    
    def test_error_history_size_limit(self):
        """Test error history size limit."""
        handler = ErrorHandler(max_error_history=3, error_reporting_enabled=False)
        
        # Add more errors than the limit
        for i in range(5):
            handler.handle_error(ValueError(f"Error {i}"))
        
        # Should only keep the last 3 errors
        assert len(handler.error_history) == 3
        assert handler.error_history[-1].exception.args[0] == "Error 4"


class TestRetryDecorator:
    """Test cases for retry decorator."""
    
    def test_retry_decorator_success(self):
        """Test retry decorator with successful function."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_decorator_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_decorator_all_fail(self):
        """Test retry decorator when all attempts fail."""
        call_count = 0
        
        @retry_on_error(max_attempts=2, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")
        
        with pytest.raises(ValueError, match="Persistent error"):
            test_function()
        
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_retry_decorator_success(self):
        """Test async retry decorator with successful function."""
        call_count = 0
        
        @retry_on_error(max_attempts=3, base_delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "async_success"
        
        result = await test_function()
        
        assert result == "async_success"
        assert call_count == 1


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_error_handler(self):
        """Test getting global error handler."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert isinstance(handler1, ErrorHandler)
        assert handler1 is handler2  # Should return same instance
    
    def test_handle_error_function(self):
        """Test global handle_error function."""
        exception = ValueError("Test error")
        
        error_info = handle_error(exception)
        
        assert isinstance(error_info, ErrorInfo)
        assert error_info.exception == exception


if __name__ == "__main__":
    pytest.main([__file__])