"""Tests for FileOrganizer."""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import date, datetime
from unittest.mock import Mock, patch, mock_open

from src.organizers.file_organizer import FileOrganizer, ConflictResolution
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata


class TestFileOrganizer:
    """Test cases for FileOrganizer."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def source_file(self, temp_dir):
        """Create a test source file."""
        source_path = Path(temp_dir) / "source" / "test_movie.mp4"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a test file with some content
        with open(source_path, 'wb') as f:
            f.write(b"test video content")
        
        return source_path
    
    @pytest.fixture
    def target_dir(self, temp_dir):
        """Create target directory for testing."""
        return Path(temp_dir) / "target"
    
    @pytest.fixture
    def video_file(self, source_file):
        """Create VideoFile instance."""
        return VideoFile(
            file_path=str(source_file),
            filename=source_file.name,
            file_size=len(b"test video content"),
            extension=".mp4",
            detected_code="SSIS-001"
        )
    
    @pytest.fixture
    def movie_metadata(self):
        """Create MovieMetadata instance."""
        return MovieMetadata(
            code="SSIS-001",
            title="Test Movie Title",
            actresses=["Test Actress", "Another Actress"],
            release_date=date(2021, 1, 15),
            studio="Test Studio",
            series="Test Series",
            genres=["Drama", "Romance"]
        )
    
    @pytest.fixture
    def organizer(self, target_dir):
        """Create FileOrganizer instance."""
        return FileOrganizer(
            target_directory=str(target_dir),
            safe_mode=True  # Use copy mode for testing
        )
    
    def test_init_default_params(self, target_dir):
        """Test FileOrganizer initialization with default parameters."""
        organizer = FileOrganizer(str(target_dir))
        
        assert organizer.target_directory == target_dir
        assert organizer.naming_pattern == "{actress}/{code}/{code}.{ext}"
        assert organizer.conflict_resolution == ConflictResolution.RENAME
        assert organizer.create_metadata_files is True
        assert organizer.verify_file_integrity is True
        assert organizer.safe_mode is True
    
    def test_init_custom_params(self, target_dir):
        """Test FileOrganizer initialization with custom parameters."""
        organizer = FileOrganizer(
            target_directory=str(target_dir),
            naming_pattern="{code}/{title}.{ext}",
            conflict_resolution=ConflictResolution.OVERWRITE,
            create_metadata_files=False,
            verify_file_integrity=False,
            safe_mode=False
        )
        
        assert organizer.naming_pattern == "{code}/{title}.{ext}"
        assert organizer.conflict_resolution == ConflictResolution.OVERWRITE
        assert organizer.create_metadata_files is False
        assert organizer.verify_file_integrity is False
        assert organizer.safe_mode is False
    
    def test_target_directory_creation(self, temp_dir):
        """Test that target directory is created if it doesn't exist."""
        target_dir = Path(temp_dir) / "new_target"
        assert not target_dir.exists()
        
        FileOrganizer(str(target_dir))
        
        assert target_dir.exists()
        assert target_dir.is_dir()
    
    def test_organize_file_success(self, organizer, video_file, movie_metadata):
        """Test successful file organization."""
        result = organizer.organize_file(video_file, movie_metadata)
        
        assert result['success'] is True
        assert 'File organized successfully' in result['message']
        assert 'details' in result
        
        details = result['details']
        assert details['original_path'] == video_file.file_path
        assert 'target_path' in details
        assert details['operation'] == 'copy'
        
        # Check that file was actually copied
        target_path = Path(details['target_path'])
        assert target_path.exists()
        assert target_path.read_bytes() == b"test video content"
    
    def test_organize_file_with_custom_pattern(self, organizer, video_file, movie_metadata):
        """Test file organization with custom naming pattern."""
        custom_pattern = "{studio}/{year}/{code}.{ext}"
        
        result = organizer.organize_file(video_file, movie_metadata, custom_pattern)
        
        assert result['success'] is True
        
        target_path = Path(result['details']['target_path'])
        expected_path = organizer.target_directory / "Test Studio" / "2021" / "SSIS-001.mp4"
        
        assert target_path == expected_path
        assert target_path.exists()
    
    def test_organize_file_creates_metadata_file(self, organizer, video_file, movie_metadata):
        """Test that metadata file is created alongside video file."""
        result = organizer.organize_file(video_file, movie_metadata)
        
        assert result['success'] is True
        
        metadata_file_path = Path(result['details']['metadata_file'])
        assert metadata_file_path.exists()
        assert metadata_file_path.suffix == '.json'
        
        # Check metadata file content
        with open(metadata_file_path, 'r', encoding='utf-8') as f:
            metadata_dict = json.load(f)
        
        assert 'file_info' in metadata_dict
        assert 'metadata' in metadata_dict
        assert metadata_dict['metadata']['code'] == "SSIS-001"
        assert metadata_dict['metadata']['title'] == "Test Movie Title"
    
    def test_organize_file_no_metadata_file(self, target_dir, video_file, movie_metadata):
        """Test file organization without creating metadata file."""
        organizer = FileOrganizer(
            str(target_dir),
            create_metadata_files=False,
            safe_mode=True
        )
        
        result = organizer.organize_file(video_file, movie_metadata)
        
        assert result['success'] is True
        assert result['details']['metadata_file'] is None
    
    def test_organize_file_move_mode(self, target_dir, video_file, movie_metadata):
        """Test file organization in move mode."""
        organizer = FileOrganizer(
            str(target_dir),
            safe_mode=False  # Move mode
        )
        
        original_path = Path(video_file.file_path)
        assert original_path.exists()
        
        result = organizer.organize_file(video_file, movie_metadata)
        
        assert result['success'] is True
        assert result['details']['operation'] == 'move'
        
        # Original file should no longer exist
        assert not original_path.exists()
        
        # Target file should exist
        target_path = Path(result['details']['target_path'])
        assert target_path.exists()
    
    def test_sanitize_filename(self, organizer):
        """Test filename sanitization."""
        test_cases = [
            ("Normal Name", "Normal Name"),
            ("Name/With\\Invalid:Chars", "Name_With_Invalid_Chars"),
            ("Name<>With|More?Invalid*Chars", "Name__With_More_Invalid_Chars"),
            ("  .Name with dots.  ", "Name with dots"),
            ("", "Unknown"),
            (None, "Unknown")
        ]
        
        for input_name, expected in test_cases:
            result = organizer._sanitize_filename(input_name)
            assert result == expected
    
    def test_get_primary_actress(self, organizer, movie_metadata):
        """Test primary actress extraction."""
        # Test with actresses
        result = organizer._get_primary_actress(movie_metadata)
        assert result == "Test Actress"
        
        # Test with no actresses
        metadata_no_actresses = MovieMetadata(code="TEST", title="Test")
        result = organizer._get_primary_actress(metadata_no_actresses)
        assert result == "Unknown"
    
    def test_get_actresses_string(self, organizer, movie_metadata):
        """Test actresses string formatting."""
        # Test with multiple actresses
        result = organizer._get_actresses_string(movie_metadata)
        assert result == "Test Actress, Another Actress"
        
        # Test with many actresses (should limit to 3)
        many_actresses_metadata = MovieMetadata(
            code="TEST",
            title="Test",
            actresses=["A1", "A2", "A3", "A4", "A5"]
        )
        result = organizer._get_actresses_string(many_actresses_metadata)
        assert "A1, A2, A3 (+2 more)" in result
        
        # Test with no actresses
        no_actresses_metadata = MovieMetadata(code="TEST", title="Test")
        result = organizer._get_actresses_string(no_actresses_metadata)
        assert result == "Unknown"
    
    def test_truncate_path_components(self, organizer):
        """Test path component truncation."""
        # Set short max length for testing
        organizer.max_filename_length = 10
        
        long_path = "very_long_directory_name/very_long_filename.mp4"
        result = organizer._truncate_path_components(long_path)
        
        parts = Path(result).parts
        for part in parts:
            assert len(part) <= 10
    
    def test_generate_target_path_default_pattern(self, organizer, video_file, movie_metadata):
        """Test target path generation with default pattern."""
        target_path = organizer._generate_target_path(video_file, movie_metadata, organizer.naming_pattern)
        
        expected_path = organizer.target_directory / "Test Actress" / "SSIS-001" / "SSIS-001.mp4"
        assert target_path == expected_path
    
    def test_generate_target_path_custom_pattern(self, organizer, video_file, movie_metadata):
        """Test target path generation with custom pattern."""
        pattern = "{studio}/{series}/{code}_{title}.{ext}"
        target_path = organizer._generate_target_path(video_file, movie_metadata, pattern)
        
        expected_path = organizer.target_directory / "Test Studio" / "Test Series" / "SSIS-001_Test Movie Title.mp4"
        assert target_path == expected_path
    
    def test_generate_target_path_with_date_variables(self, organizer, video_file, movie_metadata):
        """Test target path generation with date variables."""
        pattern = "{year}/{month}/{day}/{code}.{ext}"
        target_path = organizer._generate_target_path(video_file, movie_metadata, pattern)
        
        expected_path = organizer.target_directory / "2021" / "01" / "15" / "SSIS-001.mp4"
        assert target_path == expected_path
    
    def test_generate_target_path_no_date(self, organizer, video_file):
        """Test target path generation with no release date."""
        metadata_no_date = MovieMetadata(
            code="SSIS-001",
            title="Test Movie",
            actresses=["Test Actress"]
        )
        
        pattern = "{year}/{code}.{ext}"
        target_path = organizer._generate_target_path(video_file, metadata_no_date, pattern)
        
        expected_path = organizer.target_directory / "Unknown" / "SSIS-001.mp4"
        assert target_path == expected_path
    
    def test_generate_target_path_invalid_placeholder(self, organizer, video_file, movie_metadata):
        """Test target path generation with invalid placeholder."""
        pattern = "{invalid_placeholder}/{code}.{ext}"
        target_path = organizer._generate_target_path(video_file, movie_metadata, pattern)
        
        assert target_path is None
    
    def test_resolve_conflicts_no_conflict(self, organizer, target_dir):
        """Test conflict resolution when no conflict exists."""
        target_path = target_dir / "test.mp4"
        video_file = Mock()
        
        result = organizer._resolve_conflicts(target_path, video_file)
        
        assert result == target_path
    
    def test_resolve_conflicts_skip(self, organizer, target_dir):
        """Test conflict resolution with SKIP strategy."""
        organizer.conflict_resolution = ConflictResolution.SKIP
        
        # Create existing file
        target_path = target_dir / "test.mp4"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.touch()
        
        video_file = Mock()
        result = organizer._resolve_conflicts(target_path, video_file)
        
        assert result is None
    
    def test_resolve_conflicts_overwrite(self, organizer, target_dir):
        """Test conflict resolution with OVERWRITE strategy."""
        organizer.conflict_resolution = ConflictResolution.OVERWRITE
        
        # Create existing file
        target_path = target_dir / "test.mp4"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.touch()
        
        video_file = Mock()
        result = organizer._resolve_conflicts(target_path, video_file)
        
        assert result == target_path
    
    def test_resolve_conflicts_rename(self, organizer, target_dir):
        """Test conflict resolution with RENAME strategy."""
        organizer.conflict_resolution = ConflictResolution.RENAME
        
        # Create existing file
        target_path = target_dir / "test.mp4"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.touch()
        
        video_file = Mock()
        result = organizer._resolve_conflicts(target_path, video_file)
        
        assert result != target_path
        assert result.name == "test_1.mp4"
        assert result.parent == target_path.parent
    
    def test_generate_unique_path(self, organizer, target_dir):
        """Test unique path generation."""
        # Create existing files
        target_path = target_dir / "test.mp4"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.touch()
        
        (target_dir / "test_1.mp4").touch()
        (target_dir / "test_2.mp4").touch()
        
        result = organizer._generate_unique_path(target_path)
        
        assert result.name == "test_3.mp4"
        assert not result.exists()
    
    def test_organize_multiple_success(self, organizer, temp_dir):
        """Test organizing multiple files successfully."""
        # Create multiple source files
        source_files = []
        video_files = []
        metadatas = []
        
        for i in range(3):
            source_path = Path(temp_dir) / "source" / f"movie_{i}.mp4"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(f"content_{i}".encode())
            
            video_file = VideoFile(
                file_path=str(source_path),
                filename=source_path.name,
                file_size=len(f"content_{i}"),
                extension=".mp4",
                detected_code=f"SSIS-{i:03d}"
            )
            
            metadata = MovieMetadata(
                code=f"SSIS-{i:03d}",
                title=f"Movie {i}",
                actresses=[f"Actress {i}"]
            )
            
            source_files.append(source_path)
            video_files.append(video_file)
            metadatas.append(metadata)
        
        # Organize multiple files
        file_metadata_pairs = list(zip(video_files, metadatas))
        result = organizer.organize_multiple(file_metadata_pairs)
        
        assert result['total_files'] == 3
        assert result['successful'] == 3
        assert result['failed'] == 0
        assert len(result['results']) == 3
        
        # Check that all files were organized
        for i in range(3):
            assert result['results'][i]['result']['success'] is True
    
    def test_organize_multiple_mixed_results(self, organizer, temp_dir):
        """Test organizing multiple files with mixed success/failure."""
        # Create source files
        source_files = []
        video_files = []
        metadatas = []
        
        for i in range(2):
            source_path = Path(temp_dir) / "source" / f"movie_{i}.mp4"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(f"content_{i}".encode())
            
            video_file = VideoFile(
                file_path=str(source_path),
                filename=source_path.name,
                file_size=len(f"content_{i}"),
                extension=".mp4",
                detected_code=f"SSIS-{i:03d}"
            )
            
            metadata = MovieMetadata(
                code=f"SSIS-{i:03d}",
                title=f"Movie {i}",
                actresses=[f"Actress {i}"]
            )
            
            video_files.append(video_file)
            metadatas.append(metadata)
        
        # Make one file fail by using invalid path
        video_files[1].file_path = "/nonexistent/path.mp4"
        
        file_metadata_pairs = list(zip(video_files, metadatas))
        result = organizer.organize_multiple(file_metadata_pairs)
        
        assert result['total_files'] == 2
        assert result['successful'] == 1
        assert result['failed'] == 1
    
    def test_get_statistics(self, organizer):
        """Test statistics retrieval."""
        # Modify some statistics
        organizer.stats['files_processed'] = 10
        organizer.stats['files_moved'] = 8
        organizer.stats['files_copied'] = 0
        organizer.stats['files_skipped'] = 1
        organizer.stats['errors'] = 1
        
        stats = organizer.get_statistics()
        
        assert stats['files_processed'] == 10
        assert stats['files_moved'] == 8
        assert stats['files_copied'] == 0
        assert stats['files_skipped'] == 1
        assert stats['errors'] == 1
        assert stats['success_rate'] == 80.0  # 8/10 * 100
    
    def test_reset_statistics(self, organizer):
        """Test statistics reset."""
        # Set some statistics
        organizer.stats['files_processed'] = 5
        organizer.stats['errors'] = 2
        
        organizer.reset_statistics()
        
        assert organizer.stats['files_processed'] == 0
        assert organizer.stats['errors'] == 0
    
    def test_validate_target_directory_valid(self, organizer):
        """Test target directory validation when valid."""
        result = organizer.validate_target_directory()
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['info']['writable'] is True
    
    def test_validate_target_directory_nonexistent(self, temp_dir):
        """Test target directory validation when directory doesn't exist."""
        nonexistent_dir = Path(temp_dir) / "nonexistent"
        organizer = FileOrganizer(str(nonexistent_dir))
        
        result = organizer.validate_target_directory()
        
        assert result['valid'] is True  # Should create directory
        assert result['info']['created_directory'] is True
        assert nonexistent_dir.exists()
    
    @patch('os.statvfs')
    def test_validate_target_directory_low_space(self, mock_statvfs, organizer):
        """Test target directory validation with low disk space."""
        # Mock low disk space
        mock_stat = Mock()
        mock_stat.f_bavail = 100  # Very low
        mock_stat.f_frsize = 1024
        mock_statvfs.return_value = mock_stat
        
        result = organizer.validate_target_directory()
        
        assert result['valid'] is True
        assert any("Low disk space" in warning for warning in result['warnings'])
    
    def test_cleanup_empty_directories_dry_run(self, organizer, target_dir):
        """Test cleanup of empty directories in dry run mode."""
        # Create empty directories
        empty_dir1 = target_dir / "empty1"
        empty_dir2 = target_dir / "empty2" / "nested_empty"
        
        empty_dir1.mkdir(parents=True, exist_ok=True)
        empty_dir2.mkdir(parents=True, exist_ok=True)
        
        # Create non-empty directory
        non_empty_dir = target_dir / "non_empty"
        non_empty_dir.mkdir(parents=True, exist_ok=True)
        (non_empty_dir / "file.txt").touch()
        
        result = organizer.cleanup_empty_directories(dry_run=True)
        
        assert len(result['empty_directories']) >= 2
        assert len(result['removed_directories']) == 0
        
        # Directories should still exist
        assert empty_dir1.exists()
        assert empty_dir2.exists()
    
    def test_cleanup_empty_directories_actual(self, organizer, target_dir):
        """Test actual cleanup of empty directories."""
        # Create empty directories
        empty_dir1 = target_dir / "empty1"
        empty_dir2 = target_dir / "empty2"
        
        empty_dir1.mkdir(parents=True, exist_ok=True)
        empty_dir2.mkdir(parents=True, exist_ok=True)
        
        result = organizer.cleanup_empty_directories(dry_run=False)
        
        assert len(result['removed_directories']) >= 2
        
        # Directories should be removed
        assert not empty_dir1.exists()
        assert not empty_dir2.exists()
    
    @patch('shutil.copy2')
    def test_transfer_file_copy_failure(self, mock_copy, organizer):
        """Test file transfer failure in copy mode."""
        mock_copy.side_effect = Exception("Copy failed")
        
        source_path = Path("/source/file.mp4")
        target_path = Path("/target/file.mp4")
        
        result = organizer._transfer_file(source_path, target_path)
        
        assert result is False
    
    @patch('shutil.move')
    def test_transfer_file_move_failure(self, mock_move, target_dir):
        """Test file transfer failure in move mode."""
        organizer = FileOrganizer(str(target_dir), safe_mode=False)
        mock_move.side_effect = Exception("Move failed")
        
        source_path = Path("/source/file.mp4")
        target_path = Path("/target/file.mp4")
        
        result = organizer._transfer_file(source_path, target_path)
        
        assert result is False
    
    def test_calculate_file_hash(self, organizer, temp_dir):
        """Test file hash calculation."""
        test_file = Path(temp_dir) / "test.txt"
        test_content = b"test content for hashing"
        test_file.write_bytes(test_content)
        
        hash1 = organizer._calculate_file_hash(test_file)
        hash2 = organizer._calculate_file_hash(test_file)
        
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length
    
    def test_verify_file_integrity_success(self, organizer, temp_dir):
        """Test successful file integrity verification."""
        source_file = Path(temp_dir) / "source.txt"
        target_file = Path(temp_dir) / "target.txt"
        
        content = b"test content"
        source_file.write_bytes(content)
        target_file.write_bytes(content)
        
        result = organizer._verify_file_integrity(source_file, target_file)
        
        assert result is True
    
    def test_verify_file_integrity_failure(self, organizer, temp_dir):
        """Test failed file integrity verification."""
        source_file = Path(temp_dir) / "source.txt"
        target_file = Path(temp_dir) / "target.txt"
        
        source_file.write_bytes(b"original content")
        target_file.write_bytes(b"different content")
        
        result = organizer._verify_file_integrity(source_file, target_file)
        
        assert result is False
    
    def test_verify_file_integrity_source_missing(self, organizer, temp_dir):
        """Test file integrity verification when source is missing (moved)."""
        source_file = Path(temp_dir) / "nonexistent.txt"
        target_file = Path(temp_dir) / "target.txt"
        
        target_file.write_bytes(b"content")
        
        result = organizer._verify_file_integrity(source_file, target_file)
        
        assert result is True  # Should pass when source doesn't exist (moved)
    
    def test_create_result(self, organizer):
        """Test result dictionary creation."""
        result = organizer._create_result(True, "Success message", {"key": "value"})
        
        assert result['success'] is True
        assert result['message'] == "Success message"
        assert 'timestamp' in result
        assert result['details']['key'] == "value"
    
    def test_create_result_no_details(self, organizer):
        """Test result dictionary creation without details."""
        result = organizer._create_result(False, "Error message")
        
        assert result['success'] is False
        assert result['message'] == "Error message"
        assert 'timestamp' in result
        assert 'details' not in result


if __name__ == "__main__":
    pytest.main([__file__])