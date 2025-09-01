"""Unified logging configuration for the application."""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False


class LogLevel(Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig:
    """
    Centralized logging configuration manager.
    
    Provides unified logging setup with support for console and file logging,
    colored output, rotation, and structured formatting.
    """
    
    def __init__(
        self,
        log_level: LogLevel = LogLevel.INFO,
        log_dir: Optional[Path] = None,
        log_filename: str = "av_scraper.log",
        max_file_size_mb: int = 10,
        backup_count: int = 5,
        console_logging: bool = True,
        file_logging: bool = True,
        colored_console: bool = True,
        include_caller_info: bool = False,
        json_format: bool = False
    ):
        """
        Initialize logging configuration.
        
        Args:
            log_level: Minimum log level to record
            log_dir: Directory for log files (None for current directory)
            log_filename: Name of the log file
            max_file_size_mb: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
            console_logging: Enable console output
            file_logging: Enable file output
            colored_console: Use colored console output (requires colorlog)
            include_caller_info: Include caller information in logs
            json_format: Use JSON format for structured logging
        """
        self.log_level = log_level
        self.log_dir = log_dir or Path.cwd() / "logs"
        self.log_filename = log_filename
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self.console_logging = console_logging
        self.file_logging = file_logging
        self.colored_console = colored_console and COLORLOG_AVAILABLE
        self.include_caller_info = include_caller_info
        self.json_format = json_format
        
        # Track configured loggers to avoid duplicate configuration
        self._configured_loggers = set()
        
        # Create log directory if it doesn't exist
        if self.file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self, logger_name: Optional[str] = None) -> logging.Logger:
        """
        Set up logging configuration.
        
        Args:
            logger_name: Name of the logger (None for root logger)
            
        Returns:
            Configured logger instance
        """
        # Get or create logger
        logger = logging.getLogger(logger_name)
        
        # Avoid duplicate configuration
        if logger_name in self._configured_loggers:
            return logger
        
        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Set log level
        logger.setLevel(getattr(logging, self.log_level.value))
        
        # Prevent propagation to avoid duplicate messages
        logger.propagate = False
        
        # Add console handler
        if self.console_logging:
            console_handler = self._create_console_handler()
            logger.addHandler(console_handler)
        
        # Add file handler
        if self.file_logging:
            file_handler = self._create_file_handler()
            logger.addHandler(file_handler)
        
        # Mark as configured
        self._configured_loggers.add(logger_name or "root")
        
        return logger
    
    def _create_console_handler(self) -> logging.Handler:
        """Create console logging handler."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, self.log_level.value))
        
        if self.colored_console:
            formatter = self._create_colored_formatter()
        else:
            formatter = self._create_standard_formatter()
        
        handler.setFormatter(formatter)
        return handler
    
    def _create_file_handler(self) -> logging.Handler:
        """Create file logging handler with rotation."""
        log_file_path = self.log_dir / self.log_filename
        
        handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=self.max_file_size_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        
        handler.setLevel(getattr(logging, self.log_level.value))
        
        if self.json_format:
            formatter = self._create_json_formatter()
        else:
            formatter = self._create_standard_formatter()
        
        handler.setFormatter(formatter)
        return handler
    
    def _create_standard_formatter(self) -> logging.Formatter:
        """Create standard text formatter."""
        if self.include_caller_info:
            format_string = (
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(filename)s:%(lineno)d - %(funcName)s - %(message)s'
            )
        else:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        return logging.Formatter(
            fmt=format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _create_colored_formatter(self) -> logging.Formatter:
        """Create colored console formatter."""
        if not COLORLOG_AVAILABLE:
            return self._create_standard_formatter()
        
        if self.include_caller_info:
            format_string = (
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - '
                '%(filename)s:%(lineno)d - %(funcName)s - %(message)s%(reset)s'
            )
        else:
            format_string = (
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s'
            )
        
        return colorlog.ColoredFormatter(
            fmt=format_string,
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    
    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON formatter for structured logging."""
        return JsonFormatter(include_caller_info=self.include_caller_info)
    
    def get_log_file_path(self) -> Optional[Path]:
        """
        Get the path to the current log file.
        
        Returns:
            Path to log file or None if file logging is disabled
        """
        if not self.file_logging:
            return None
        
        return self.log_dir / self.log_filename
    
    def get_log_files(self) -> list[Path]:
        """
        Get list of all log files (including rotated ones).
        
        Returns:
            List of log file paths
        """
        if not self.file_logging:
            return []
        
        log_files = []
        base_name = self.log_filename
        
        # Main log file
        main_log = self.log_dir / base_name
        if main_log.exists():
            log_files.append(main_log)
        
        # Rotated log files
        for i in range(1, self.backup_count + 1):
            rotated_log = self.log_dir / f"{base_name}.{i}"
            if rotated_log.exists():
                log_files.append(rotated_log)
        
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """
        Clean up old log files.
        
        Args:
            days_to_keep: Number of days of logs to keep
            
        Returns:
            Number of files removed
        """
        if not self.file_logging:
            return 0
        
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        removed_count = 0
        
        # Find all log files in the directory
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    removed_count += 1
            except OSError:
                # File might be in use or permission denied
                continue
        
        return removed_count
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get logging statistics.
        
        Returns:
            Dictionary with logging statistics
        """
        stats = {
            'log_level': self.log_level.value,
            'console_logging': self.console_logging,
            'file_logging': self.file_logging,
            'colored_console': self.colored_console,
            'json_format': self.json_format,
            'configured_loggers': len(self._configured_loggers),
            'log_files': []
        }
        
        if self.file_logging:
            stats['log_dir'] = str(self.log_dir)
            stats['log_filename'] = self.log_filename
            
            log_files = self.get_log_files()
            for log_file in log_files:
                try:
                    file_stats = log_file.stat()
                    stats['log_files'].append({
                        'path': str(log_file),
                        'size_bytes': file_stats.st_size,
                        'size_mb': file_stats.st_size / (1024 * 1024),
                        'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                    })
                except OSError:
                    continue
        
        return stats


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_caller_info: bool = False):
        """
        Initialize JSON formatter.
        
        Args:
            include_caller_info: Include caller information in JSON
        """
        super().__init__()
        self.include_caller_info = include_caller_info
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        import json
        
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }
        
        if self.include_caller_info:
            log_data.update({
                'filename': record.filename,
                'line_number': record.lineno,
                'function': record.funcName
            })
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_application_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_dir: Optional[Path] = None,
    console_logging: bool = True,
    file_logging: bool = True,
    colored_console: bool = True
) -> LoggingConfig:
    """
    Set up application-wide logging configuration.
    
    Args:
        log_level: Minimum log level
        log_dir: Directory for log files
        console_logging: Enable console output
        file_logging: Enable file output
        colored_console: Use colored console output
        
    Returns:
        Configured LoggingConfig instance
    """
    config = LoggingConfig(
        log_level=log_level,
        log_dir=log_dir,
        console_logging=console_logging,
        file_logging=file_logging,
        colored_console=colored_console
    )
    
    # Configure root logger
    config.setup_logging()
    
    # Configure application loggers
    application_loggers = [
        'src.scrapers',
        'src.organizers',
        'src.downloaders',
        'src.utils',
        'src.models'
    ]
    
    for logger_name in application_loggers:
        config.setup_logging(logger_name)
    
    return config


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)