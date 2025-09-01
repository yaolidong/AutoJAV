"""File organizer for moving and organizing video files based on metadata."""

import os
import json
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum

from ..models.video_file import VideoFile
from ..models.movie_metadata import MovieMetadata


class ConflictResolution(Enum):
    """Strategies for handling file conflicts."""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"
    ASK = "ask"


class FileOrganizer:
    """
    Organizes video files based on metadata with configurable naming patterns.
    
    This class handles moving video files to organized directory structures,
    creating metadata files, and managing file conflicts.
    """
    
    def __init__(
        self,
        target_directory: str,
        naming_pattern: str = "{actress}/{code}/{code}.{ext}",
        conflict_resolution: ConflictResolution = ConflictResolution.RENAME,
        create_metadata_files: bool = True,
        verify_file_integrity: bool = True,
        max_filename_length: int = 255,
        safe_mode: bool = True
    ):
        """
        Initialize the file organizer.
        
        Args:
            target_directory: Base directory for organized files
            naming_pattern: Pattern for file naming (supports placeholders)
            conflict_resolution: Strategy for handling file conflicts
            create_metadata_files: Whether to create metadata JSON files
            verify_file_integrity: Whether to verify file integrity after moving
            max_filename_length: Maximum filename length (OS dependent)
            safe_mode: If True, copy files instead of moving them
        """
        self.target_directory = Path(target_directory)
        self.naming_pattern = naming_pattern
        self.conflict_resolution = conflict_resolution
        self.create_metadata_files = create_metadata_files
        self.verify_file_integrity = verify_file_integrity
        self.max_filename_length = max_filename_length
        self.safe_mode = safe_mode
        
        self.logger = logging.getLogger(__name__)
        
        # Statistics tracking
        self.stats = {
            'files_processed': 0,
            'files_moved': 0,
            'files_copied': 0,
            'files_skipped': 0,
            'conflicts_resolved': 0,
            'metadata_files_created': 0,
            'errors': 0
        }
        
        # Ensure target directory exists
        self.target_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Initialized FileOrganizer with target: {self.target_directory}")
    
    def organize_file(
        self,
        video_file: VideoFile,
        metadata: MovieMetadata,
        custom_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Organize a single video file based on its metadata.
        
        Args:
            video_file: Video file to organize
            metadata: Metadata for the video file
            custom_pattern: Optional custom naming pattern for this file
            
        Returns:
            Dictionary with organization results
        """
        self.stats['files_processed'] += 1
        
        try:
            self.logger.info(f"Organizing file: {video_file.filename}")
            
            # Generate target path
            pattern = custom_pattern or self.naming_pattern
            target_path = self._generate_target_path(video_file, metadata, pattern)
            
            if not target_path:
                self.logger.error(f"Failed to generate target path for {video_file.filename}")
                self.stats['errors'] += 1
                return self._create_result(False, "Failed to generate target path")
            
            # Create target directory
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle file conflicts
            final_target_path = self._resolve_conflicts(target_path, video_file)
            
            if not final_target_path:
                self.logger.warning(f"Skipped file due to conflict: {video_file.filename}")
                self.stats['files_skipped'] += 1
                return self._create_result(False, "Skipped due to conflict")
            
            # Move or copy the file
            success = self._transfer_file(Path(video_file.file_path), final_target_path)
            
            if not success:
                self.logger.error(f"Failed to transfer file: {video_file.filename}")
                self.stats['errors'] += 1
                return self._create_result(False, "File transfer failed")
            
            # Create metadata file if requested
            metadata_file_path = None
            if self.create_metadata_files:
                metadata_file_path = self._create_metadata_file(final_target_path, metadata)
            
            # Update statistics
            if self.safe_mode:
                self.stats['files_copied'] += 1
            else:
                self.stats['files_moved'] += 1
            
            result = self._create_result(
                True,
                "File organized successfully",
                {
                    'original_path': video_file.file_path,
                    'target_path': str(final_target_path),
                    'metadata_file': str(metadata_file_path) if metadata_file_path else None,
                    'operation': 'copy' if self.safe_mode else 'move'
                }
            )
            
            self.logger.info(f"Successfully organized: {video_file.filename} -> {final_target_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error organizing file {video_file.filename}: {e}")
            self.stats['errors'] += 1
            return self._create_result(False, f"Error: {str(e)}")
    
    def organize_multiple(
        self,
        file_metadata_pairs: List[Tuple[VideoFile, MovieMetadata]]
    ) -> Dict[str, Any]:
        """
        Organize multiple files in batch.
        
        Args:
            file_metadata_pairs: List of (VideoFile, MovieMetadata) tuples
            
        Returns:
            Dictionary with batch organization results
        """
        self.logger.info(f"Starting batch organization of {len(file_metadata_pairs)} files")
        
        results = []
        successful = 0
        failed = 0
        
        for video_file, metadata in file_metadata_pairs:
            try:
                result = self.organize_file(video_file, metadata)
                results.append({
                    'file': video_file.filename,
                    'result': result
                })
                
                if result['success']:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                self.logger.error(f"Error in batch processing {video_file.filename}: {e}")
                results.append({
                    'file': video_file.filename,
                    'result': self._create_result(False, f"Batch error: {str(e)}")
                })
                failed += 1
        
        batch_result = {
            'total_files': len(file_metadata_pairs),
            'successful': successful,
            'failed': failed,
            'results': results,
            'statistics': self.get_statistics()
        }
        
        self.logger.info(f"Batch organization completed: {successful}/{len(file_metadata_pairs)} successful")
        return batch_result
    
    def _generate_target_path(
        self,
        video_file: VideoFile,
        metadata: MovieMetadata,
        pattern: str
    ) -> Optional[Path]:
        """
        Generate target file path based on naming pattern.
        
        Args:
            video_file: Video file information
            metadata: Movie metadata
            pattern: Naming pattern with placeholders
            
        Returns:
            Target path or None if generation failed
        """
        try:
            # Prepare replacement variables
            variables = {
                'code': self._sanitize_filename(metadata.code),
                'title': self._sanitize_filename(metadata.title),
                'title_en': self._sanitize_filename(metadata.title_en or metadata.title),
                'actress': self._get_primary_actress(metadata),
                'actresses': self._get_actresses_string(metadata),
                'studio': self._sanitize_filename(metadata.studio or 'Unknown'),
                'series': self._sanitize_filename(metadata.series or ''),
                'year': str(metadata.release_date.year) if metadata.release_date else 'Unknown',
                'month': f"{metadata.release_date.month:02d}" if metadata.release_date else 'Unknown',
                'day': f"{metadata.release_date.day:02d}" if metadata.release_date else 'Unknown',
                'ext': video_file.extension.lstrip('.'),
                'original_name': Path(video_file.filename).stem
            }
            
            # Replace placeholders in pattern
            try:
                relative_path = pattern.format(**variables)
            except KeyError as e:
                self.logger.error(f"Unknown placeholder in pattern: {e}")
                return None
            
            # Ensure path length is within limits
            relative_path = self._truncate_path_components(relative_path)
            
            # Create full target path
            target_path = self.target_directory / relative_path
            
            return target_path
            
        except Exception as e:
            self.logger.error(f"Error generating target path: {e}")
            return None
    
    def _get_primary_actress(self, metadata: MovieMetadata) -> str:
        """
        Get primary actress name for directory structure.
        
        Args:
            metadata: Movie metadata
            
        Returns:
            Primary actress name (sanitized)
        """
        if not metadata.actresses:
            return "Unknown"
        
        # Use first actress as primary
        primary_actress = metadata.actresses[0]
        return self._sanitize_filename(primary_actress)
    
    def _get_actresses_string(self, metadata: MovieMetadata) -> str:
        """
        Get formatted actresses string.
        
        Args:
            metadata: Movie metadata
            
        Returns:
            Formatted actresses string
        """
        if not metadata.actresses:
            return "Unknown"
        
        # Join multiple actresses with separator
        actresses_str = ", ".join(metadata.actresses[:3])  # Limit to first 3
        if len(metadata.actresses) > 3:
            actresses_str += f" (+{len(metadata.actresses) - 3} more)"
        
        return self._sanitize_filename(actresses_str)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        if not filename:
            return "Unknown"
        
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Ensure not empty
        if not sanitized:
            sanitized = "Unknown"
        
        return sanitized
    
    def _truncate_path_components(self, path: str) -> str:
        """
        Truncate path components to fit within filesystem limits.
        
        Args:
            path: Original path
            
        Returns:
            Truncated path
        """
        parts = Path(path).parts
        truncated_parts = []
        
        for part in parts:
            if len(part) > self.max_filename_length:
                # Truncate while preserving extension
                if '.' in part:
                    name, ext = part.rsplit('.', 1)
                    max_name_length = self.max_filename_length - len(ext) - 1
                    truncated_part = name[:max_name_length] + '.' + ext
                else:
                    truncated_part = part[:self.max_filename_length]
                
                truncated_parts.append(truncated_part)
            else:
                truncated_parts.append(part)
        
        return str(Path(*truncated_parts))
    
    def _resolve_conflicts(self, target_path: Path, video_file: VideoFile) -> Optional[Path]:
        """
        Resolve file conflicts based on configured strategy.
        
        Args:
            target_path: Intended target path
            video_file: Video file being organized
            
        Returns:
            Final target path or None if skipped
        """
        if not target_path.exists():
            return target_path
        
        self.stats['conflicts_resolved'] += 1
        
        if self.conflict_resolution == ConflictResolution.SKIP:
            self.logger.info(f"Skipping existing file: {target_path}")
            return None
        
        elif self.conflict_resolution == ConflictResolution.OVERWRITE:
            self.logger.info(f"Overwriting existing file: {target_path}")
            return target_path
        
        elif self.conflict_resolution == ConflictResolution.RENAME:
            return self._generate_unique_path(target_path)
        
        elif self.conflict_resolution == ConflictResolution.ASK:
            # In automated context, default to rename
            self.logger.info(f"Auto-renaming conflicted file: {target_path}")
            return self._generate_unique_path(target_path)
        
        return target_path
    
    def _generate_unique_path(self, target_path: Path) -> Path:
        """
        Generate unique path by adding counter suffix.
        
        Args:
            target_path: Original target path
            
        Returns:
            Unique target path
        """
        counter = 1
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = parent / new_name
            
            if not new_path.exists():
                self.logger.info(f"Generated unique path: {new_path}")
                return new_path
            
            counter += 1
            
            # Prevent infinite loop
            if counter > 9999:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"{stem}_{timestamp}{suffix}"
                return parent / new_name
    
    def _transfer_file(self, source_path: Path, target_path: Path) -> bool:
        """
        Transfer file from source to target location.
        
        Args:
            source_path: Source file path
            target_path: Target file path
            
        Returns:
            True if transfer successful, False otherwise
        """
        try:
            if self.safe_mode:
                # Copy file (safer, keeps original)
                shutil.copy2(source_path, target_path)
                self.logger.debug(f"Copied file: {source_path} -> {target_path}")
            else:
                # Move file (more efficient)
                shutil.move(str(source_path), str(target_path))
                self.logger.debug(f"Moved file: {source_path} -> {target_path}")
            
            # Verify file integrity if requested
            if self.verify_file_integrity:
                if not self._verify_file_integrity(source_path, target_path):
                    self.logger.error(f"File integrity verification failed: {target_path}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error transferring file {source_path} -> {target_path}: {e}")
            return False
    
    def _verify_file_integrity(self, source_path: Path, target_path: Path) -> bool:
        """
        Verify file integrity by comparing checksums.
        
        Args:
            source_path: Original file path
            target_path: Target file path
            
        Returns:
            True if files match, False otherwise
        """
        try:
            # Skip verification if source no longer exists (moved)
            if not source_path.exists():
                return True
            
            source_hash = self._calculate_file_hash(source_path)
            target_hash = self._calculate_file_hash(target_path)
            
            return source_hash == target_hash
            
        except Exception as e:
            self.logger.error(f"Error verifying file integrity: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def _create_metadata_file(self, video_path: Path, metadata: MovieMetadata) -> Optional[Path]:
        """
        Create metadata JSON file alongside video file.
        
        Args:
            video_path: Path to video file
            metadata: Movie metadata
            
        Returns:
            Path to created metadata file or None if failed
        """
        try:
            # Generate metadata file path
            metadata_path = video_path.with_suffix('.json')
            
            # Prepare metadata dictionary
            metadata_dict = {
                'file_info': {
                    'filename': video_path.name,
                    'organized_at': datetime.now().isoformat(),
                    'organizer_version': '1.0'
                },
                'metadata': metadata.to_dict()
            }
            
            # Write metadata file
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
            
            self.stats['metadata_files_created'] += 1
            self.logger.debug(f"Created metadata file: {metadata_path}")
            
            return metadata_path
            
        except Exception as e:
            self.logger.error(f"Error creating metadata file: {e}")
            return None
    
    def _create_result(self, success: bool, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create standardized result dictionary.
        
        Args:
            success: Whether operation was successful
            message: Result message
            details: Optional additional details
            
        Returns:
            Result dictionary
        """
        result = {
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            result['details'] = details
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get organization statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'files_processed': self.stats['files_processed'],
            'files_moved': self.stats['files_moved'],
            'files_copied': self.stats['files_copied'],
            'files_skipped': self.stats['files_skipped'],
            'conflicts_resolved': self.stats['conflicts_resolved'],
            'metadata_files_created': self.stats['metadata_files_created'],
            'errors': self.stats['errors'],
            'success_rate': (
                (self.stats['files_moved'] + self.stats['files_copied']) / 
                max(1, self.stats['files_processed'])
            ) * 100
        }
    
    def reset_statistics(self) -> None:
        """Reset organization statistics."""
        for key in self.stats:
            self.stats[key] = 0
        
        self.logger.info("Statistics reset")
    
    def validate_target_directory(self) -> Dict[str, Any]:
        """
        Validate target directory accessibility and permissions.
        
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        try:
            # Check if directory exists
            if not self.target_directory.exists():
                result['warnings'].append(f"Target directory does not exist: {self.target_directory}")
                
                # Try to create it
                try:
                    self.target_directory.mkdir(parents=True, exist_ok=True)
                    result['info']['created_directory'] = True
                except Exception as e:
                    result['errors'].append(f"Cannot create target directory: {e}")
                    result['valid'] = False
            
            # Check write permissions
            if self.target_directory.exists():
                test_file = self.target_directory / '.test_write_permission'
                try:
                    test_file.touch()
                    test_file.unlink()
                    result['info']['writable'] = True
                except Exception as e:
                    result['errors'].append(f"No write permission in target directory: {e}")
                    result['valid'] = False
            
            # Check available space (basic check)
            if self.target_directory.exists():
                try:
                    stat = os.statvfs(self.target_directory)
                    free_space = stat.f_bavail * stat.f_frsize
                    result['info']['free_space_bytes'] = free_space
                    result['info']['free_space_gb'] = free_space / (1024**3)
                    
                    if free_space < 1024**3:  # Less than 1GB
                        result['warnings'].append("Low disk space in target directory")
                        
                except Exception as e:
                    result['warnings'].append(f"Cannot check disk space: {e}")
            
        except Exception as e:
            result['errors'].append(f"Error validating target directory: {e}")
            result['valid'] = False
        
        return result
    
    def cleanup_empty_directories(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Clean up empty directories in target directory.
        
        Args:
            dry_run: If True, only report what would be deleted
            
        Returns:
            Cleanup result dictionary
        """
        result = {
            'empty_directories': [],
            'removed_directories': [],
            'errors': []
        }
        
        try:
            # Find empty directories
            for root, dirs, files in os.walk(self.target_directory, topdown=False):
                root_path = Path(root)
                
                # Skip target directory itself
                if root_path == self.target_directory:
                    continue
                
                # Check if directory is empty
                try:
                    if not any(root_path.iterdir()):
                        result['empty_directories'].append(str(root_path))
                        
                        if not dry_run:
                            root_path.rmdir()
                            result['removed_directories'].append(str(root_path))
                            self.logger.info(f"Removed empty directory: {root_path}")
                            
                except Exception as e:
                    result['errors'].append(f"Error processing directory {root_path}: {e}")
        
        except Exception as e:
            result['errors'].append(f"Error during cleanup: {e}")
        
        if dry_run:
            self.logger.info(f"Dry run: Found {len(result['empty_directories'])} empty directories")
        else:
            self.logger.info(f"Removed {len(result['removed_directories'])} empty directories")
        
        return result