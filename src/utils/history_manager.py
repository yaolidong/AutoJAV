"""Scraping history manager for tracking processed files."""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from threading import Lock

from ..models.scrape_history import ScrapeHistoryEntry, ProcessStatus


class HistoryManager:
    """Manages scraping history with persistence."""
    
    def __init__(self, history_file: Optional[str] = None):
        """
        Initialize history manager.
        
        Args:
            history_file: Path to history JSON file
        """
        self.logger = logging.getLogger(__name__)
        
        # Default history file location
        if history_file is None:
            history_file = "/app/logs/scrape_history.json"
        
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-safe access
        self.lock = Lock()
        
        # Load existing history
        self.history: List[ScrapeHistoryEntry] = []
        self.load_history()
        
        # Statistics cache
        self._stats_cache = None
        self._stats_cache_time = None
        self._stats_cache_duration = 60  # seconds
    
    def load_history(self) -> None:
        """Load history from file."""
        with self.lock:
            if self.history_file.exists():
                try:
                    with open(self.history_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    self.history = []
                    for entry_data in data.get('entries', []):
                        try:
                            entry = ScrapeHistoryEntry.from_dict(entry_data)
                            self.history.append(entry)
                        except Exception as e:
                            self.logger.warning(f"Failed to load history entry: {e}")
                    
                    self.logger.info(f"Loaded {len(self.history)} history entries")
                except Exception as e:
                    self.logger.error(f"Error loading history: {e}")
                    self.history = []
            else:
                self.logger.info("No existing history file found")
                self.history = []
    
    def save_history(self) -> None:
        """Save history to file."""
        with self.lock:
            try:
                # Prepare data for saving
                data = {
                    'version': '1.0',
                    'last_updated': datetime.now().isoformat(),
                    'total_entries': len(self.history),
                    'entries': [entry.to_dict() for entry in self.history]
                }
                
                # Write to temporary file first
                temp_file = self.history_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # Rename to actual file
                temp_file.replace(self.history_file)
                
                self.logger.debug(f"Saved {len(self.history)} history entries")
            except Exception as e:
                self.logger.error(f"Error saving history: {e}")
    
    def add_entry(self, entry: ScrapeHistoryEntry) -> None:
        """
        Add a new history entry.
        
        Args:
            entry: History entry to add
        """
        with self.lock:
            self.history.append(entry)
            # Clear stats cache
            self._stats_cache = None
        
        # Save immediately for persistence
        self.save_history()
        
        self.logger.info(f"Added history entry for {entry.original_filename}")
    
    def record_success(
        self,
        original_filename: str,
        original_path: str,
        file_size: int,
        file_extension: str,
        detected_code: Optional[str],
        new_filename: str,
        new_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        scraper_used: Optional[str] = None,
        scraping_time: Optional[float] = None
    ) -> ScrapeHistoryEntry:
        """
        Record a successful processing.
        
        Returns:
            Created history entry
        """
        entry = ScrapeHistoryEntry(
            original_filename=original_filename,
            original_path=original_path,
            file_size=file_size,
            file_extension=file_extension,
            detected_code=detected_code,
            process_time=datetime.now(),
            status=ProcessStatus.SUCCESS,
            new_filename=new_filename,
            new_path=new_path,
            organized_path=new_path,
            metadata_found=bool(metadata),
            scraper_used=scraper_used,
            scraping_time=scraping_time
        )
        
        # Extract metadata if provided
        if metadata:
            entry.title = metadata.get('title')
            entry.actresses = metadata.get('actresses', [])
            entry.studio = metadata.get('studio')
            entry.release_date = metadata.get('release_date')
            entry.genres = metadata.get('genres', [])
            entry.cover_downloaded = metadata.get('cover_downloaded', False)
            entry.metadata_json = metadata
        
        self.add_entry(entry)
        return entry
    
    def record_failure(
        self,
        original_filename: str,
        original_path: str,
        file_size: int,
        file_extension: str,
        detected_code: Optional[str],
        error_message: str,
        error_details: Optional[str] = None
    ) -> ScrapeHistoryEntry:
        """
        Record a failed processing.
        
        Returns:
            Created history entry
        """
        entry = ScrapeHistoryEntry(
            original_filename=original_filename,
            original_path=original_path,
            file_size=file_size,
            file_extension=file_extension,
            detected_code=detected_code,
            process_time=datetime.now(),
            status=ProcessStatus.FAILED,
            error_message=error_message,
            error_details=error_details
        )
        
        self.add_entry(entry)
        return entry
    
    def get_recent_entries(self, limit: int = 100) -> List[ScrapeHistoryEntry]:
        """
        Get recent history entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of recent entries
        """
        with self.lock:
            # Return most recent entries first
            return list(reversed(self.history[-limit:]))
    
    def get_entries_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ScrapeHistoryEntry]:
        """
        Get entries within a date range.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            
        Returns:
            List of entries within range
        """
        if start_date is None:
            start_date = datetime.min
        if end_date is None:
            end_date = datetime.max
        
        with self.lock:
            return [
                entry for entry in self.history
                if start_date <= entry.process_time <= end_date
            ]
    
    def get_entries_by_status(self, status: ProcessStatus) -> List[ScrapeHistoryEntry]:
        """
        Get entries by processing status.
        
        Args:
            status: Processing status to filter by
            
        Returns:
            List of entries with given status
        """
        with self.lock:
            return [entry for entry in self.history if entry.status == status]
    
    def get_entries_by_code(self, code: str) -> List[ScrapeHistoryEntry]:
        """
        Get entries by detected code.
        
        Args:
            code: Code to search for
            
        Returns:
            List of entries with given code
        """
        with self.lock:
            return [
                entry for entry in self.history
                if entry.detected_code and entry.detected_code.upper() == code.upper()
            ]
    
    def search_entries(self, query: str) -> List[ScrapeHistoryEntry]:
        """
        Search entries by filename or metadata.
        
        Args:
            query: Search query
            
        Returns:
            List of matching entries
        """
        query_lower = query.lower()
        
        with self.lock:
            results = []
            for entry in self.history:
                # Search in various fields
                if (query_lower in entry.original_filename.lower() or
                    (entry.new_filename and query_lower in entry.new_filename.lower()) or
                    (entry.detected_code and query_lower in entry.detected_code.lower()) or
                    (entry.title and query_lower in entry.title.lower()) or
                    any(query_lower in actress.lower() for actress in entry.actresses)):
                    results.append(entry)
            
            return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with statistics
        """
        # Check cache
        if self._stats_cache and self._stats_cache_time:
            if (datetime.now() - self._stats_cache_time).seconds < self._stats_cache_duration:
                return self._stats_cache
        
        with self.lock:
            total = len(self.history)
            successful = sum(1 for e in self.history if e.status == ProcessStatus.SUCCESS)
            failed = sum(1 for e in self.history if e.status == ProcessStatus.FAILED)
            partial = sum(1 for e in self.history if e.status == ProcessStatus.PARTIAL)
            skipped = sum(1 for e in self.history if e.status == ProcessStatus.SKIPPED)
            
            # Calculate size statistics
            total_size = sum(e.file_size for e in self.history)
            organized_size = sum(
                e.file_size for e in self.history
                if e.status == ProcessStatus.SUCCESS
            )
            
            # Calculate metadata statistics
            with_metadata = sum(1 for e in self.history if e.metadata_found)
            with_cover = sum(1 for e in self.history if e.cover_downloaded)
            
            # Get unique actresses
            all_actresses = set()
            for entry in self.history:
                all_actresses.update(entry.actresses)
            
            # Get unique studios
            all_studios = set()
            for entry in self.history:
                if entry.studio:
                    all_studios.add(entry.studio)
            
            # Calculate average processing time
            processing_times = [
                e.scraping_time for e in self.history
                if e.scraping_time is not None
            ]
            avg_processing_time = (
                sum(processing_times) / len(processing_times)
                if processing_times else 0
            )
            
            # Get recent activity
            now = datetime.now()
            last_24h = sum(
                1 for e in self.history
                if (now - e.process_time).days < 1
            )
            last_7d = sum(
                1 for e in self.history
                if (now - e.process_time).days < 7
            )
            last_30d = sum(
                1 for e in self.history
                if (now - e.process_time).days < 30
            )
            
            stats = {
                'total_processed': total,
                'successful': successful,
                'failed': failed,
                'partial': partial,
                'skipped': skipped,
                'success_rate': (successful / total * 100) if total > 0 else 0,
                'total_size_mb': total_size / (1024 * 1024),
                'organized_size_mb': organized_size / (1024 * 1024),
                'with_metadata': with_metadata,
                'with_cover': with_cover,
                'unique_actresses': len(all_actresses),
                'unique_studios': len(all_studios),
                'avg_processing_time': avg_processing_time,
                'last_24h': last_24h,
                'last_7d': last_7d,
                'last_30d': last_30d,
                'last_update': datetime.now().isoformat()
            }
            
            # Update cache
            self._stats_cache = stats
            self._stats_cache_time = datetime.now()
            
            return stats
    
    def clear_old_entries(self, days: int = 90) -> int:
        """
        Clear entries older than specified days, or all entries if days=0.
        
        Args:
            days: Number of days to keep (0 to clear all)
            
        Returns:
            Number of entries removed
        """
        with self.lock:
            original_count = len(self.history)
            
            if days == 0:
                # Clear all entries
                self.history = []
                removed = original_count
                # Clear stats cache when clearing all entries
                self._stats_cache = None
                self._stats_cache_time = None
            else:
                # Clear entries older than specified days
                cutoff_date = datetime.now() - timedelta(days=days)
                self.history = [
                    entry for entry in self.history
                    if entry.process_time >= cutoff_date
                ]
                removed = original_count - len(self.history)
                # Clear stats cache when removing entries
                if removed > 0:
                    self._stats_cache = None
                    self._stats_cache_time = None
        
        if removed > 0:
            self.save_history()
            if days == 0:
                self.logger.info(f"Cleared all {removed} history entries")
            else:
                self.logger.info(f"Removed {removed} old history entries")
        
        return removed
    
    def export_to_csv(self, output_file: str) -> None:
        """
        Export history to CSV file.
        
        Args:
            output_file: Path to output CSV file
        """
        import csv
        
        with self.lock:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                if not self.history:
                    return
                
                # Get all field names from first entry
                fieldnames = [
                    'process_time', 'status', 'original_filename', 'original_path',
                    'file_size_mb', 'detected_code', 'new_filename', 'new_path',
                    'title', 'actresses', 'studio', 'release_date', 'genres',
                    'scraper_used', 'scraping_time', 'error_message'
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for entry in self.history:
                    row = {
                        'process_time': entry.process_time.isoformat(),
                        'status': entry.status.value,
                        'original_filename': entry.original_filename,
                        'original_path': entry.original_path,
                        'file_size_mb': f"{entry.file_size_mb:.2f}",
                        'detected_code': entry.detected_code or '',
                        'new_filename': entry.new_filename or '',
                        'new_path': entry.new_path or '',
                        'title': entry.title or '',
                        'actresses': ', '.join(entry.actresses),
                        'studio': entry.studio or '',
                        'release_date': entry.release_date or '',
                        'genres': ', '.join(entry.genres),
                        'scraper_used': entry.scraper_used or '',
                        'scraping_time': f"{entry.scraping_time:.2f}" if entry.scraping_time else '',
                        'error_message': entry.error_message or ''
                    }
                    writer.writerow(row)
        
        self.logger.info(f"Exported {len(self.history)} entries to {output_file}")