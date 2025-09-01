"""Duplicate file detection and handling system."""

import hashlib
import asyncio
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .logging_config import get_logger
from ..models.video_file import VideoFile


class DuplicateStrategy(Enum):
    """Strategies for handling duplicate files."""
    SKIP = "skip"  # Skip processing duplicates
    KEEP_LARGER = "keep_larger"  # Keep the larger file
    KEEP_NEWER = "keep_newer"  # Keep the newer file
    KEEP_BOTH = "keep_both"  # Keep both files with different names
    INTERACTIVE = "interactive"  # Ask user for each duplicate


class HashAlgorithm(Enum):
    """Supported hash algorithms for file comparison."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    XXHASH = "xxhash"  # Fast hash for large files


@dataclass
class DuplicateGroup:
    """Group of duplicate files."""
    hash_value: str
    files: List[VideoFile] = field(default_factory=list)
    total_size: int = 0
    detection_time: datetime = field(default_factory=datetime.now)
    
    @property
    def file_count(self) -> int:
        """Number of files in this duplicate group."""
        return len(self.files)
    
    @property
    def wasted_space(self) -> int:
        """Bytes of wasted space (total size - largest file size)."""
        if not self.files:
            return 0
        largest_size = max(file.file_size for file in self.files)
        return self.total_size - largest_size
    
    def get_recommended_file(self, strategy: DuplicateStrategy) -> Optional[VideoFile]:
        """Get recommended file to keep based on strategy."""
        if not self.files:
            return None
        
        if strategy == DuplicateStrategy.KEEP_LARGER:
            return max(self.files, key=lambda f: f.file_size)
        elif strategy == DuplicateStrategy.KEEP_NEWER:
            return max(self.files, key=lambda f: f.modified_time or datetime.min)
        else:
            return self.files[0]  # Default to first file


@dataclass
class DuplicateReport:
    """Report of duplicate detection results."""
    total_files_scanned: int = 0
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    total_duplicates: int = 0
    total_wasted_space: int = 0
    scan_duration: float = 0.0
    
    @property
    def duplicate_percentage(self) -> float:
        """Percentage of files that are duplicates."""
        if self.total_files_scanned == 0:
            return 0.0
        return (self.total_duplicates / self.total_files_scanned) * 100
    
    @property
    def wasted_space_mb(self) -> float:
        """Wasted space in MB."""
        return self.total_wasted_space / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'total_files_scanned': self.total_files_scanned,
            'duplicate_groups': len(self.duplicate_groups),
            'total_duplicates': self.total_duplicates,
            'duplicate_percentage': self.duplicate_percentage,
            'total_wasted_space': self.total_wasted_space,
            'wasted_space_mb': self.wasted_space_mb,
            'scan_duration': self.scan_duration,
            'groups': [
                {
                    'hash': group.hash_value[:16] + "...",
                    'file_count': group.file_count,
                    'total_size': group.total_size,
                    'wasted_space': group.wasted_space,
                    'files': [f.filename for f in group.files]
                }
                for group in self.duplicate_groups
            ]
        }


class DuplicateDetector:
    """
    Advanced duplicate file detection system.
    
    Uses file hashing to identify duplicate files with various
    strategies for handling duplicates.
    """
    
    def __init__(
        self,
        hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        chunk_size: int = 8192,
        max_concurrent_hashing: int = 4,
        cache_hashes: bool = True,
        cache_file: Optional[Path] = None
    ):
        """
        Initialize duplicate detector.
        
        Args:
            hash_algorithm: Algorithm to use for file hashing
            chunk_size: Size of chunks for reading files
            max_concurrent_hashing: Maximum concurrent hash operations
            cache_hashes: Enable hash caching
            cache_file: File to store hash cache
        """
        self.hash_algorithm = hash_algorithm
        self.chunk_size = chunk_size
        self.max_concurrent_hashing = max_concurrent_hashing
        self.cache_hashes = cache_hashes
        self.cache_file = cache_file or Path("./cache/file_hashes.json")
        
        self.logger = get_logger(__name__)
        
        # Hash cache: file_path -> (mtime, size, hash)
        self.hash_cache: Dict[str, Tuple[float, int, str]] = {}
        
        # Semaphore for concurrent hashing
        self._hash_semaphore = asyncio.Semaphore(max_concurrent_hashing)
        
        # Load hash cache
        if self.cache_hashes:
            self._load_hash_cache()
        
        self.logger.info(f"Duplicate detector initialized with {hash_algorithm.value} hashing")
    
    async def detect_duplicates(
        self,
        files: List[VideoFile],
        progress_callback: Optional[callable] = None
    ) -> DuplicateReport:
        """
        Detect duplicate files in the given list.
        
        Args:
            files: List of video files to check
            progress_callback: Optional callback for progress updates
            
        Returns:
            DuplicateReport with detection results
        """
        start_time = datetime.now()
        self.logger.info(f"Starting duplicate detection for {len(files)} files")
        
        # Group files by size first (quick pre-filter)
        size_groups = self._group_by_size(files)
        
        # Only hash files that have potential duplicates (same size)
        files_to_hash = []
        for size, file_list in size_groups.items():
            if len(file_list) > 1:
                files_to_hash.extend(file_list)
        
        self.logger.info(f"Found {len(files_to_hash)} files with potential duplicates")
        
        # Calculate hashes for potential duplicates
        hash_map = await self._calculate_hashes(files_to_hash, progress_callback)
        
        # Group files by hash
        duplicate_groups = self._group_by_hash(hash_map)
        
        # Calculate statistics
        total_duplicates = sum(len(group.files) - 1 for group in duplicate_groups)
        total_wasted_space = sum(group.wasted_space for group in duplicate_groups)
        
        # Save hash cache
        if self.cache_hashes:
            self._save_hash_cache()
        
        scan_duration = (datetime.now() - start_time).total_seconds()
        
        report = DuplicateReport(
            total_files_scanned=len(files),
            duplicate_groups=duplicate_groups,
            total_duplicates=total_duplicates,
            total_wasted_space=total_wasted_space,
            scan_duration=scan_duration
        )
        
        self.logger.info(
            f"Duplicate detection completed: {len(duplicate_groups)} groups, "
            f"{total_duplicates} duplicates, {report.wasted_space_mb:.1f}MB wasted"
        )
        
        return report
    
    def _group_by_size(self, files: List[VideoFile]) -> Dict[int, List[VideoFile]]:
        """Group files by size for initial filtering."""
        size_groups: Dict[int, List[VideoFile]] = {}
        
        for file in files:
            if file.file_size not in size_groups:
                size_groups[file.file_size] = []
            size_groups[file.file_size].append(file)
        
        return size_groups
    
    async def _calculate_hashes(
        self,
        files: List[VideoFile],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, VideoFile]:
        """Calculate hashes for files with progress tracking."""
        hash_map: Dict[str, VideoFile] = {}
        
        # Create tasks for concurrent hashing
        tasks = []
        for i, file in enumerate(files):
            task = asyncio.create_task(
                self._hash_file_with_semaphore(file),
                name=f"hash_{i}"
            )
            tasks.append((task, file))
        
        # Process completed tasks
        completed = 0
        for task, file in tasks:
            try:
                file_hash = await task
                if file_hash:
                    hash_map[file_hash] = file
                
                completed += 1
                
                # Call progress callback
                if progress_callback:
                    progress_callback(completed, len(files))
                    
            except Exception as e:
                self.logger.error(f"Failed to hash {file.filename}: {e}")
        
        return hash_map
    
    async def _hash_file_with_semaphore(self, file: VideoFile) -> Optional[str]:
        """Hash file with semaphore for concurrency control."""
        async with self._hash_semaphore:
            return await self._hash_file(file)
    
    async def _hash_file(self, file: VideoFile) -> Optional[str]:
        """Calculate hash for a single file."""
        try:
            file_path = Path(file.file_path)
            
            # Check cache first
            if self.cache_hashes and self._is_hash_cached(file):
                cached_hash = self._get_cached_hash(file)
                if cached_hash:
                    return cached_hash
            
            # Calculate hash
            file_hash = await asyncio.to_thread(self._calculate_file_hash, file_path)
            
            # Cache the result
            if self.cache_hashes and file_hash:
                self._cache_hash(file, file_hash)
            
            return file_hash
            
        except Exception as e:
            self.logger.error(f"Error hashing file {file.filename}: {e}")
            return None
    
    def _calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate file hash using specified algorithm."""
        try:
            # Choose hash algorithm
            if self.hash_algorithm == HashAlgorithm.MD5:
                hasher = hashlib.md5()
            elif self.hash_algorithm == HashAlgorithm.SHA1:
                hasher = hashlib.sha1()
            elif self.hash_algorithm == HashAlgorithm.SHA256:
                hasher = hashlib.sha256()
            elif self.hash_algorithm == HashAlgorithm.XXHASH:
                try:
                    import xxhash
                    hasher = xxhash.xxh64()
                except ImportError:
                    self.logger.warning("xxhash not available, falling back to SHA256")
                    hasher = hashlib.sha256()
            else:
                hasher = hashlib.sha256()
            
            # Read file in chunks and update hash
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.chunk_size):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return None
    
    def _is_hash_cached(self, file: VideoFile) -> bool:
        """Check if file hash is cached and still valid."""
        if not self.cache_hashes or file.file_path not in self.hash_cache:
            return False
        
        cached_mtime, cached_size, _ = self.hash_cache[file.file_path]
        
        # Check if file has been modified
        file_path = Path(file.file_path)
        if not file_path.exists():
            return False
        
        current_mtime = file_path.stat().st_mtime
        current_size = file_path.stat().st_size
        
        return (cached_mtime == current_mtime and cached_size == current_size)
    
    def _get_cached_hash(self, file: VideoFile) -> Optional[str]:
        """Get cached hash for file."""
        if file.file_path in self.hash_cache:
            _, _, cached_hash = self.hash_cache[file.file_path]
            return cached_hash
        return None
    
    def _cache_hash(self, file: VideoFile, file_hash: str) -> None:
        """Cache hash for file."""
        try:
            file_path = Path(file.file_path)
            stat = file_path.stat()
            self.hash_cache[file.file_path] = (stat.st_mtime, stat.st_size, file_hash)
        except Exception as e:
            self.logger.warning(f"Failed to cache hash for {file.filename}: {e}")
    
    def _group_by_hash(self, hash_map: Dict[str, VideoFile]) -> List[DuplicateGroup]:
        """Group files by hash value to identify duplicates."""
        hash_groups: Dict[str, List[VideoFile]] = {}
        
        # Invert hash_map to group by hash
        for file_hash, file in hash_map.items():
            if file_hash not in hash_groups:
                hash_groups[file_hash] = []
            hash_groups[file_hash].append(file)
        
        # Create duplicate groups (only groups with multiple files)
        duplicate_groups = []
        for file_hash, files in hash_groups.items():
            if len(files) > 1:
                total_size = sum(file.file_size for file in files)
                group = DuplicateGroup(
                    hash_value=file_hash,
                    files=files,
                    total_size=total_size
                )
                duplicate_groups.append(group)
        
        # Sort by wasted space (descending)
        duplicate_groups.sort(key=lambda g: g.wasted_space, reverse=True)
        
        return duplicate_groups
    
    def _load_hash_cache(self) -> None:
        """Load hash cache from file."""
        try:
            if self.cache_file.exists():
                import json
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Convert to internal format
                for file_path, (mtime, size, file_hash) in cache_data.items():
                    self.hash_cache[file_path] = (mtime, size, file_hash)
                
                self.logger.debug(f"Loaded {len(self.hash_cache)} cached hashes")
        except Exception as e:
            self.logger.warning(f"Failed to load hash cache: {e}")
    
    def _save_hash_cache(self) -> None:
        """Save hash cache to file."""
        try:
            # Ensure cache directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(self.cache_file, 'w') as f:
                json.dump(self.hash_cache, f, indent=2)
            
            self.logger.debug(f"Saved {len(self.hash_cache)} cached hashes")
        except Exception as e:
            self.logger.warning(f"Failed to save hash cache: {e}")
    
    async def handle_duplicates(
        self,
        duplicate_groups: List[DuplicateGroup],
        strategy: DuplicateStrategy,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Handle duplicate files according to specified strategy.
        
        Args:
            duplicate_groups: Groups of duplicate files
            strategy: Strategy for handling duplicates
            dry_run: If True, only simulate actions without actual changes
            
        Returns:
            Dictionary with action results
        """
        results = {
            'files_processed': 0,
            'files_deleted': 0,
            'files_renamed': 0,
            'space_freed': 0,
            'actions': [],
            'errors': []
        }
        
        for group in duplicate_groups:
            try:
                action_result = await self._handle_duplicate_group(group, strategy, dry_run)
                
                results['files_processed'] += len(group.files)
                results['files_deleted'] += action_result.get('deleted', 0)
                results['files_renamed'] += action_result.get('renamed', 0)
                results['space_freed'] += action_result.get('space_freed', 0)
                results['actions'].extend(action_result.get('actions', []))
                
            except Exception as e:
                error_msg = f"Error handling duplicate group {group.hash_value[:8]}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    async def _handle_duplicate_group(
        self,
        group: DuplicateGroup,
        strategy: DuplicateStrategy,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Handle a single duplicate group."""
        result = {
            'deleted': 0,
            'renamed': 0,
            'space_freed': 0,
            'actions': []
        }
        
        if strategy == DuplicateStrategy.SKIP:
            result['actions'].append(f"Skipped {len(group.files)} duplicate files")
            return result
        
        # Get recommended file to keep
        keep_file = group.get_recommended_file(strategy)
        if not keep_file:
            return result
        
        # Process other files in group
        for file in group.files:
            if file == keep_file:
                continue
            
            if strategy == DuplicateStrategy.KEEP_BOTH:
                # Rename duplicate file
                new_name = self._generate_unique_name(file)
                action = f"Rename {file.filename} to {new_name}"
                
                if not dry_run:
                    # Implement actual renaming logic here
                    pass
                
                result['renamed'] += 1
                result['actions'].append(action)
                
            else:
                # Delete duplicate file
                action = f"Delete {file.filename} (keeping {keep_file.filename})"
                
                if not dry_run:
                    # Implement actual deletion logic here
                    pass
                
                result['deleted'] += 1
                result['space_freed'] += file.file_size
                result['actions'].append(action)
        
        return result
    
    def _generate_unique_name(self, file: VideoFile) -> str:
        """Generate unique name for duplicate file."""
        file_path = Path(file.file_path)
        base_name = file_path.stem
        extension = file_path.suffix
        
        counter = 1
        while True:
            new_name = f"{base_name}_duplicate_{counter}{extension}"
            new_path = file_path.parent / new_name
            
            if not new_path.exists():
                return new_name
            
            counter += 1
    
    def clear_cache(self) -> None:
        """Clear hash cache."""
        self.hash_cache.clear()
        
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
                self.logger.info("Hash cache cleared")
            except Exception as e:
                self.logger.error(f"Failed to delete cache file: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_files': len(self.hash_cache),
            'cache_file_exists': self.cache_file.exists() if self.cache_file else False,
            'cache_file_size': self.cache_file.stat().st_size if self.cache_file and self.cache_file.exists() else 0
        }


# Global duplicate detector instance
_global_duplicate_detector: Optional[DuplicateDetector] = None


def get_duplicate_detector() -> DuplicateDetector:
    """
    Get global duplicate detector instance.
    
    Returns:
        Global DuplicateDetector instance
    """
    global _global_duplicate_detector
    
    if _global_duplicate_detector is None:
        _global_duplicate_detector = DuplicateDetector()
    
    return _global_duplicate_detector