#!/usr/bin/env python3
"""Example usage of logging and error handling systems."""

import asyncio
import tempfile
import time
from pathlib import Path

from src.utils.logging_config import (
    LoggingConfig, LogLevel, setup_application_logging, get_logger
)
from src.utils.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, RetryStrategy,
    retry_on_error, get_error_handler, handle_error
)
from src.utils.progress_tracker import (
    ProgressTracker, ProgressUnit, TaskStatus, ProgressContext, get_progress_tracker
)


def logging_configuration_example():
    """Demonstrate logging configuration options."""
    print("=== Logging Configuration Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        
        # Create logging configuration
        config = LoggingConfig(
            log_level=LogLevel.DEBUG,
            log_dir=log_dir,
            log_filename="example.log",
            console_logging=True,
            file_logging=True,
            colored_console=True,
            include_caller_info=True
        )
        
        print(f"Log configuration:")
        print(f"  Log level: {config.log_level.value}")
        print(f"  Log directory: {config.log_dir}")
        print(f"  Console logging: {config.console_logging}")
        print(f"  File logging: {config.file_logging}")
        print(f"  Colored console: {config.colored_console}")
        
        # Set up logger
        logger = config.setup_logging("example_logger")
        
        # Test different log levels
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")
        
        # Check log file was created
        log_file = config.get_log_file_path()
        if log_file and log_file.exists():
            print(f"\n✓ Log file created: {log_file}")
            print(f"  File size: {log_file.stat().st_size} bytes")
        
        # Get logging statistics
        stats = config.get_log_stats()
        print(f"\nLogging statistics:")
        print(f"  Configured loggers: {stats['configured_loggers']}")
        print(f"  Log files: {len(stats['log_files'])}")


def json_logging_example():
    """Demonstrate JSON structured logging."""
    print("\n=== JSON Logging Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir) / "json_logs"
        
        # Create JSON logging configuration
        config = LoggingConfig(
            log_level=LogLevel.INFO,
            log_dir=log_dir,
            log_filename="structured.log",
            console_logging=False,  # Only file logging for JSON
            file_logging=True,
            json_format=True,
            include_caller_info=True
        )
        
        logger = config.setup_logging("json_logger")
        
        # Log structured data
        logger.info("User action", extra={
            'user_id': 'user123',
            'action': 'file_upload',
            'file_size': 1024,
            'success': True
        })
        
        logger.error("Processing failed", extra={
            'error_code': 'E001',
            'component': 'file_processor',
            'retry_count': 3
        })
        
        # Read and display JSON log
        log_file = config.get_log_file_path()
        if log_file and log_file.exists():
            print("JSON log entries:")
            with open(log_file, 'r') as f:
                for line in f:
                    print(f"  {line.strip()}")


def error_handling_basic_example():
    """Demonstrate basic error handling."""
    print("\n=== Basic Error Handling Example ===\n")
    
    error_handler = ErrorHandler(error_reporting_enabled=False)  # Disable logging for demo
    
    # Handle different types of errors
    errors = [
        ValueError("Invalid input value"),
        ConnectionError("Network connection failed"),
        FileNotFoundError("Configuration file not found"),
        PermissionError("Access denied to resource")
    ]
    
    for error in errors:
        error_info = error_handler.handle_error(
            error,
            context={'component': 'example', 'timestamp': time.time()}
        )
        
        print(f"Error {error_info.error_id}:")
        print(f"  Type: {type(error).__name__}")
        print(f"  Category: {error_info.category.value}")
        print(f"  Severity: {error_info.severity.value}")
        print(f"  Message: {error}")
        print()
    
    # Show error statistics
    stats = error_handler.get_error_statistics()
    print(f"Error statistics:")
    print(f"  Total errors: {stats['total_errors']}")
    print(f"  Error types: {stats['error_counts_by_type']}")


def retry_mechanism_example():
    """Demonstrate retry mechanisms."""
    print("\n=== Retry Mechanism Example ===\n")
    
    error_handler = ErrorHandler(error_reporting_enabled=False)
    
    # Function that fails a few times then succeeds
    attempt_count = 0
    
    def unreliable_function():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  Attempt {attempt_count}")
        
        if attempt_count < 3:
            raise ConnectionError("Temporary network error")
        
        return "Success!"
    
    # Test retry with backoff
    print("Testing retry with backoff:")
    
    retry_strategy = RetryStrategy(
        max_attempts=5,
        base_delay=0.1,  # Short delay for demo
        exponential_backoff=True
    )
    
    try:
        result = error_handler.retry_with_backoff(
            unreliable_function,
            retry_strategy=retry_strategy,
            context={'operation': 'network_request'}
        )
        print(f"✓ Final result: {result}")
    except Exception as e:
        print(f"✗ All retries failed: {e}")
    
    print(f"Total attempts made: {attempt_count}")


def retry_decorator_example():
    """Demonstrate retry decorator."""
    print("\n=== Retry Decorator Example ===\n")
    
    call_count = 0
    
    @retry_on_error(max_attempts=3, base_delay=0.1)
    def flaky_operation():
        nonlocal call_count
        call_count += 1
        print(f"  Decorated function call {call_count}")
        
        if call_count < 3:
            raise ValueError("Temporary failure")
        
        return "Decorator success!"
    
    print("Testing retry decorator:")
    
    try:
        result = flaky_operation()
        print(f"✓ Result: {result}")
    except Exception as e:
        print(f"✗ Failed: {e}")


async def async_retry_example():
    """Demonstrate async retry mechanisms."""
    print("\n=== Async Retry Example ===\n")
    
    error_handler = ErrorHandler(error_reporting_enabled=False)
    
    attempt_count = 0
    
    async def async_unreliable_function():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  Async attempt {attempt_count}")
        
        if attempt_count < 3:
            raise TimeoutError("Async timeout error")
        
        return "Async success!"
    
    print("Testing async retry:")
    
    try:
        result = await error_handler.async_retry_with_backoff(
            async_unreliable_function,
            retry_strategy=RetryStrategy(max_attempts=5, base_delay=0.1)
        )
        print(f"✓ Async result: {result}")
    except Exception as e:
        print(f"✗ Async retry failed: {e}")


def recovery_strategy_example():
    """Demonstrate error recovery strategies."""
    print("\n=== Recovery Strategy Example ===\n")
    
    error_handler = ErrorHandler(error_reporting_enabled=False)
    
    # Register custom recovery strategy
    def network_recovery(exception, context):
        print(f"  Attempting recovery for: {exception}")
        print(f"  Context: {context}")
        
        # Simulate recovery logic
        if "retry_count" in context and context["retry_count"] < 2:
            print("  ✓ Recovery successful")
            return True
        else:
            print("  ✗ Recovery failed")
            return False
    
    error_handler.register_recovery_strategy(ConnectionError, network_recovery)
    
    # Test recovery
    print("Testing error recovery:")
    
    network_error = ConnectionError("Connection timeout")
    error_info = error_handler.handle_error(
        network_error,
        context={'retry_count': 1, 'url': 'https://example.com'}
    )
    
    print(f"Error resolved: {error_info.resolved}")
    print(f"Resolution strategy: {error_info.resolution_strategy}")
    
    # Show recovery statistics
    stats = error_handler.get_error_statistics()
    print(f"\nRecovery statistics:")
    print(f"  Successful recoveries: {stats['successful_recoveries']}")
    print(f"  Failed recoveries: {stats['failed_recoveries']}")


def progress_tracking_example():
    """Demonstrate progress tracking."""
    print("\n=== Progress Tracking Example ===\n")
    
    tracker = ProgressTracker(enable_logging=False)
    
    # Start multiple tasks
    print("Starting tasks:")
    
    task1 = tracker.start_task("download", "Downloading files", total=100, unit=ProgressUnit.FILES)
    task2 = tracker.start_task("process", "Processing data", total=50, unit=ProgressUnit.ITEMS)
    
    print(f"  Task 1: {task1.name} (0/{task1.total} {task1.unit.value})")
    print(f"  Task 2: {task2.name} (0/{task2.total} {task2.unit.value})")
    
    # Simulate progress updates
    print("\nSimulating progress:")
    
    for i in range(5):
        # Update download progress
        tracker.update_progress("download", increment=20)
        download_progress = tracker.get_task_progress("download")
        
        # Update processing progress
        tracker.update_progress("process", increment=10)
        process_progress = tracker.get_task_progress("process")
        
        print(f"  Download: {download_progress.current}/{download_progress.total} "
              f"({download_progress.progress_percentage:.1f}%)")
        print(f"  Process: {process_progress.current}/{process_progress.total} "
              f"({process_progress.progress_percentage:.1f}%)")
        
        time.sleep(0.1)  # Simulate work
    
    # Complete tasks
    tracker.complete_task("download", success=True)
    tracker.complete_task("process", success=True)
    
    print("\n✓ All tasks completed")
    
    # Show overall progress
    overall = tracker.get_overall_progress()
    print(f"\nOverall statistics:")
    print(f"  Active tasks: {overall['active_tasks']}")
    print(f"  Completed tasks: {overall['completed_tasks']}")
    print(f"  Total items processed: {overall['completed_items']}")


def progress_context_example():
    """Demonstrate progress context manager."""
    print("\n=== Progress Context Example ===\n")
    
    tracker = ProgressTracker(enable_logging=False)
    
    print("Using progress context manager:")
    
    try:
        with ProgressContext("context_task", "Context Task", total=10, tracker=tracker) as ctx:
            for i in range(10):
                time.sleep(0.05)  # Simulate work
                ctx.update(current=i + 1)
                ctx.set_metadata(step=f"Processing item {i + 1}")
                
                if i == 7:  # Simulate some metadata
                    ctx.set_metadata(milestone="Almost done")
            
            print("  ✓ Context task completed successfully")
    
    except Exception as e:
        print(f"  ✗ Context task failed: {e}")
    
    # Check final state
    completed_tasks = tracker.get_completed_tasks()
    if completed_tasks:
        task = completed_tasks[0]
        print(f"  Final status: {task.status.value}")
        print(f"  Final progress: {task.current}/{task.total}")
        print(f"  Metadata: {task.metadata}")


def progress_callbacks_example():
    """Demonstrate progress callbacks."""
    print("\n=== Progress Callbacks Example ===\n")
    
    tracker = ProgressTracker(enable_logging=False)
    
    # Add progress callback
    def progress_callback(task_progress):
        if task_progress.progress_percentage:
            print(f"  Callback: {task_progress.name} - {task_progress.progress_percentage:.1f}% complete")
    
    tracker.add_progress_callback(progress_callback)
    
    print("Progress with callback:")
    
    tracker.start_task("callback_task", "Callback Task", total=5)
    
    for i in range(5):
        time.sleep(0.1)
        tracker.update_progress("callback_task", current=i + 1)
    
    tracker.complete_task("callback_task", success=True)


def integrated_example():
    """Demonstrate integrated logging, error handling, and progress tracking."""
    print("\n=== Integrated Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up logging
        log_config = setup_application_logging(
            log_level=LogLevel.INFO,
            log_dir=Path(temp_dir) / "logs",
            console_logging=True,
            file_logging=True
        )
        
        logger = get_logger("integrated_example")
        error_handler = get_error_handler()
        tracker = get_progress_tracker()
        
        logger.info("Starting integrated example")
        
        # Simulate a complex operation with progress tracking and error handling
        with ProgressContext("integrated", "Integrated Operation", total=3, tracker=tracker) as ctx:
            
            # Step 1: Successful operation
            logger.info("Step 1: Initialization")
            ctx.update(current=1)
            time.sleep(0.1)
            
            # Step 2: Operation with potential error
            logger.info("Step 2: Processing with potential error")
            try:
                # Simulate an operation that might fail
                if True:  # Change to False to simulate error
                    logger.info("Processing completed successfully")
                else:
                    raise ValueError("Processing failed")
                
                ctx.update(current=2)
                
            except Exception as e:
                error_info = error_handler.handle_error(
                    e,
                    context={'step': 2, 'operation': 'processing'},
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM
                )
                logger.error(f"Error in step 2: {error_info.error_id}")
                raise
            
            # Step 3: Finalization
            logger.info("Step 3: Finalization")
            ctx.update(current=3)
            time.sleep(0.1)
        
        logger.info("Integrated example completed successfully")
        
        # Show final statistics
        error_stats = error_handler.get_error_statistics()
        progress_stats = tracker.get_overall_progress()
        log_stats = log_config.get_log_stats()
        
        print(f"\nFinal statistics:")
        print(f"  Errors handled: {error_stats['total_errors']}")
        print(f"  Tasks completed: {progress_stats['completed_tasks']}")
        print(f"  Log files created: {len(log_stats['log_files'])}")


async def main():
    """Run all examples."""
    print("Logging and Error Handling Examples")
    print("=" * 50)
    
    try:
        logging_configuration_example()
        json_logging_example()
        error_handling_basic_example()
        retry_mechanism_example()
        retry_decorator_example()
        await async_retry_example()
        recovery_strategy_example()
        progress_tracking_example()
        progress_context_example()
        progress_callbacks_example()
        integrated_example()
        
        print("\n" + "=" * 50)
        print("All examples completed!")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error in examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())