"""Tests for FileScanner."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.scanner.file_scanner import FileScanner
from src.models.video_file import VideoFile


class TestFileScanner:
    """Test cases for FileScanner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.supported_formats = ['.mp4', '.mkv', '.avi']
        
    def test_init(self):
        """Test FileScanner initialization."""
        scanner = FileScanner('/test/path', self.supported_formats)
        assert scanner.source_directory == Path('/test/path')
        assert scanner.supported_formats == ['.mp4', '.mkv', '.avi']
        assert len(scanner.compiled_patterns) > 0
    
    def test_is_video_file(self):
        """Test video file detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            video_file = Path(temp_dir) / "test.mp4"
            video_file.touch()
            
            text_file = Path(temp_dir) / "test.txt"
            text_file.touch()
            
            scanner = FileScanner(temp_dir, self.supported_formats)
            
            assert scanner.is_video_file(video_file) is True
            assert scanner.is_video_file(text_file) is False
    
    def test_extract_code_standard_format(self):
        """Test code extraction from standard format filenames."""
        scanner = FileScanner('/test', self.supported_formats)
        
        test_cases = [
            ("ABC-123.mp4", "ABC-123"),
            ("ABCD-1234.mkv", "ABCD-1234"),
            ("[Tag] DEF-456 [1080p].avi", "DEF-456"),
            ("GHI-789_HD.mp4", "GHI-789"),
            ("JKL.012.mp4", "JKL-012"),
            ("MNO_345.mkv", "MNO-345"),
        ]
        
        for filename, expected_code in test_cases:
            result = scanner.extract_code_from_filename(filename)
            assert result == expected_code, f"Failed for {filename}: expected {expected_code}, got {result}"
    
    def test_extract_code_special_formats(self):
        """Test code extraction from special format filenames."""
        scanner = FileScanner('/test', self.supported_formats)
        
        test_cases = [
            ("FC2-PPV-123456.mp4", "FC2-PPV-123456"),
            ("FC2-654321.mkv", "FC2-654321"),
            ("1PON-123456.mp4", "1PON-123456"),
            ("123456-789.avi", "123456-789"),
            ("n1234.mp4", "N1234"),
            ("4017-PPV123.mkv", "4017-PPV123"),
        ]
        
        for filename, expected_code in test_cases:
            result = scanner.extract_code_from_filename(filename)
            assert result == expected_code, f"Failed for {filename}: expected {expected_code}, got {result}"
    
    def test_extract_code_no_match(self):
        """Test code extraction when no code is found."""
        scanner = FileScanner('/test', self.supported_formats)
        
        test_cases = [
            "random_video.mp4",
            "movie.mkv",
            "123.avi",
            "abc.mp4",
            "no-code-here.mkv"
        ]
        
        for filename in test_cases:
            result = scanner.extract_code_from_filename(filename)
            assert result is None, f"Expected None for {filename}, got {result}"
    
    def test_clean_filename(self):
        """Test filename cleaning functionality."""
        scanner = FileScanner('/test', self.supported_formats)
        
        test_cases = [
            ("[Tag] ABC-123 [1080p]", "ABC-123"),
            ("(Studio) DEF-456 (HD)", "DEF-456"),
            ("【字幕】GHI-789【高清】", "GHI-789"),
            ("JKL_012_1080p", "JKL 012"),
            ("MNO-345_HD", "MNO-345"),
            ("PQR.678.FHD", "PQR 678"),
        ]
        
        for input_name, expected_output in test_cases:
            result = scanner._clean_filename(input_name)
            assert expected_output in result, f"Expected '{expected_output}' in cleaned '{result}' for input '{input_name}'"
    
    def test_should_skip_directory(self):
        """Test directory skipping logic."""
        scanner = FileScanner('/test', self.supported_formats)
        
        # Directories that should be skipped
        skip_dirs = [
            Path('.hidden'),
            Path('__pycache__'),
            Path('.git'),
            Path('tmp'),
            Path('$RECYCLE.BIN'),
        ]
        
        for dir_path in skip_dirs:
            assert scanner._should_skip_directory(dir_path) is True
        
        # Directories that should not be skipped
        normal_dirs = [
            Path('videos'),
            Path('movies'),
            Path('collection'),
        ]
        
        for dir_path in normal_dirs:
            assert scanner._should_skip_directory(dir_path) is False
    
    def test_scan_directory_success(self):
        """Test successful directory scanning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test video files
            video_files = [
                "ABC-123.mp4",
                "DEF-456.mkv",
                "GHI-789.avi",
                "random.txt"  # Non-video file
            ]
            
            for filename in video_files:
                (temp_path / filename).touch()
            
            # Create subdirectory with video
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "JKL-012.mp4").touch()
            
            scanner = FileScanner(str(temp_path), self.supported_formats)
            results = scanner.scan_directory()
            
            # Should find 4 video files (3 in root + 1 in subdir)
            assert len(results) == 4
            
            # Check that all results are VideoFile objects
            for result in results:
                assert isinstance(result, VideoFile)
                assert result.extension in self.supported_formats
            
            # Check that codes were detected
            codes = [vf.detected_code for vf in results if vf.detected_code]
            assert len(codes) >= 3  # At least ABC-123, DEF-456, GHI-789, JKL-012
    
    def test_scan_directory_not_found(self):
        """Test scanning non-existent directory."""
        scanner = FileScanner('/nonexistent/path', self.supported_formats)
        
        with pytest.raises(FileNotFoundError):
            scanner.scan_directory()
    
    def test_scan_directory_not_directory(self):
        """Test scanning a file instead of directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            scanner = FileScanner(temp_file.name, self.supported_formats)
            
            with pytest.raises(NotADirectoryError):
                scanner.scan_directory()
    
    def test_create_video_file(self):
        """Test VideoFile creation from file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "ABC-123.mp4"
            video_path.touch()
            
            scanner = FileScanner(temp_dir, self.supported_formats)
            video_file = scanner._create_video_file(video_path)
            
            assert video_file is not None
            assert isinstance(video_file, VideoFile)
            assert video_file.filename == "ABC-123.mp4"
            assert video_file.extension == ".mp4"
            assert video_file.detected_code == "ABC-123"
            assert video_file.file_size >= 0
            assert video_file.created_time is not None
            assert video_file.modified_time is not None
    
    def test_get_scan_statistics_empty(self):
        """Test statistics for empty file list."""
        scanner = FileScanner('/test', self.supported_formats)
        stats = scanner.get_scan_statistics([])
        
        assert stats['total_files'] == 0
        assert stats['total_size_mb'] == 0
        assert stats['files_with_codes'] == 0
        assert stats['files_without_codes'] == 0
        assert stats['extensions'] == {}
        assert stats['average_size_mb'] == 0
    
    def test_get_scan_statistics_with_files(self):
        """Test statistics for file list with data."""
        scanner = FileScanner('/test', self.supported_formats)
        
        # Create mock video files
        video_files = [
            VideoFile(
                file_path="/test/ABC-123.mp4",
                filename="ABC-123.mp4",
                file_size=1024 * 1024,  # 1MB
                extension=".mp4",
                detected_code="ABC-123"
            ),
            VideoFile(
                file_path="/test/DEF-456.mkv",
                filename="DEF-456.mkv",
                file_size=2 * 1024 * 1024,  # 2MB
                extension=".mkv",
                detected_code="DEF-456"
            ),
            VideoFile(
                file_path="/test/random.avi",
                filename="random.avi",
                file_size=512 * 1024,  # 0.5MB
                extension=".avi",
                detected_code=None
            )
        ]
        
        stats = scanner.get_scan_statistics(video_files)
        
        assert stats['total_files'] == 3
        assert stats['total_size_mb'] == 3.5
        assert stats['files_with_codes'] == 2
        assert stats['files_without_codes'] == 1
        assert stats['extensions'] == {'.mp4': 1, '.mkv': 1, '.avi': 1}
        assert abs(stats['average_size_mb'] - 1.17) < 0.01  # Approximately 1.17MB
    
    def test_format_code_standard(self):
        """Test code formatting for standard patterns."""
        scanner = FileScanner('/test', self.supported_formats)
        
        # Mock regex match objects
        class MockMatch:
            def __init__(self, groups):
                self._groups = groups
            
            def groups(self):
                return self._groups
        
        test_cases = [
            (("ABC", "123"), "ABC-123"),
            ("FC2", "PPV", "123456"), "FC2-PPV-123456"),
            (("FC2", "123456"), "FC2-123456"),
            (("N", "1234"), "N1234"),
            (("1PON", "123456"), "1PON-123456"),
        ]
        
        for groups, expected in test_cases:
            if isinstance(groups, tuple) and len(groups) == 2:
                match = MockMatch(groups)
                result = scanner._format_code(match)
                assert result == expected
    
    @patch('src.scanner.file_scanner.Path.iterdir')
    def test_walk_directory_permission_error(self, mock_iterdir):
        """Test handling of permission errors during directory walking."""
        mock_iterdir.side_effect = PermissionError("Access denied")
        
        scanner = FileScanner('/test', self.supported_formats)
        
        # Should not raise exception, just log warning
        results = list(scanner._walk_directory(Path('/test')))
        assert len(results) == 0