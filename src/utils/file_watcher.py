"""File system watcher for monitoring new video files."""

import asyncio
import logging
from pathlib import Path
from typing import Set, Callable, Optional, List
from datetime import datetime, timedelta
import json

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from ..models.video_file import VideoFile
from .logging_config import get_logger


class VideoFileHandler(FileSystemEventHandler):
    """Handler for video file system events."""
    
    def __init__(
        self,
        supported_formats: List[str],
        callback: Callable[[Path], None],
        cooldown_seconds: int = 5
    ):
        """
        Initialize the video file handler.
        
        Args:
            supported_formats: List of supported video file extensions
            callback: Callback function to process new video files
            cooldown_seconds: Cooldown period before processing a file
        """
        self.supported_formats = [fmt.lower() for fmt in supported_formats]
        self.callback = callback
        self.cooldown_seconds = cooldown_seconds
        self.logger = get_logger(__name__)
        
        # Track files and their last modification time
        self.pending_files: dict[Path, datetime] = {}
        self.processing_files: Set[Path] = set()
        self.processed_files: Set[Path] = set()
        
        # Load processed files history
        self._load_processed_files()
    
    def _load_processed_files(self):
        """Load previously processed files from cache."""
        cache_file = Path("./logs/processed_files.json")
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self.processed_files = {Path(p) for p in data.get('processed_files', [])}
                    self.logger.info(f"Loaded {len(self.processed_files)} processed files from cache")
            except Exception as e:
                self.logger.warning(f"Could not load processed files cache: {e}")
    
    def _save_processed_files(self):
        """Save processed files to cache."""
        cache_file = Path("./logs/processed_files.json")
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump({
                    'processed_files': [str(p) for p in self.processed_files],
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save processed files cache: {e}")
    
    def is_video_file(self, path: Path) -> bool:
        """Check if the file is a supported video file."""
        return path.suffix.lower() in self.supported_formats and path.is_file()
    
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if self.is_video_file(path):
            self.logger.info(f"New video file detected: {path}")
            self.pending_files[path] = datetime.now()
    
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        if self.is_video_file(path) and path not in self.processed_files:
            self.logger.debug(f"Video file modified: {path}")
            self.pending_files[path] = datetime.now()
    
    def process_pending_files(self):
        """Process files that have been stable for the cooldown period."""
        now = datetime.now()
        cooldown_delta = timedelta(seconds=self.cooldown_seconds)
        
        files_to_process = []
        for path, last_modified in list(self.pending_files.items()):
            if now - last_modified >= cooldown_delta:
                # File has been stable for cooldown period
                if path not in self.processing_files and path not in self.processed_files:
                    files_to_process.append(path)
                    self.processing_files.add(path)
                del self.pending_files[path]
        
        for path in files_to_process:
            try:
                self.logger.info(f"Processing new video file: {path}")
                self.callback(path)
                self.processed_files.add(path)
                self.processing_files.discard(path)
                self._save_processed_files()
            except Exception as e:
                self.logger.error(f"Error processing file {path}: {e}")
                self.processing_files.discard(path)
    
    def mark_as_processed(self, path: Path):
        """Mark a file as processed."""
        self.processed_files.add(path)
        self.processing_files.discard(path)
        self._save_processed_files()
    
    def reset_processed_files(self):
        """Reset the processed files list."""
        self.processed_files.clear()
        self.processing_files.clear()
        self._save_processed_files()
        self.logger.info("Reset processed files list")


class FileWatcher:
    """File system watcher for monitoring video files."""
    
    def __init__(
        self,
        watch_directory: Path,
        supported_formats: List[str],
        scan_interval: int = 10,
        cooldown_seconds: int = 5
    ):
        """
        Initialize the file watcher.
        
        Args:
            watch_directory: Directory to monitor
            supported_formats: List of supported video file extensions
            scan_interval: Interval in seconds to scan for stable files
            cooldown_seconds: Cooldown period before processing a file
        """
        self.watch_directory = Path(watch_directory)
        self.supported_formats = supported_formats
        self.scan_interval = scan_interval
        self.cooldown_seconds = cooldown_seconds
        
        self.logger = get_logger(__name__)
        self.observer = Observer()
        self.handler: Optional[VideoFileHandler] = None
        self.is_watching = False
        self.scan_task: Optional[asyncio.Task] = None
        self.callback: Optional[Callable] = None
    
    def start(self, callback: Callable[[Path], None]):
        """
        Start watching the directory.
        
        Args:
            callback: Callback function to process new video files
        """
        if self.is_watching:
            self.logger.warning("File watcher is already running")
            return
        
        self.callback = callback
        
        # Create handler
        self.handler = VideoFileHandler(
            supported_formats=self.supported_formats,
            callback=callback,
            cooldown_seconds=self.cooldown_seconds
        )
        
        # Schedule observer
        self.observer.schedule(
            self.handler,
            str(self.watch_directory),
            recursive=True
        )
        
        # Start observer
        self.observer.start()
        self.is_watching = True
        
        self.logger.info(f"Started watching directory: {self.watch_directory}")
    
    async def start_async(self, callback: Callable[[Path], None]):
        """Start watching with async support."""
        self.start(callback)
        
        # Start periodic scanning for stable files
        self.scan_task = asyncio.create_task(self._scan_loop())
    
    async def _scan_loop(self):
        """Periodically scan for files ready to process."""
        while self.is_watching:
            try:
                if self.handler:
                    self.handler.process_pending_files()
            except Exception as e:
                self.logger.error(f"Error in scan loop: {e}")
            
            await asyncio.sleep(self.scan_interval)
    
    def stop(self):
        """Stop watching the directory."""
        if not self.is_watching:
            return
        
        self.observer.stop()
        self.observer.join(timeout=5)
        self.is_watching = False
        
        if self.scan_task:
            self.scan_task.cancel()
        
        self.logger.info("Stopped watching directory")
    
    def get_initial_files(self) -> List[Path]:
        """
        Get initial video files in the directory that haven't been processed.
        
        Returns:
            List of unprocessed video file paths
        """
        video_files = []
        
        if not self.watch_directory.exists():
            self.logger.warning(f"Watch directory does not exist: {self.watch_directory}")
            return video_files
        
        # Scan directory for existing video files
        for ext in self.supported_formats:
            pattern = f"**/*{ext}"
            for file_path in self.watch_directory.glob(pattern):
                if file_path.is_file():
                    # Check if file hasn't been processed
                    if self.handler and file_path not in self.handler.processed_files:
                        video_files.append(file_path)
        
        self.logger.info(f"Found {len(video_files)} unprocessed video files in {self.watch_directory}")
        return video_files
    
    def mark_as_processed(self, path: Path):
        """Mark a file as processed."""
        if self.handler:
            self.handler.mark_as_processed(path)
    
    def reset_processed_files(self):
        """Reset the processed files list."""
        if self.handler:
            self.handler.reset_processed_files()