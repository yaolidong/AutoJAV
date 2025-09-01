"""Scan command implementation."""

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from .base_command import BaseCommand
from ...main_application import AVMetadataScraper


class ScanCommand(BaseCommand):
    """Command to scan for video files without processing them."""
    
    @property
    def name(self) -> str:
        return 'scan'
    
    @property
    def description(self) -> str:
        return 'Scan directory for video files and show information'
    
    def add_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Add scan command parser."""
        parser = self._create_parser(
            subparsers,
            epilog="""
Examples:
  av-scraper scan                              # Scan default directory
  av-scraper scan --source /videos            # Scan specific directory
  av-scraper scan --show-codes                # Show detected movie codes
  av-scraper scan --format table              # Display as table
  av-scraper scan --export scan_results.json  # Export results to file
            """
        )
        
        # Source directory
        parser.add_argument(
            '--source', '-s',
            type=Path,
            help='Directory to scan for video files'
        )
        
        # Display options
        parser.add_argument(
            '--format',
            choices=['list', 'table', 'json'],
            default='list',
            help='Output format (default: list)'
        )
        
        parser.add_argument(
            '--show-codes',
            action='store_true',
            help='Show detected movie codes'
        )
        
        parser.add_argument(
            '--show-sizes',
            action='store_true',
            help='Show file sizes'
        )
        
        parser.add_argument(
            '--show-paths',
            action='store_true',
            help='Show full file paths'
        )
        
        # Filtering options
        parser.add_argument(
            '--include-pattern',
            help='Only include files matching this pattern (glob)'
        )
        
        parser.add_argument(
            '--exclude-pattern',
            help='Exclude files matching this pattern (glob)'
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
        
        parser.add_argument(
            '--extensions',
            nargs='+',
            help='File extensions to include (e.g., .mp4 .mkv)'
        )
        
        # Sorting options
        parser.add_argument(
            '--sort-by',
            choices=['name', 'size', 'date', 'code'],
            default='name',
            help='Sort files by (default: name)'
        )
        
        parser.add_argument(
            '--reverse',
            action='store_true',
            help='Reverse sort order'
        )
        
        # Export options
        parser.add_argument(
            '--export',
            type=Path,
            help='Export results to file (JSON format)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of results shown'
        )
        
        return parser
    
    async def execute(self, args: argparse.Namespace, app: Optional[AVMetadataScraper] = None) -> Dict[str, Any]:
        """Execute the scan command."""
        app = self._validate_app_required(app)
        
        try:
            # Override source directory if specified
            if args.source:
                app.file_scanner.source_directory = str(args.source)
            
            # Apply filtering options
            self._apply_scan_filters(app, args)
            
            # Perform scan
            video_files = await app._scan_files()
            
            if not video_files:
                return self._format_result(
                    success=True,
                    message="No video files found",
                    files_found=0
                )
            
            # Apply sorting
            video_files = self._sort_files(video_files, args)
            
            # Apply limit
            if args.limit:
                video_files = video_files[:args.limit]
            
            # Prepare results
            scan_results = self._prepare_scan_results(video_files, args)
            
            # Export if requested
            if args.export:
                await self._export_results(scan_results, args.export)
            
            # Format output based on requested format
            if args.format == 'json':
                return scan_results
            elif args.format == 'table':
                self._print_table_format(scan_results['files'], args)
            else:  # list format
                self._print_list_format(scan_results['files'], args)
            
            return self._format_result(
                success=True,
                message=f"Found {len(video_files)} video files",
                **scan_results
            )
            
        except Exception as e:
            return self._format_result(
                success=False,
                message=f"Scan failed: {e}",
                error=str(e)
            )
    
    def _apply_scan_filters(self, app: AVMetadataScraper, args: argparse.Namespace) -> None:
        """Apply filtering options to the file scanner."""
        # This would require extending the FileScanner class to support these filters
        # For now, we'll note what filters would be applied
        filters = {}
        
        if args.include_pattern:
            filters['include_pattern'] = args.include_pattern
        
        if args.exclude_pattern:
            filters['exclude_pattern'] = args.exclude_pattern
        
        if args.extensions:
            app.file_scanner.supported_formats = args.extensions
        
        # Size filters would need to be implemented in FileScanner
        if args.min_size:
            filters['min_size'] = self._parse_size(args.min_size)
        
        if args.max_size:
            filters['max_size'] = self._parse_size(args.max_size)
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string (e.g., '100MB', '1GB') to bytes."""
        size_str = size_str.upper()
        
        if size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        elif size_str.endswith('TB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024 * 1024)
        else:
            return int(size_str)  # Assume bytes
    
    def _sort_files(self, video_files: list, args: argparse.Namespace) -> list:
        """Sort video files based on specified criteria."""
        sort_key = None
        
        if args.sort_by == 'name':
            sort_key = lambda f: f.filename.lower()
        elif args.sort_by == 'size':
            sort_key = lambda f: f.size_bytes
        elif args.sort_by == 'date':
            sort_key = lambda f: f.modified_time
        elif args.sort_by == 'code':
            sort_key = lambda f: f.detected_code or ''
        
        if sort_key:
            video_files.sort(key=sort_key, reverse=args.reverse)
        
        return video_files
    
    def _prepare_scan_results(self, video_files: list, args: argparse.Namespace) -> Dict[str, Any]:
        """Prepare scan results for output."""
        files_data = []
        total_size = 0
        codes_found = 0
        
        for video_file in video_files:
            file_data = {
                'filename': video_file.filename,
                'size_bytes': video_file.size_bytes,
                'size_human': self._format_size(video_file.size_bytes),
                'extension': video_file.extension,
                'modified_time': video_file.modified_time.isoformat() if video_file.modified_time else None,
            }
            
            if args.show_paths:
                file_data['full_path'] = str(video_file.file_path)
            
            if args.show_codes or args.sort_by == 'code':
                file_data['detected_code'] = video_file.detected_code
                if video_file.detected_code:
                    codes_found += 1
            
            files_data.append(file_data)
            total_size += video_file.size_bytes
        
        return {
            'files': files_data,
            'summary': {
                'total_files': len(video_files),
                'total_size_bytes': total_size,
                'total_size_human': self._format_size(total_size),
                'codes_detected': codes_found,
                'code_detection_rate': (codes_found / len(video_files) * 100) if video_files else 0,
                'extensions': list(set(f.extension for f in video_files)),
                'scan_timestamp': self._get_timestamp()
            }
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _print_list_format(self, files_data: list, args: argparse.Namespace) -> None:
        """Print files in list format."""
        for file_data in files_data:
            line_parts = [file_data['filename']]
            
            if args.show_sizes:
                line_parts.append(f"({file_data['size_human']})")
            
            if args.show_codes and file_data.get('detected_code'):
                line_parts.append(f"[{file_data['detected_code']}]")
            
            if args.show_paths:
                line_parts.append(f"-> {file_data['full_path']}")
            
            print(" ".join(line_parts))
    
    def _print_table_format(self, files_data: list, args: argparse.Namespace) -> None:
        """Print files in table format."""
        # Simple table implementation
        headers = ['Filename']
        
        if args.show_sizes:
            headers.append('Size')
        
        if args.show_codes:
            headers.append('Code')
        
        if args.show_paths:
            headers.append('Path')
        
        # Print headers
        print(" | ".join(f"{h:<20}" for h in headers))
        print("-" * (len(headers) * 23 - 3))
        
        # Print rows
        for file_data in files_data:
            row = [file_data['filename'][:20]]
            
            if args.show_sizes:
                row.append(file_data['size_human'])
            
            if args.show_codes:
                code = file_data.get('detected_code', '')
                row.append(code[:20] if code else '-')
            
            if args.show_paths:
                path = file_data.get('full_path', '')
                row.append(path[:30] + '...' if len(path) > 30 else path)
            
            print(" | ".join(f"{cell:<20}" for cell in row))
    
    async def _export_results(self, results: Dict[str, Any], export_path: Path) -> None:
        """Export scan results to file."""
        import json
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Results exported to: {export_path}")