"""Main application class that integrates all components."""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field

from .utils.logging_config import LoggingConfig, LogLevel, get_logger
from .utils.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity, get_error_handler
from .utils.progress_tracker import ProgressTracker, ProgressUnit, ProgressContext, get_progress_tracker
from .utils.progress_persistence import ProgressPersistence, get_progress_persistence
from .utils.duplicate_detector import DuplicateDetector, DuplicateStrategy, get_duplicate_detector
from .utils.batch_processor import BatchProcessor, get_batch_processor
from .utils.performance_monitor import PerformanceMonitor, PerformanceContext, get_performance_monitor
from .utils.file_watcher import FileWatcher
from .config.config_manager import ConfigManager
from .scanner.file_scanner import FileScanner
from .scrapers.scraper_factory import ScraperFactory
from .organizers.file_organizer import FileOrganizer, ConflictResolution
from .downloaders.image_downloader import ImageDownloader, ImageType
from .models.video_file import VideoFile
from .models.movie_metadata import MovieMetadata


@dataclass
class ProcessingStats:
    """Statistics for processing session."""
    files_scanned: int = 0
    files_processed: int = 0
    files_organized: int = 0
    metadata_scraped: int = 0
    images_downloaded: int = 0
    errors_encountered: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.files_scanned == 0:
            return 0.0
        return (self.files_processed / self.files_scanned) * 100


class AVMetadataScraper:
    """
    Main application class that orchestrates the complete AV metadata scraping workflow.
    
    Integrates file scanning, metadata scraping, file organization, and image downloading
    into a cohesive processing pipeline with error handling and progress tracking.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the AV metadata scraper application.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config_data()
        
        # Set up logging
        self._setup_logging()
        self.logger = get_logger(__name__)
        
        # Initialize error handling and progress tracking
        self.error_handler = get_error_handler()
        self.progress_tracker = get_progress_tracker()
        self.progress_persistence = get_progress_persistence()
        self.duplicate_detector = get_duplicate_detector()
        self.performance_monitor = get_performance_monitor()
        self.batch_processor = get_batch_processor()
        
        # Initialize components
        self._initialize_components()
        
        # Application state
        self.is_running = False
        self.should_stop = False
        self.processing_stats = ProcessingStats()
        
        # Task queue for concurrent processing
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self.worker_tasks: List[asyncio.Task] = []
        
        # Advanced features
        self.current_session_id: Optional[str] = None
        self.enable_duplicate_detection = self.config.get('advanced', {}).get('enable_duplicate_detection', False)
        self.enable_performance_monitoring = self.config.get('advanced', {}).get('enable_performance_monitoring', True)
        
        # Watch mode configuration
        self.watch_mode = self.config.get('watch_mode', {}).get('enabled', False)
        self.watch_interval = self.config.get('watch_mode', {}).get('scan_interval', 30)
        self.file_watcher: Optional[FileWatcher] = None
        
        self.logger.info("AV Metadata Scraper initialized")
    
    def _setup_logging(self) -> None:
        """Set up application logging configuration."""
        log_config = self.config.get('logging', {})
        
        logging_config = LoggingConfig(
            log_level=LogLevel(log_config.get('level', 'INFO')),
            log_dir=Path(log_config.get('directory', 'logs')),
            log_filename=log_config.get('filename', 'av_scraper.log'),
            console_logging=log_config.get('console', True),
            file_logging=log_config.get('file', True),
            colored_console=log_config.get('colored', True),
            json_format=log_config.get('json_format', False)
        )
        
        # Configure application loggers
        logging_config.setup_logging()
        logging_config.setup_logging('src.scrapers')
        logging_config.setup_logging('src.organizers')
        logging_config.setup_logging('src.downloaders')
        logging_config.setup_logging('src.utils')
    
    def _initialize_components(self) -> None:
        """Initialize all application components."""
        try:
            # File scanner
            directories_config = self.config.get('directories', {})
            supported_extensions = self.config.get('supported_extensions', ['.mp4', '.mkv', '.avi'])
            self.file_scanner = FileScanner(
                source_directory=directories_config.get('source', './source'),
                supported_formats=supported_extensions
            )
            
            # Metadata scraper factory
            scraper_config = self.config.get('scrapers', {})
            self.scraper_factory = ScraperFactory(scraper_config)
            self.metadata_scraper = self.scraper_factory.create_metadata_scraper()
            
            # File organizer
            directories_config = self.config.get('directories', {})
            organization_config = self.config.get('organization', {})
            self.file_organizer = FileOrganizer(
                target_directory=directories_config.get('target', './organized'),
                naming_pattern=organization_config.get('naming_pattern', '{actress}/{code}/{code}.{ext}'),
                conflict_resolution=ConflictResolution(organization_config.get('conflict_resolution', 'rename')),
                create_metadata_files=organization_config.get('create_metadata_files', True),
                safe_mode=organization_config.get('safe_mode', True)
            )
            
            # Image downloader
            downloader_config = self.config.get('downloader', {})
            self.image_downloader = ImageDownloader(
                max_concurrent_downloads=downloader_config.get('max_concurrent', 3),
                timeout_seconds=downloader_config.get('timeout', 30),
                resize_images=downloader_config.get('resize_images', False),
                create_thumbnails=downloader_config.get('create_thumbnails', False)
            )
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def start(self, resume_session_id: Optional[str] = None) -> None:
        """Start the application and begin processing."""
        if self.is_running:
            self.logger.warning("Application is already running")
            return
        
        self.logger.info("Starting AV Metadata Scraper")
        self.is_running = True
        self.should_stop = False
        self.processing_stats = ProcessingStats(start_time=datetime.now())
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        try:
            # Start performance monitoring if enabled
            if self.enable_performance_monitoring:
                self.performance_monitor.start_monitoring()
            
            # Start progress tracking
            self.progress_tracker.start_auto_updates()
            
            # Resume or start new session
            if resume_session_id:
                session = self.progress_persistence.resume_session(resume_session_id)
                if session:
                    self.current_session_id = resume_session_id
                    self.logger.info(f"Resumed processing session: {resume_session_id}")
                else:
                    self.logger.warning(f"Could not resume session {resume_session_id}, starting new session")
            
            # Run the main processing pipeline
            await self._run_processing_pipeline()
            
        except Exception as e:
            self.logger.error(f"Error during processing: {e}")
            self.error_handler.handle_error(e, context={'component': 'main_pipeline'})
            raise
        finally:
            await self._cleanup()
    
    async def start_watch_mode(self) -> None:
        """Start the application in watch mode for continuous monitoring."""
        if self.is_running:
            self.logger.warning("Application is already running")
            return
        
        self.logger.info("Starting AV Metadata Scraper in WATCH MODE")
        self.is_running = True
        self.should_stop = False
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        try:
            # Start performance monitoring if enabled
            if self.enable_performance_monitoring:
                self.performance_monitor.start_monitoring()
            
            # Initialize file watcher
            directories_config = self.config.get('directories', {})
            source_dir = Path(directories_config.get('source', './source'))
            supported_extensions = self.config.get('supported_extensions', ['.mp4', '.mkv', '.avi'])
            
            self.file_watcher = FileWatcher(
                watch_directory=source_dir,
                supported_formats=supported_extensions,
                scan_interval=self.watch_interval,
                cooldown_seconds=5
            )
            
            # Process existing unprocessed files first
            self.logger.info("Scanning for existing unprocessed files...")
            initial_files = self.file_watcher.get_initial_files()
            
            if initial_files:
                self.logger.info(f"Processing {len(initial_files)} existing files...")
                for file_path in initial_files:
                    await self._process_new_file(file_path)
                    self.file_watcher.mark_as_processed(file_path)
            
            # Start watching for new files
            self.logger.info(f"Starting file system monitoring on: {source_dir}")
            await self.file_watcher.start_async(
                callback=lambda path: asyncio.create_task(self._process_new_file(path))
            )
            
            # Keep the application running
            self.logger.info("Watch mode active. Press Ctrl+C to stop.")
            while not self.should_stop:
                await asyncio.sleep(1)
                
                # Periodically log status
                if int(datetime.now().timestamp()) % 60 == 0:  # Every minute
                    self.logger.debug(f"Watch mode active - Processed: {self.processing_stats.files_processed} files")
            
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Error in watch mode: {e}")
            self.error_handler.handle_error(e, context={'component': 'watch_mode'})
        finally:
            if self.file_watcher:
                self.file_watcher.stop()
            await self._cleanup()
    
    async def _process_new_file(self, file_path: Path) -> None:
        """Process a newly detected video file."""
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Create VideoFile object
            video_file = VideoFile(
                file_path=str(file_path),
                filename=file_path.name,
                file_size=file_path.stat().st_size if file_path.exists() else 0,
                extension=file_path.suffix
            )
            
            # Extract code from filename
            code = self.file_scanner.extract_code_from_filename(file_path.name)
            if code:
                video_file.detected_code = code
                
                # Process the file through the pipeline
                await self._process_single_file(video_file, "WatchMode")
                
                # Mark as processed
                if self.file_watcher:
                    self.file_watcher.mark_as_processed(file_path)
                    
                self.processing_stats.files_processed += 1
                self.logger.info(f"Successfully processed: {file_path.name}")
            else:
                self.logger.warning(f"Could not extract code from filename: {file_path.name}")
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            self.error_handler.handle_error(e, context={'file': str(file_path)})
    
    async def stop(self) -> None:
        """Stop the application gracefully."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping AV Metadata Scraper...")
        self.should_stop = True
        
        # Stop file watcher if active
        if self.file_watcher:
            self.file_watcher.stop()
        
        # Cancel worker tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        await self._cleanup()
    
    async def _run_processing_pipeline(self) -> None:
        """Run the complete processing pipeline with advanced features."""
        with PerformanceContext("processing_pipeline", self.performance_monitor):
            self.logger.info("Starting processing pipeline")
            
            # Step 1: Scan for video files
            video_files = await self._scan_files()
            
            if not video_files:
                self.logger.info("No video files found to process")
                return
            
            # Step 2: Duplicate detection (if enabled)
            if self.enable_duplicate_detection:
                video_files = await self._detect_and_handle_duplicates(video_files)
            
            # Step 3: Start or resume processing session
            if not self.current_session_id:
                session = self.progress_persistence.start_session(
                    total_files=len(video_files),
                    metadata={
                        'source_directories': self.config.get('scanner', {}).get('source_directory', ''),
                        'target_directory': self.config.get('organizer', {}).get('target_directory', ''),
                        'duplicate_detection_enabled': self.enable_duplicate_detection
                    }
                )
                self.current_session_id = session.session_id
            
            # Step 4: Filter already processed files (for resumed sessions)
            video_files = await self._filter_processed_files(video_files)
            
            if not video_files:
                self.logger.info("All files have been processed")
                return
            
            # Step 5: Start concurrent workers
            await self._start_workers()
            
            # Step 6: Queue files for processing
            await self._queue_files_for_processing(video_files)
            
            # Step 7: Wait for processing to complete
            await self._wait_for_completion()
            
            # Step 8: Finalize session
            self._finalize_processing_session()
            
            self.logger.info("Processing pipeline completed")
    
    async def _scan_files(self) -> List[VideoFile]:
        """Scan for video files to process."""
        with ProgressContext(
            "file_scan", 
            "Scanning for video files", 
            tracker=self.progress_tracker
        ) as ctx:
            
            self.logger.info("Scanning for video files...")
            
            try:
                video_files = await asyncio.to_thread(self.file_scanner.scan_directory)
                
                self.processing_stats.files_scanned = len(video_files)
                ctx.update(current=len(video_files))
                ctx.set_metadata(files_found=len(video_files))
                
                self.logger.info(f"Found {len(video_files)} video files")
                return video_files
                
            except Exception as e:
                self.logger.error(f"Error scanning files: {e}")
                self.error_handler.handle_error(
                    e, 
                    context={'component': 'file_scanner'},
                    category=ErrorCategory.FILE_SYSTEM,
                    severity=ErrorSeverity.HIGH
                )
                return []
    
    async def _start_workers(self) -> None:
        """Start concurrent worker tasks."""
        processing_config = self.config.get('processing', {})
        max_workers = processing_config.get('max_concurrent_files', 3)
        
        self.logger.info(f"Starting {max_workers} worker tasks")
        
        for i in range(max_workers):
            worker_task = asyncio.create_task(
                self._worker_loop(f"worker-{i+1}"),
                name=f"worker-{i+1}"
            )
            self.worker_tasks.append(worker_task)
    
    async def _queue_files_for_processing(self, video_files: List[VideoFile]) -> None:
        """Queue video files for processing."""
        self.logger.info(f"Queuing {len(video_files)} files for processing")
        
        for video_file in video_files:
            await self.processing_queue.put(video_file)
        
        # Add sentinel values to signal workers to stop
        for _ in self.worker_tasks:
            await self.processing_queue.put(None)
    
    async def _worker_loop(self, worker_name: str) -> None:
        """Main worker loop for processing files."""
        self.logger.debug(f"Worker {worker_name} started")
        
        while not self.should_stop:
            try:
                # Get next file from queue
                video_file = await self.processing_queue.get()
                
                # Check for sentinel value (stop signal)
                if video_file is None:
                    break
                
                # Process the file
                await self._process_single_file(video_file, worker_name)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except asyncio.CancelledError:
                self.logger.debug(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in worker {worker_name}: {e}")
                self.error_handler.handle_error(
                    e,
                    context={'worker': worker_name, 'component': 'worker_loop'}
                )
        
        self.logger.debug(f"Worker {worker_name} stopped")
    
    async def _process_single_file(self, video_file: VideoFile, worker_name: str) -> None:
        """Process a single video file through the complete pipeline."""
        file_id = f"file_{video_file.filename}"
        
        with ProgressContext(
            file_id,
            f"Processing {video_file.filename}",
            total=4,  # Steps: scrape, organize, download, complete
            unit=ProgressUnit.COUNT,
            tracker=self.progress_tracker
        ) as ctx:
            
            self.logger.info(f"[{worker_name}] Processing {video_file.filename}")
            
            try:
                # Step 1: Scrape metadata
                ctx.set_metadata(step="scraping_metadata")
                metadata = await self._scrape_metadata(video_file)
                ctx.update(current=1)
                
                if not metadata:
                    self.logger.warning(f"No metadata found for {video_file.filename}")
                    self.processing_stats.errors_encountered += 1
                    return
                
                self.processing_stats.metadata_scraped += 1
                
                # Step 2: Organize file
                ctx.set_metadata(step="organizing_file")
                organize_result = await self._organize_file(video_file, metadata)
                ctx.update(current=2)
                
                if not organize_result['success']:
                    self.logger.error(f"Failed to organize {video_file.filename}: {organize_result['message']}")
                    self.processing_stats.errors_encountered += 1
                    return
                
                self.processing_stats.files_organized += 1
                
                # Step 3: Download images
                ctx.set_metadata(step="downloading_images")
                target_dir = Path(organize_result['details']['target_path']).parent
                await self._download_images(metadata, target_dir)
                ctx.update(current=3)
                
                # Step 4: Complete
                ctx.set_metadata(step="completed")
                ctx.update(current=4)
                
                self.processing_stats.files_processed += 1
                
                # Update progress persistence
                if self.current_session_id:
                    self.progress_persistence.update_session(processed_file=video_file.filename)
                
                self.logger.info(f"[{worker_name}] Successfully processed {video_file.filename}")
                
            except Exception as e:
                self.logger.error(f"[{worker_name}] Error processing {video_file.filename}: {e}")
                self.error_handler.handle_error(
                    e,
                    context={
                        'worker': worker_name,
                        'file': video_file.filename,
                        'component': 'file_processing'
                    }
                )
                self.processing_stats.errors_encountered += 1
                
                # Update progress persistence
                if self.current_session_id:
                    self.progress_persistence.update_session(failed_file=video_file.filename)
    
    async def _scrape_metadata(self, video_file: VideoFile) -> Optional[MovieMetadata]:
        """Scrape metadata for a video file."""
        try:
            # Extract movie code from filename
            movie_code = video_file.detected_code
            if not movie_code:
                self.logger.warning(f"No movie code detected for {video_file.filename}")
                return None
            
            # Scrape metadata
            metadata = await self.metadata_scraper.scrape_metadata(movie_code)
            
            if metadata:
                self.logger.debug(f"Scraped metadata for {movie_code}: {metadata.title}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error scraping metadata for {video_file.filename}: {e}")
            self.error_handler.handle_error(
                e,
                context={'file': video_file.filename, 'component': 'metadata_scraping'}
            )
            return None
    
    async def _organize_file(self, video_file: VideoFile, metadata: MovieMetadata) -> Dict[str, Any]:
        """Organize a video file based on its metadata."""
        try:
            result = await asyncio.to_thread(
                self.file_organizer.organize_file,
                video_file,
                metadata
            )
            
            if result['success']:
                self.logger.debug(f"Organized {video_file.filename} to {result['details']['target_path']}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error organizing {video_file.filename}: {e}")
            self.error_handler.handle_error(
                e,
                context={'file': video_file.filename, 'component': 'file_organization'}
            )
            return {'success': False, 'message': str(e)}
    
    async def _download_images(self, metadata: MovieMetadata, target_dir: Path) -> None:
        """Download images for a movie."""
        try:
            downloader_config = self.config.get('downloader', {})
            
            # Skip image download if disabled
            if not downloader_config.get('enabled', True):
                return
            
            # Determine which image types to download
            image_types = []
            if downloader_config.get('download_cover', True):
                image_types.append(ImageType.COVER)
            if downloader_config.get('download_poster', True):
                image_types.append(ImageType.POSTER)
            if downloader_config.get('download_screenshots', False):
                image_types.append(ImageType.SCREENSHOT)
            
            if not image_types:
                return
            
            result = await self.image_downloader.download_movie_images(
                metadata,
                target_dir,
                image_types
            )
            
            if result['success']:
                downloaded_count = len(result['downloaded_files'])
                self.processing_stats.images_downloaded += downloaded_count
                self.logger.debug(f"Downloaded {downloaded_count} images for {metadata.code}")
            else:
                self.logger.warning(f"Image download failed for {metadata.code}: {result['message']}")
            
        except Exception as e:
            self.logger.error(f"Error downloading images for {metadata.code}: {e}")
            self.error_handler.handle_error(
                e,
                context={'code': metadata.code, 'component': 'image_download'}
            )
    
    async def _wait_for_completion(self) -> None:
        """Wait for all processing to complete."""
        self.logger.info("Waiting for processing to complete...")
        
        # Wait for all items in queue to be processed
        await self.processing_queue.join()
        
        # Wait for all worker tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.logger.info("All processing completed")
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        if sys.platform != 'win32':
            # Unix-like systems
            loop = asyncio.get_event_loop()
            
            def signal_handler():
                self.logger.info("Received shutdown signal")
                asyncio.create_task(self.stop())
            
            loop.add_signal_handler(signal.SIGINT, signal_handler)
            loop.add_signal_handler(signal.SIGTERM, signal_handler)
    
    async def _detect_and_handle_duplicates(self, video_files: List[VideoFile]) -> List[VideoFile]:
        """Detect and handle duplicate files."""
        with PerformanceContext("duplicate_detection", self.performance_monitor):
            self.logger.info("Starting duplicate detection...")
            
            # Detect duplicates
            duplicate_report = await self.duplicate_detector.detect_duplicates(video_files)
            
            self.logger.info(
                f"Duplicate detection completed: {len(duplicate_report.duplicate_groups)} groups, "
                f"{duplicate_report.total_duplicates} duplicates, "
                f"{duplicate_report.wasted_space_mb:.1f}MB wasted space"
            )
            
            # Handle duplicates based on configuration
            duplicate_config = self.config.get('advanced', {}).get('duplicate_handling', {})
            strategy = DuplicateStrategy(duplicate_config.get('strategy', 'skip'))
            
            if strategy != DuplicateStrategy.SKIP and duplicate_report.duplicate_groups:
                handle_result = await self.duplicate_detector.handle_duplicates(
                    duplicate_report.duplicate_groups,
                    strategy,
                    dry_run=duplicate_config.get('dry_run', True)
                )
                
                self.logger.info(
                    f"Duplicate handling: {handle_result['files_deleted']} deleted, "
                    f"{handle_result['files_renamed']} renamed, "
                    f"{handle_result['space_freed'] / (1024*1024):.1f}MB freed"
                )
            
            # Return files excluding duplicates that were handled
            if strategy == DuplicateStrategy.SKIP:
                # Remove duplicate files from processing list
                duplicate_files = set()
                for group in duplicate_report.duplicate_groups:
                    # Keep the first file, skip the rest
                    for file in group.files[1:]:
                        duplicate_files.add(file.file_path)
                
                filtered_files = [f for f in video_files if f.file_path not in duplicate_files]
                self.logger.info(f"Skipped {len(duplicate_files)} duplicate files")
                return filtered_files
            
            return video_files
    
    async def _filter_processed_files(self, video_files: List[VideoFile]) -> List[VideoFile]:
        """Filter out files that have already been processed in current session."""
        if not self.current_session_id:
            return video_files
        
        session = self.progress_persistence.load_session(self.current_session_id)
        if not session:
            return video_files
        
        # Get already processed files
        processed_files = session.processed_files.union(session.failed_files).union(session.skipped_files)
        
        # Filter out processed files
        remaining_files = [f for f in video_files if f.filename not in processed_files]
        
        if len(remaining_files) < len(video_files):
            skipped_count = len(video_files) - len(remaining_files)
            self.logger.info(f"Skipped {skipped_count} already processed files")
        
        return remaining_files
    
    def _finalize_processing_session(self) -> None:
        """Finalize the current processing session."""
        if self.current_session_id:
            session_summary = self.progress_persistence.finalize_session()
            if session_summary:
                self.logger.info(
                    f"Session completed: {session_summary['processed_files']} processed, "
                    f"{session_summary['success_rate']:.1f}% success rate"
                )
    
    async def _cleanup(self) -> None:
        """Clean up resources and finalize processing."""
        self.logger.info("Cleaning up resources...")
        
        try:
            # Stop progress tracking
            self.progress_tracker.stop_auto_updates()
            
            # Stop performance monitoring
            if self.enable_performance_monitoring:
                self.performance_monitor.stop_monitoring()
                
                # Save performance report
                try:
                    report_file = self.performance_monitor.save_performance_report()
                    self.logger.info(f"Performance report saved: {report_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to save performance report: {e}")
            
            # Finalize processing session
            self._finalize_processing_session()
            
            # Finalize processing stats
            self.processing_stats.end_time = datetime.now()
            
            # Log final statistics
            self._log_final_statistics()
            
            # Clean up components
            if hasattr(self.metadata_scraper, 'cleanup'):
                await self.metadata_scraper.cleanup()
            
            self.is_running = False
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def _log_final_statistics(self) -> None:
        """Log final processing statistics."""
        stats = self.processing_stats
        
        self.logger.info("=== Processing Statistics ===")
        self.logger.info(f"Files scanned: {stats.files_scanned}")
        self.logger.info(f"Files processed: {stats.files_processed}")
        self.logger.info(f"Files organized: {stats.files_organized}")
        self.logger.info(f"Metadata scraped: {stats.metadata_scraped}")
        self.logger.info(f"Images downloaded: {stats.images_downloaded}")
        self.logger.info(f"Errors encountered: {stats.errors_encountered}")
        self.logger.info(f"Success rate: {stats.success_rate:.1f}%")
        
        if stats.duration:
            self.logger.info(f"Total duration: {stats.duration:.1f} seconds")
            if stats.files_processed > 0:
                rate = stats.files_processed / stats.duration
                self.logger.info(f"Processing rate: {rate:.2f} files/second")
        
        # Log component statistics
        scraper_stats = self.metadata_scraper.get_scraper_stats()
        organizer_stats = self.file_organizer.get_statistics()
        downloader_stats = self.image_downloader.get_statistics()
        error_stats = self.error_handler.get_error_statistics()
        
        self.logger.info(f"Scraper success rate: {scraper_stats['success_rate']:.1f}%")
        self.logger.info(f"Organizer success rate: {organizer_stats['success_rate']:.1f}%")
        self.logger.info(f"Downloader success rate: {downloader_stats['success_rate']:.1f}%")
        self.logger.info(f"Total errors handled: {error_stats['total_errors']}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current application status.
        
        Returns:
            Dictionary with current status information
        """
        status = {
            'is_running': self.is_running,
            'should_stop': self.should_stop,
            'processing_stats': {
                'files_scanned': self.processing_stats.files_scanned,
                'files_processed': self.processing_stats.files_processed,
                'files_organized': self.processing_stats.files_organized,
                'metadata_scraped': self.processing_stats.metadata_scraped,
                'images_downloaded': self.processing_stats.images_downloaded,
                'errors_encountered': self.processing_stats.errors_encountered,
                'success_rate': self.processing_stats.success_rate,
                'duration': self.processing_stats.duration
            },
            'active_tasks': len([t for t in self.worker_tasks if not t.done()]),
            'queue_size': self.processing_queue.qsize(),
            'progress': self.progress_tracker.get_overall_progress(),
            'component_stats': {
                'scraper': self.metadata_scraper.get_scraper_stats(),
                'organizer': self.file_organizer.get_statistics(),
                'downloader': self.image_downloader.get_statistics(),
                'error_handler': self.error_handler.get_error_statistics()
            }
        }
        
        # Add advanced features status
        if self.current_session_id:
            session_progress = self.progress_persistence.get_session_progress(self.current_session_id)
            status['session'] = session_progress
        
        if self.enable_performance_monitoring:
            status['performance'] = self.performance_monitor.get_performance_summary()
        
        status['advanced_features'] = {
            'duplicate_detection_enabled': self.enable_duplicate_detection,
            'performance_monitoring_enabled': self.enable_performance_monitoring,
            'current_session_id': self.current_session_id
        }
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform application health check.
        
        Returns:
            Dictionary with health status
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        try:
            # Check scraper health
            scraper_health = await self.metadata_scraper.health_check()
            health_status['components']['scrapers'] = scraper_health
            
            # Check file organizer
            organizer_validation = self.file_organizer.validate_target_directory()
            health_status['components']['organizer'] = {
                'target_directory_valid': organizer_validation['valid'],
                'errors': organizer_validation['errors']
            }
            
            # Check configuration
            config_validation = self.config_manager.validate_config()
            health_status['components']['configuration'] = {
                'valid': len(config_validation['errors']) == 0,
                'errors': config_validation['errors'],
                'warnings': config_validation['warnings']
            }
            
            # Overall health assessment
            component_issues = []
            for component, status in health_status['components'].items():
                if isinstance(status, dict):
                    if 'errors' in status and status['errors']:
                        component_issues.append(component)
                    elif hasattr(status, 'get') and not status.get('valid', True):
                        component_issues.append(component)
            
            if component_issues:
                health_status['status'] = 'degraded'
                health_status['issues'] = component_issues
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        return health_status


async def main():
    """Main entry point for the application."""
    try:
        # Create and start the application
        app = AVMetadataScraper()
        await app.start()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())