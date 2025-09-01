"""Progress persistence and recovery system."""

import json
import pickle
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum

from .logging_config import get_logger
from .progress_tracker import ProgressTracker, TaskProgress, TaskStatus
from ..models.video_file import VideoFile
from ..models.movie_metadata import MovieMetadata


class PersistenceFormat(Enum):
    """Supported persistence formats."""
    JSON = "json"
    PICKLE = "pickle"


@dataclass
class ProcessingSession:
    """Represents a processing session that can be saved and restored."""
    session_id: str
    start_time: datetime
    last_update: datetime
    total_files: int
    processed_files: Set[str] = field(default_factory=set)
    failed_files: Set[str] = field(default_factory=set)
    skipped_files: Set[str] = field(default_factory=set)
    pending_files: List[str] = field(default_factory=list)
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'last_update': self.last_update.isoformat(),
            'total_files': self.total_files,
            'processed_files': list(self.processed_files),
            'failed_files': list(self.failed_files),
            'skipped_files': list(self.skipped_files),
            'pending_files': self.pending_files,
            'session_metadata': self.session_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingSession':
        """Create from dictionary."""
        return cls(
            session_id=data['session_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            last_update=datetime.fromisoformat(data['last_update']),
            total_files=data['total_files'],
            processed_files=set(data['processed_files']),
            failed_files=set(data['failed_files']),
            skipped_files=set(data['skipped_files']),
            pending_files=data['pending_files'],
            session_metadata=data['session_metadata']
        )


class ProgressPersistence:
    """
    System for persisting and recovering processing progress.
    
    Allows resuming interrupted processing sessions and maintaining
    state across application restarts.
    """
    
    def __init__(
        self,
        persistence_dir: Path = Path("./progress"),
        format: PersistenceFormat = PersistenceFormat.JSON,
        auto_save_interval: float = 30.0,
        max_sessions: int = 10
    ):
        """
        Initialize progress persistence system.
        
        Args:
            persistence_dir: Directory to store progress files
            format: Persistence format (JSON or pickle)
            auto_save_interval: Automatic save interval in seconds
            max_sessions: Maximum number of sessions to keep
        """
        self.persistence_dir = Path(persistence_dir)
        self.format = format
        self.auto_save_interval = auto_save_interval
        self.max_sessions = max_sessions
        
        self.logger = get_logger(__name__)
        
        # Current session
        self.current_session: Optional[ProcessingSession] = None
        
        # Auto-save task
        self._auto_save_task: Optional[asyncio.Task] = None
        self._stop_auto_save = asyncio.Event()
        
        # Ensure persistence directory exists
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Progress persistence initialized: {self.persistence_dir}")
    
    def start_session(
        self,
        session_id: Optional[str] = None,
        total_files: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingSession:
        """
        Start a new processing session.
        
        Args:
            session_id: Unique session identifier (auto-generated if None)
            total_files: Total number of files to process
            metadata: Additional session metadata
            
        Returns:
            New ProcessingSession object
        """
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = ProcessingSession(
            session_id=session_id,
            start_time=datetime.now(),
            last_update=datetime.now(),
            total_files=total_files,
            session_metadata=metadata or {}
        )
        
        # Save initial session
        self.save_session()
        
        # Start auto-save
        self.start_auto_save()
        
        self.logger.info(f"Started processing session: {session_id}")
        return self.current_session
    
    def update_session(
        self,
        processed_file: Optional[str] = None,
        failed_file: Optional[str] = None,
        skipped_file: Optional[str] = None,
        pending_files: Optional[List[str]] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update current session progress.
        
        Args:
            processed_file: File that was successfully processed
            failed_file: File that failed processing
            skipped_file: File that was skipped
            pending_files: List of pending files to process
            metadata_update: Metadata updates
        """
        if not self.current_session:
            self.logger.warning("No active session to update")
            return
        
        # Update file sets
        if processed_file:
            self.current_session.processed_files.add(processed_file)
            # Remove from pending if it was there
            if processed_file in self.current_session.pending_files:
                self.current_session.pending_files.remove(processed_file)
        
        if failed_file:
            self.current_session.failed_files.add(failed_file)
            if failed_file in self.current_session.pending_files:
                self.current_session.pending_files.remove(failed_file)
        
        if skipped_file:
            self.current_session.skipped_files.add(skipped_file)
            if skipped_file in self.current_session.pending_files:
                self.current_session.pending_files.remove(skipped_file)
        
        if pending_files is not None:
            self.current_session.pending_files = pending_files
        
        # Update metadata
        if metadata_update:
            self.current_session.session_metadata.update(metadata_update)
        
        # Update timestamp
        self.current_session.last_update = datetime.now()
    
    def save_session(self, session: Optional[ProcessingSession] = None) -> bool:
        """
        Save session to disk.
        
        Args:
            session: Session to save (current session if None)
            
        Returns:
            True if saved successfully
        """
        if session is None:
            session = self.current_session
        
        if not session:
            self.logger.warning("No session to save")
            return False
        
        try:
            session_file = self.persistence_dir / f"{session.session_id}.{self.format.value}"
            
            if self.format == PersistenceFormat.JSON:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            else:  # PICKLE
                with open(session_file, 'wb') as f:
                    pickle.dump(session, f)
            
            self.logger.debug(f"Saved session: {session.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save session {session.session_id}: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[ProcessingSession]:
        """
        Load session from disk.
        
        Args:
            session_id: Session identifier to load
            
        Returns:
            Loaded ProcessingSession or None if not found
        """
        try:
            session_file = self.persistence_dir / f"{session_id}.{self.format.value}"
            
            if not session_file.exists():
                self.logger.warning(f"Session file not found: {session_file}")
                return None
            
            if self.format == PersistenceFormat.JSON:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                session = ProcessingSession.from_dict(data)
            else:  # PICKLE
                with open(session_file, 'rb') as f:
                    session = pickle.load(f)
            
            self.logger.info(f"Loaded session: {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def resume_session(self, session_id: str) -> Optional[ProcessingSession]:
        """
        Resume a previous processing session.
        
        Args:
            session_id: Session identifier to resume
            
        Returns:
            Resumed ProcessingSession or None if not found
        """
        session = self.load_session(session_id)
        
        if session:
            self.current_session = session
            self.start_auto_save()
            self.logger.info(f"Resumed session: {session_id}")
        
        return session
    
    def list_sessions(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        List available sessions.
        
        Args:
            include_completed: Include completed sessions
            
        Returns:
            List of session information dictionaries
        """
        sessions = []
        
        try:
            pattern = f"*.{self.format.value}"
            for session_file in self.persistence_dir.glob(pattern):
                try:
                    session = self.load_session(session_file.stem)
                    if session:
                        # Check if session is completed
                        total_processed = (
                            len(session.processed_files) + 
                            len(session.failed_files) + 
                            len(session.skipped_files)
                        )
                        is_completed = total_processed >= session.total_files
                        
                        if include_completed or not is_completed:
                            sessions.append({
                                'session_id': session.session_id,
                                'start_time': session.start_time,
                                'last_update': session.last_update,
                                'total_files': session.total_files,
                                'processed_files': len(session.processed_files),
                                'failed_files': len(session.failed_files),
                                'skipped_files': len(session.skipped_files),
                                'pending_files': len(session.pending_files),
                                'is_completed': is_completed,
                                'progress_percentage': (total_processed / max(1, session.total_files)) * 100
                            })
                except Exception as e:
                    self.logger.warning(f"Failed to load session info from {session_file}: {e}")
            
            # Sort by last update time (most recent first)
            sessions.sort(key=lambda x: x['last_update'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session file.
        
        Args:
            session_id: Session identifier to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            session_file = self.persistence_dir / f"{session_id}.{self.format.value}"
            
            if session_file.exists():
                session_file.unlink()
                self.logger.info(f"Deleted session: {session_id}")
                return True
            else:
                self.logger.warning(f"Session file not found: {session_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """
        Clean up old session files.
        
        Args:
            max_age_days: Maximum age in days for session files
            
        Returns:
            Number of sessions deleted
        """
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        
        try:
            pattern = f"*.{self.format.value}"
            for session_file in self.persistence_dir.glob(pattern):
                try:
                    # Check file modification time
                    file_mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        session_file.unlink()
                        deleted_count += 1
                        self.logger.debug(f"Deleted old session: {session_file.stem}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to check/delete session {session_file}: {e}")
            
            # Also enforce max sessions limit
            sessions = self.list_sessions(include_completed=True)
            if len(sessions) > self.max_sessions:
                # Delete oldest sessions
                sessions_to_delete = sessions[self.max_sessions:]
                for session_info in sessions_to_delete:
                    if self.delete_session(session_info['session_id']):
                        deleted_count += 1
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old sessions")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old sessions: {e}")
        
        return deleted_count
    
    def get_session_progress(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed progress information for a session.
        
        Args:
            session_id: Session ID (current session if None)
            
        Returns:
            Progress information dictionary
        """
        session = self.current_session
        
        if session_id:
            session = self.load_session(session_id)
        
        if not session:
            return None
        
        total_processed = (
            len(session.processed_files) + 
            len(session.failed_files) + 
            len(session.skipped_files)
        )
        
        progress_percentage = (total_processed / max(1, session.total_files)) * 100
        
        # Calculate processing rate
        elapsed_time = (session.last_update - session.start_time).total_seconds()
        processing_rate = len(session.processed_files) / max(1, elapsed_time / 3600)  # files per hour
        
        # Estimate remaining time
        remaining_files = len(session.pending_files)
        estimated_remaining_hours = remaining_files / max(0.1, processing_rate)
        
        return {
            'session_id': session.session_id,
            'start_time': session.start_time,
            'last_update': session.last_update,
            'elapsed_time_seconds': elapsed_time,
            'total_files': session.total_files,
            'processed_files': len(session.processed_files),
            'failed_files': len(session.failed_files),
            'skipped_files': len(session.skipped_files),
            'pending_files': remaining_files,
            'progress_percentage': progress_percentage,
            'processing_rate_per_hour': processing_rate,
            'estimated_remaining_hours': estimated_remaining_hours,
            'is_completed': total_processed >= session.total_files,
            'session_metadata': session.session_metadata
        }
    
    def start_auto_save(self) -> None:
        """Start automatic session saving."""
        if self._auto_save_task and not self._auto_save_task.done():
            return
        
        try:
            # Only start auto-save if we're in an async context
            loop = asyncio.get_running_loop()
            self._stop_auto_save.clear()
            self._auto_save_task = asyncio.create_task(self._auto_save_loop())
            self.logger.debug("Started auto-save task")
        except RuntimeError:
            # No event loop running, skip auto-save
            self.logger.debug("No event loop running, skipping auto-save")
    
    def stop_auto_save(self) -> None:
        """Stop automatic session saving."""
        self._stop_auto_save.set()
        
        if self._auto_save_task and not self._auto_save_task.done():
            try:
                self._auto_save_task.cancel()
            except RuntimeError:
                # No event loop, task already stopped
                pass
        
        self.logger.debug("Stopped auto-save task")
    
    async def _auto_save_loop(self) -> None:
        """Auto-save loop task."""
        while not self._stop_auto_save.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_auto_save.wait(),
                    timeout=self.auto_save_interval
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                # Save current session
                if self.current_session:
                    self.save_session()
    
    def finalize_session(self) -> Optional[Dict[str, Any]]:
        """
        Finalize current session and return summary.
        
        Returns:
            Session summary dictionary
        """
        if not self.current_session:
            return None
        
        # Stop auto-save
        self.stop_auto_save()
        
        # Final save
        self.save_session()
        
        # Get final progress
        progress = self.get_session_progress()
        
        self.logger.info(f"Finalized session: {self.current_session.session_id}")
        self.current_session = None
        
        return progress


# Global progress persistence instance
_global_progress_persistence: Optional[ProgressPersistence] = None


def get_progress_persistence() -> ProgressPersistence:
    """
    Get global progress persistence instance.
    
    Returns:
        Global ProgressPersistence instance
    """
    global _global_progress_persistence
    
    if _global_progress_persistence is None:
        _global_progress_persistence = ProgressPersistence()
    
    return _global_progress_persistence