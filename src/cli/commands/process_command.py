"""Process command implementation."""

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper


class ProcessCommand(BaseCommand):
    """Command to start the main processing pipeline."""
    
    @property
    def name(self) -> str:
        return 'process'
    
    @property
    def description(self) -> str:
        return 'Start processing video files (scan, scrape metadata, organize)'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add process command parser."""
        parser = self._create_parser(
            subparsers,
            epilog="""
Examples:
  av-scraper process                           # Process with default settings
  av-scraper process --source /videos         # Process specific directory
  av-scraper process --dry-run                # Preview what would be done
  av-scraper process --max-concurrent 5       # Use 5 concurrent workers
  av-scraper process --skip-images            # Skip image downloads
            """
        )
        
        # Source directory
        parser.add_argument(
            '--source', '-s',
            type=Path,
            help='Source directory to scan for video files'
        )
        
        # Target directory
        parser.add_argument(
            '--target', '-t',
            type=Path,
            help='Target directory for organized files'
        )
        
        # Processing options
        parser.add_argument(
            '--dry-run', '-n',
            action='store_true',
            help='Preview operations without making changes'
        )
        
        parser.add_argument(
            '--max-concurrent',
            type=int,
            help='Maximum number of concurrent file processors'
        )
        
        parser.add_argument(
            '--skip-images',
            action='store_true',
            help='Skip image downloads'
        )
        
        parser.add_argument(
            '--skip-metadata',
            action='store_true',
            help='Skip metadata scraping (organize by filename only)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force processing even if files already exist'
        )
        
        # Filtering options
        parser.add_argument(
            '--include-pattern',
            help='Only process files matching this pattern (glob)'
        )
        
        parser.add_argument(
            '--exclude-pattern',
            help='Skip files matching this pattern (glob)'
        )
        
        parser.add_argument(
            '--min-size',
            type=str,
            help='Minimum file size (e.g., 100MB, 1GB)'
        )
        
        parser.add_argument(
            '--max-size',
            type=str,
            help='Maximum file size (e.g., 10GB)'
        )
        
        # Resume options
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Resume from previous interrupted session'
        )
        
        parser.add_argument(
            '--checkpoint-file',
            type=Path,
            help='File to save/load processing checkpoint'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the process command."""
        app = self._validate_app_required(app)
        
        try:
            # Override configuration with command line arguments
            await self._apply_command_overrides(app, args)
            
            # Handle dry run mode
            if args.dry_run:
                return await self._execute_dry_run(app, args)
            
            # Handle resume mode
            if args.resume:
                return await self._execute_resume(app, args)
            
            # Normal processing
            return await self._execute_normal_processing(app, args)
            
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Processing failed: {e}",
                error=str(e)
            )
    
    async def _apply_command_overrides(self, app: AVMetadataScraper, args: argparse.Namespace) -> None:
        """Apply command line argument overrides to application configuration."""
        config_overrides = {}
        
        # Directory overrides
        if args.source:
            config_overrides['scanner'] = config_overrides.get('scanner', {})
            config_overrides['scanner']['source_directory'] = str(args.source)
        
        if args.target:
            config_overrides['organizer'] = config_overrides.get('organizer', {})
            config_overrides['organizer']['target_directory'] = str(args.target)
        
        # Processing overrides
        if args.max_concurrent:
            config_overrides['processing'] = config_overrides.get('processing', {})
            config_overrides['processing']['max_concurrent_files'] = args.max_concurrent
        
        if args.skip_images:
            config_overrides['downloader'] = config_overrides.get('downloader', {})
            config_overrides['downloader']['enabled'] = False
        
        # Apply overrides
        if config_overrides:
            app.config_manager.update_config(config_overrides)
            # Reinitialize components with new config
            app._initialize_components()
    
    async def _execute_dry_run(self, app: AVMetadataScraper, args: argparse.Namespace) -> Dict[str, Any]:
        """Execute dry run mode - preview operations without making changes."""
        # Scan files
        video_files = await app._scan_files()
        
        if not video_files:
            return self._format_result(
                success=True,
                message="No video files found to process",
                files_found=0
            )
        
        # Preview operations
        preview_results = []
        
        for video_file in video_files[:10]:  # Limit preview to first 10 files
            preview = {
                'file': video_file.filename,
                'size': video_file.size_bytes,
                'detected_code': video_file.detected_code,
                'would_scrape_metadata': not args.skip_metadata,
                'would_download_images': not args.skip_images,
            }
            
            # Predict target path
            if video_file.detected_code:
                # This would require implementing a preview method in organizer
                preview['predicted_target'] = f"[actress]/{video_file.detected_code}/{video_file.detected_code}.{video_file.extension}"
            else:
                preview['predicted_target'] = f"unknown/{video_file.filename}"
            
            preview_results.append(preview)
        
        return self._format_result(
            success=True,
            message=f"Dry run completed - would process {len(video_files)} files",
            files_found=len(video_files),
            preview_results=preview_results,
            total_size=sum(f.size_bytes for f in video_files),
            dry_run=True
        )
    
    async def _execute_resume(self, app: AVMetadataScraper, args: argparse.Namespace) -> Dict[str, Any]:
        """Execute resume mode - continue from previous checkpoint."""
        checkpoint_file = args.checkpoint_file or Path('processing_checkpoint.json')
        
        if not checkpoint_file.exists():
            return self._format_result(
                success=False,
                message=f"Checkpoint file not found: {checkpoint_file}",
                checkpoint_file=str(checkpoint_file)
            )
        
        # Load checkpoint (this would need to be implemented in the main app)
        # For now, just start normal processing
        return await self._execute_normal_processing(app, args)
    
    async def _execute_normal_processing(self, app: AVMetadataScraper, args: argparse.Namespace) -> Dict[str, Any]:
        """Execute normal processing mode."""
        # Start the application
        await app.start()
        
        # Get final statistics
        status = app.get_status()
        stats = status['processing_stats']
        
        return self._format_result(
            success=stats['errors_encountered'] == 0,
            message=f"Processing completed - {stats['files_processed']}/{stats['files_scanned']} files processed successfully",
            statistics=stats,
            component_stats=status['component_stats']
        )