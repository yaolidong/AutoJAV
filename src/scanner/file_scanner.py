"""File scanner for detecting and analyzing video files - Fixed version."""

import os
import re
import logging
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime

from ..models.video_file import VideoFile
from ..utils.pattern_manager import PatternManager


class FileScanner:
    """Scans directories for video files and extracts metadata."""
    
    def __init__(self, source_directory: str, supported_formats: List[str], use_pattern_manager: bool = True):
        """
        Initialize the file scanner.
        
        Args:
            source_directory: Directory to scan for video files
            supported_formats: List of supported video file extensions
            use_pattern_manager: Whether to use PatternManager for code extraction
        """
        self.source_directory = Path(source_directory)
        self.supported_formats = [fmt.lower() for fmt in supported_formats]
        self.logger = logging.getLogger(__name__)
        self.use_pattern_manager = use_pattern_manager
        
        # Initialize pattern manager if requested
        if self.use_pattern_manager:
            try:
                # PatternManager will automatically find the correct path
                self.pattern_manager = PatternManager()
                self.logger.info("Using PatternManager for code extraction")
            except Exception as e:
                self.logger.warning(f"Failed to initialize PatternManager: {e}, falling back to built-in patterns")
                self.use_pattern_manager = False
        
        # Common AV code patterns (fallback if PatternManager not available)
        # Updated patterns to match both hyphen and space after cleaning
        self.code_patterns = [
            # Standard patterns like ABC-123, ABCD-123 (also matches with space)
            r'([A-Z]{2,5})[\s\-]?(\d{3,4})',
            # Patterns with numbers in prefix like 1PON-123456
            r'(\d+[A-Z]+)[\s\-]?(\d+)',
            # FC2 patterns like FC2-PPV-123456
            r'(FC2)[\s\-]?(PPV)?[\s\-]?(\d+)',
            # Carib patterns like 123456-789
            r'(\d{6})[\s\-](\d{3})',
            # Tokyo Hot patterns like n1234
            r'(n)\s?(\d{4})',
            # Heydouga patterns like 4017-PPV123
            r'(\d{4})[\s\-]?(PPV)?(\d+)',
        ]
        
        # Compile regex patterns for better performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.code_patterns]
    
    def scan_directory(self) -> List[VideoFile]:
        """
        Scan the source directory for video files.
        
        Returns:
            List of VideoFile objects found in the directory
            
        Raises:
            FileNotFoundError: If source directory doesn't exist
            PermissionError: If directory is not accessible
        """
        if not self.source_directory.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_directory}")
        
        if not self.source_directory.is_dir():
            raise NotADirectoryError(f"Source path is not a directory: {self.source_directory}")
        
        self.logger.info(f"Scanning directory: {self.source_directory}")
        video_files = []
        scanned_count = 0
        
        try:
            for file_path in self._walk_directory(self.source_directory):
                scanned_count += 1
                if scanned_count % 100 == 0:
                    self.logger.debug(f"Scanned {scanned_count} files...")
                
                if self.is_video_file(file_path):
                    try:
                        video_file = self._create_video_file(file_path)
                        if video_file:
                            video_files.append(video_file)
                    except Exception as e:
                        self.logger.warning(f"Error processing file {file_path}: {e}")
                        continue
            
            self.logger.info(f"Found {len(video_files)} video files out of {scanned_count} total files")
            return video_files
            
        except PermissionError as e:
            self.logger.error(f"Permission denied accessing directory: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error scanning directory: {e}")
            raise
    
    def _walk_directory(self, directory: Path):
        """
        Recursively walk through directory and yield file paths.
        
        Args:
            directory: Directory to walk through
            
        Yields:
            Path objects for each file found
        """
        try:
            for item in directory.iterdir():
                if item.is_file():
                    yield item
                elif item.is_dir() and not self._should_skip_directory(item):
                    yield from self._walk_directory(item)
        except PermissionError:
            self.logger.warning(f"Permission denied accessing: {directory}")
        except Exception as e:
            self.logger.warning(f"Error accessing directory {directory}: {e}")
    
    def _should_skip_directory(self, directory: Path) -> bool:
        """
        Check if a directory should be skipped during scanning.
        
        Args:
            directory: Directory to check
            
        Returns:
            True if directory should be skipped
        """
        skip_patterns = {
            # Hidden directories
            '.',
            # System directories
            '__pycache__',
            '.git',
            '.svn',
            # Temporary directories
            'tmp',
            'temp',
            # Recycle bin
            '$RECYCLE.BIN',
            'Trash',
        }
        
        dir_name = directory.name.lower()
        return (
            dir_name.startswith('.') or
            dir_name in skip_patterns or
            # Skip very deep nested directories (potential infinite loops)
            len(directory.parts) > 20
        )
    
    def is_video_file(self, file_path: Path) -> bool:
        """
        Check if a file is a supported video file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file is a supported video format
        """
        if not file_path.is_file():
            return False
        
        extension = file_path.suffix.lower()
        return extension in self.supported_formats
    
    def _create_video_file(self, file_path: Path) -> Optional[VideoFile]:
        """
        Create a VideoFile object from a file path.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            VideoFile object or None if creation fails
        """
        try:
            stat = file_path.stat()
            
            video_file = VideoFile(
                file_path=str(file_path),
                filename=file_path.name,
                file_size=stat.st_size,
                extension=file_path.suffix.lower(),
                created_time=datetime.fromtimestamp(stat.st_ctime),
                modified_time=datetime.fromtimestamp(stat.st_mtime)
            )
            
            # Extract code from filename
            detected_code = self.extract_code_from_filename(file_path.name)
            if detected_code:
                video_file.detected_code = detected_code
                self.logger.debug(f"Detected code '{detected_code}' from file: {file_path.name}")
            else:
                self.logger.debug(f"No code detected from file: {file_path.name}")
            
            return video_file
            
        except Exception as e:
            self.logger.error(f"Error creating VideoFile for {file_path}: {e}")
            return None
    
    def extract_code_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract AV code from filename using various patterns.
        
        Args:
            filename: Name of the file to extract code from
            
        Returns:
            Extracted code or None if no code found
        """
        # Use PatternManager if available
        if self.use_pattern_manager and hasattr(self, 'pattern_manager'):
            code = self.pattern_manager.extract_code(filename)
            if code:
                return code
        
        # Fallback to built-in patterns
        # Remove file extension
        name_without_ext = Path(filename).stem
        
        # Clean up common prefixes/suffixes
        cleaned_name = self._clean_filename(name_without_ext)
        
        # Try each pattern
        for pattern in self.compiled_patterns:
            match = pattern.search(cleaned_name)
            if match:
                code = self._format_code(match)
                if code:
                    return code.upper()
        
        return None
    
    def _clean_filename(self, filename: str) -> str:
        """
        Clean filename by removing common prefixes, suffixes, and noise.
        
        Args:
            filename: Filename to clean
            
        Returns:
            Cleaned filename
        """
        # Remove common prefixes
        prefixes_to_remove = [
            r'^\[.*?\]',  # Remove [tags] at the beginning
            r'^\(.*?\)',  # Remove (tags) at the beginning
            r'^【.*?】',   # Remove 【tags】 at the beginning
        ]
        
        cleaned = filename
        for prefix_pattern in prefixes_to_remove:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove common suffixes
        suffixes_to_remove = [
            r'\[.*?\]$',  # Remove [tags] at the end
            r'\(.*?\)$',  # Remove (tags) at the end
            r'【.*?】$',   # Remove 【tags】 at the end
            r'_\d+p$',    # Remove quality indicators like _1080p
            r'_HD$',      # Remove HD suffix
            r'_FHD$',     # Remove FHD suffix
            r'_4K$',      # Remove 4K suffix
        ]
        
        for suffix_pattern in suffixes_to_remove:
            cleaned = re.sub(suffix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Replace underscores and dots with spaces, but preserve hyphens between letters and numbers
        # This helps maintain the structure of codes like JUL-777
        cleaned = re.sub(r'[_\.]', ' ', cleaned)
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def _format_code(self, match: re.Match) -> Optional[str]:
        """
        Format the matched code according to standard conventions.
        
        Args:
            match: Regex match object
            
        Returns:
            Formatted code or None if invalid
        """
        groups = match.groups()
        
        if len(groups) >= 2:
            prefix = groups[0]
            number = groups[1]
            
            # Handle special cases
            if prefix.upper() == 'FC2':
                # FC2-PPV-123456 or FC2-123456 format
                if len(groups) >= 3 and groups[2]:
                    # If PPV is captured in groups[1], number is in groups[2]
                    if groups[1] and groups[1].upper() == 'PPV':
                        return f"FC2-PPV-{groups[2]}"
                    else:
                        return f"FC2-PPV-{groups[2]}"
                else:
                    return f"FC2-PPV-{number}"
            
            elif prefix.upper() == 'N':
                # Tokyo Hot n1234 format
                return f"n{number}"
            
            elif prefix.isdigit():
                # Patterns like 1PON-123456 or Carib 123456-789
                if len(groups) >= 3:
                    return f"{prefix}-{groups[2]}"
                else:
                    return f"{prefix}-{number}"
            
            else:
                # Standard ABC-123 format
                return f"{prefix}-{number}"
        
        return None
    
    def get_scan_statistics(self, video_files: List[VideoFile]) -> dict:
        """
        Get statistics about the scanned files.
        
        Args:
            video_files: List of video files to analyze
            
        Returns:
            Dictionary containing scan statistics
        """
        if not video_files:
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'files_with_codes': 0,
                'files_without_codes': 0,
                'extensions': {},
                'average_size_mb': 0
            }
        
        total_size = sum(vf.file_size for vf in video_files)
        files_with_codes = sum(1 for vf in video_files if vf.detected_code)
        
        # Count extensions
        extensions = {}
        for vf in video_files:
            ext = vf.extension
            extensions[ext] = extensions.get(ext, 0) + 1
        
        return {
            'total_files': len(video_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'files_with_codes': files_with_codes,
            'files_without_codes': len(video_files) - files_with_codes,
            'extensions': extensions,
            'average_size_mb': round(total_size / len(video_files) / (1024 * 1024), 2)
        }