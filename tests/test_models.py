"""Tests for data models."""

import pytest
from datetime import datetime, date
from src.models import VideoFile, MovieMetadata, Config


class TestVideoFile:
    """Test cases for VideoFile model."""
    
    def test_video_file_creation(self):
        """Test creating a valid VideoFile."""
        video = VideoFile(
            file_path="/path/to/video.mp4",
            filename="video.mp4",
            file_size=1024000,
            extension=".mp4"
        )
        
        assert video.file_path == "/path/to/video.mp4"
        assert video.filename == "video.mp4"
        assert video.file_size == 1024000
        assert video.extension == ".mp4"
        assert video.detected_code is None
    
    def test_video_file_validation(self):
        """Test VideoFile validation."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            VideoFile(file_path="", filename="test.mp4", file_size=1000, extension=".mp4")
        
        with pytest.raises(ValueError, match="filename cannot be empty"):
            VideoFile(file_path="/test", filename="", file_size=1000, extension=".mp4")
        
        with pytest.raises(ValueError, match="file_size cannot be negative"):
            VideoFile(file_path="/test", filename="test.mp4", file_size=-1, extension=".mp4")
    
    def test_video_file_properties(self):
        """Test VideoFile properties."""
        video = VideoFile(
            file_path="/path/to/video.mp4",
            filename="video.mp4",
            file_size=1048576,  # 1MB
            extension=".mp4"
        )
        
        assert video.full_path == "/path/to/video.mp4"
        assert video.size_mb == 1.0


class TestMovieMetadata:
    """Test cases for MovieMetadata model."""
    
    def test_movie_metadata_creation(self):
        """Test creating valid MovieMetadata."""
        metadata = MovieMetadata(
            code="TEST-001",
            title="Test Movie",
            actresses=["Actress 1", "Actress 2"]
        )
        
        assert metadata.code == "TEST-001"
        assert metadata.title == "Test Movie"
        assert metadata.actresses == ["Actress 1", "Actress 2"]
        assert metadata.primary_actress == "Actress 1"
    
    def test_movie_metadata_validation(self):
        """Test MovieMetadata validation."""
        with pytest.raises(ValueError, match="code cannot be empty"):
            MovieMetadata(code="", title="Test")
        
        with pytest.raises(ValueError, match="title cannot be empty"):
            MovieMetadata(code="TEST-001", title="")
        
        with pytest.raises(ValueError, match="rating must be between 0 and 10"):
            MovieMetadata(code="TEST-001", title="Test", rating=15)
    
    def test_duration_str(self):
        """Test duration string formatting."""
        metadata = MovieMetadata(code="TEST-001", title="Test", duration=90)
        assert metadata.duration_str == "1h 30m"
        
        metadata.duration = 45
        assert metadata.duration_str == "45m"
        
        metadata.duration = None
        assert metadata.duration_str == "Unknown"


class TestConfig:
    """Test cases for Config model."""
    
    def test_config_creation(self):
        """Test creating valid Config."""
        config = Config(
            source_directory="/source",
            target_directory="/target"
        )
        
        assert config.source_directory == "/source"
        assert config.target_directory == "/target"
        assert config.max_concurrent_files == 3
        assert config.headless_browser is True
    
    def test_config_validation(self):
        """Test Config validation."""
        with pytest.raises(ValueError, match="source_directory cannot be empty"):
            Config(source_directory="", target_directory="/target")
        
        with pytest.raises(ValueError, match="max_concurrent_files must be at least 1"):
            Config(source_directory="/source", target_directory="/target", max_concurrent_files=0)
    
    def test_supported_extensions(self):
        """Test extension support checking."""
        config = Config(source_directory="/source", target_directory="/target")
        
        assert config.is_supported_extension(".mp4")
        assert config.is_supported_extension("mp4")
        assert config.is_supported_extension(".MP4")
        assert not config.is_supported_extension(".txt")