"""Mock data generators for testing."""

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict

from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata


class MockDataGenerator:
    """Generates realistic mock data for testing."""
    
    # Sample data for generating realistic metadata
    STUDIOS = [
        'S1 NO.1 STYLE', 'MOODYZ', 'IDEAPOCKET', 'PREMIUM', 'ATTACKERS',
        'E-BODY', 'MADONNA', 'Fitch', 'OPPAI', 'WANZ FACTORY', 'FC2',
        '1Pondo', 'Caribbeancom', 'HEYZO', 'Tokyo Hot'
    ]
    
    ACTRESSES = [
        'Yui Hatano', 'Mia Nanasawa', 'Rika Aimi', 'Tsukasa Aoi', 'Rei Mizuna',
        'Akari Mitani', 'Yua Mikami', 'Shoko Takahashi', 'Eimi Fukada', 'Minami Aizawa',
        'Kana Momonogi', 'Rara Anzai', 'Ichika Matsumoto', 'Mahiro Tadai', 'Yume Nishimiya'
    ]
    
    SERIES = [
        'First Impression', 'Beautiful Girl', 'Office Lady', 'School Girl',
        'Married Woman', 'Big Tits', 'Slender', 'Amateur', 'Cosplay', 'Massage'
    ]
    
    GENRES = [
        'Drama', 'Beautiful Girl', 'Single Work', 'Big Tits', 'Slender',
        'Married Woman', 'Mature Woman', 'School Girl', 'Office Lady', 'Cosplay',
        'Massage', 'Creampie', 'Facial', 'Oral', 'Threesome', 'Group'
    ]
    
    CODE_PATTERNS = [
        'SSIS-{:03d}', 'SSNI-{:03d}', 'MIDE-{:03d}', 'PRED-{:03d}', 'IPX-{:03d}',
        'PPPD-{:03d}', 'MEYD-{:03d}', 'JUL-{:03d}', 'JUFE-{:03d}', 'EBOD-{:03d}',
        'FC2-PPV-{:06d}', '1PON-{:06d}', 'CARIB-{:06d}', 'HEYZO-{:04d}'
    ]
    
    @classmethod
    def generate_video_file(cls, 
                          code: Optional[str] = None,
                          extension: str = '.mp4',
                          base_path: str = '/test') -> VideoFile:
        """Generate a mock VideoFile object."""
        if code is None:
            pattern = random.choice(cls.CODE_PATTERNS)
            if 'PPV' in pattern or 'PON' in pattern or 'CARIB' in pattern:
                code = pattern.format(random.randint(100000, 999999))
            else:
                code = pattern.format(random.randint(1, 999))
        
        filename = f"{code}{extension}"
        file_path = f"{base_path}/{filename}"
        
        # Generate realistic file sizes (100MB to 5GB)
        file_size = random.randint(100 * 1024 * 1024, 5 * 1024 * 1024 * 1024)
        
        # Generate timestamps
        created_time = datetime.now() - timedelta(days=random.randint(1, 365))
        modified_time = created_time + timedelta(hours=random.randint(0, 24))
        
        return VideoFile(
            file_path=file_path,
            filename=filename,
            file_size=file_size,
            extension=extension,
            detected_code=code,
            created_time=created_time,
            modified_time=modified_time
        )
    
    @classmethod
    def generate_movie_metadata(cls, 
                              code: Optional[str] = None,
                              include_images: bool = True,
                              include_optional_fields: bool = True) -> MovieMetadata:
        """Generate a mock MovieMetadata object."""
        if code is None:
            pattern = random.choice(cls.CODE_PATTERNS)
            if 'PPV' in pattern or 'PON' in pattern or 'CARIB' in pattern:
                code = pattern.format(random.randint(100000, 999999))
            else:
                code = pattern.format(random.randint(1, 999))
        
        # Generate basic metadata
        title = cls._generate_title()
        actresses = random.sample(cls.ACTRESSES, random.randint(1, 3))
        studio = random.choice(cls.STUDIOS)
        
        metadata = MovieMetadata(
            code=code,
            title=title,
            actresses=actresses,
            studio=studio,
            source_url=f"https://javdb.com/v/{code.lower().replace('-', '')}"
        )
        
        if include_optional_fields:
            # Add optional fields
            metadata.title_en = title  # Same as title for simplicity
            metadata.release_date = cls._generate_release_date()
            metadata.duration = random.randint(60, 180)  # 1-3 hours
            metadata.series = random.choice(cls.SERIES) if random.random() > 0.3 else None
            metadata.genres = random.sample(cls.GENRES, random.randint(2, 5))
            metadata.description = cls._generate_description(title, actresses[0])
            metadata.rating = round(random.uniform(3.0, 5.0), 1)
            metadata.scraped_at = datetime.now()
        
        if include_images:
            # Add image URLs
            base_url = "https://example.com/images"
            metadata.cover_url = f"{base_url}/covers/{code.lower()}_cover.jpg"
            metadata.poster_url = f"{base_url}/posters/{code.lower()}_poster.jpg"
            metadata.screenshots = [
                f"{base_url}/screenshots/{code.lower()}_{i}.jpg" 
                for i in range(1, random.randint(3, 8))
            ]
        
        return metadata
    
    @classmethod
    def generate_video_file_batch(cls, count: int, **kwargs) -> List[VideoFile]:
        """Generate a batch of VideoFile objects."""
        return [cls.generate_video_file(**kwargs) for _ in range(count)]
    
    @classmethod
    def generate_metadata_batch(cls, count: int, **kwargs) -> List[MovieMetadata]:
        """Generate a batch of MovieMetadata objects."""
        return [cls.generate_movie_metadata(**kwargs) for _ in range(count)]
    
    @classmethod
    def generate_test_directory_structure(cls, base_path: Path, file_count: int = 50):
        """Generate a realistic test directory structure with video files."""
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create main directory with files
        main_files = cls._generate_filenames(file_count // 2)
        for filename in main_files:
            file_path = base_path / filename
            file_path.write_bytes(b"fake video content" * random.randint(100, 1000))
        
        # Create subdirectories
        subdirs = ['JAV', 'Uncensored', 'Amateur', 'Vintage']
        for subdir in subdirs:
            subdir_path = base_path / subdir
            subdir_path.mkdir(exist_ok=True)
            
            subdir_files = cls._generate_filenames(file_count // (len(subdirs) * 2))
            for filename in subdir_files:
                file_path = subdir_path / filename
                file_path.write_bytes(b"fake video content" * random.randint(100, 1000))
        
        return base_path
    
    @classmethod
    def create_mock_config(cls, 
                          source_dir: str,
                          target_dir: str,
                          **overrides) -> Dict:
        """Create a mock configuration dictionary."""
        config = {
            'logging': {
                'level': 'INFO',
                'console': True,
                'file': False,
                'directory': '/tmp/logs'
            },
            'scanner': {
                'source_directory': source_dir,
                'supported_formats': ['.mp4', '.mkv', '.avi', '.wmv', '.mov'],
                'recursive': True
            },
            'organizer': {
                'target_directory': target_dir,
                'naming_pattern': '{actress}/{code}/{code}.{ext}',
                'safe_mode': True,
                'create_metadata_files': True
            },
            'scrapers': {
                'priority': ['javdb', 'javlibrary'],
                'timeout_seconds': 30,
                'retry_attempts': 2,
                'cache_duration_minutes': 60
            },
            'downloader': {
                'enabled': True,
                'max_concurrent': 3,
                'timeout_seconds': 30,
                'retry_attempts': 2
            },
            'processing': {
                'max_concurrent_files': 5,
                'batch_size': 20
            }
        }
        
        # Apply overrides
        for key, value in overrides.items():
            if '.' in key:
                # Handle nested keys like 'scanner.recursive'
                parts = key.split('.')
                current = config
                for part in parts[:-1]:
                    current = current[part]
                current[parts[-1]] = value
            else:
                config[key] = value
        
        return config
    
    @classmethod
    def save_mock_data_to_files(cls, 
                               output_dir: Path,
                               video_files: List[VideoFile],
                               metadata_list: List[MovieMetadata]):
        """Save mock data to JSON files for testing."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save video files
        video_files_data = [asdict(vf) for vf in video_files]
        with open(output_dir / 'mock_video_files.json', 'w', encoding='utf-8') as f:
            json.dump(video_files_data, f, indent=2, default=str, ensure_ascii=False)
        
        # Save metadata
        metadata_data = [asdict(md) for md in metadata_list]
        with open(output_dir / 'mock_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata_data, f, indent=2, default=str, ensure_ascii=False)
        
        # Save mapping of codes to metadata
        code_mapping = {md.code: asdict(md) for md in metadata_list}
        with open(output_dir / 'mock_code_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(code_mapping, f, indent=2, default=str, ensure_ascii=False)
    
    @classmethod
    def load_mock_data_from_files(cls, input_dir: Path) -> Dict:
        """Load mock data from JSON files."""
        data = {}
        
        # Load video files
        video_files_path = input_dir / 'mock_video_files.json'
        if video_files_path.exists():
            with open(video_files_path, 'r', encoding='utf-8') as f:
                video_files_data = json.load(f)
                data['video_files'] = [VideoFile(**vf) for vf in video_files_data]
        
        # Load metadata
        metadata_path = input_dir / 'mock_metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_data = json.load(f)
                data['metadata'] = [MovieMetadata(**md) for md in metadata_data]
        
        # Load code mapping
        mapping_path = input_dir / 'mock_code_mapping.json'
        if mapping_path.exists():
            with open(mapping_path, 'r', encoding='utf-8') as f:
                data['code_mapping'] = json.load(f)
        
        return data
    
    @classmethod
    def _generate_title(cls) -> str:
        """Generate a realistic movie title."""
        title_templates = [
            "{adjective} {noun} {action}",
            "{actress_type} {action} {theme}",
            "{theme} {adjective} {noun}",
            "{action} with {adjective} {actress_type}",
            "{number} {noun} {action}"
        ]
        
        adjectives = ['Beautiful', 'Passionate', 'Secret', 'Forbidden', 'Sweet', 'Wild', 'Gentle', 'Intense']
        nouns = ['Love', 'Desire', 'Romance', 'Affair', 'Encounter', 'Experience', 'Story', 'Dream']
        actions = ['Awakening', 'Temptation', 'Seduction', 'Adventure', 'Journey', 'Discovery']
        actress_types = ['Office Lady', 'School Girl', 'Housewife', 'Teacher', 'Nurse', 'Student']
        themes = ['Summer', 'Night', 'Weekend', 'Holiday', 'Morning', 'Evening']
        numbers = ['First', 'Second', 'Last', 'Special', 'Final', 'Ultimate']
        
        template = random.choice(title_templates)
        return template.format(
            adjective=random.choice(adjectives),
            noun=random.choice(nouns),
            action=random.choice(actions),
            actress_type=random.choice(actress_types),
            theme=random.choice(themes),
            number=random.choice(numbers)
        )
    
    @classmethod
    def _generate_description(cls, title: str, actress: str) -> str:
        """Generate a realistic description."""
        templates = [
            f"In this captivating story, {actress} delivers an outstanding performance in '{title}'. "
            "A must-watch for fans of quality entertainment.",
            
            f"{actress} stars in this beautiful production that showcases her incredible talent. "
            f"'{title}' is a masterpiece that will leave you wanting more.",
            
            f"Experience the magic of {actress} in '{title}'. This exceptional work features "
            "stunning cinematography and an engaging storyline.",
            
            f"Don't miss {actress}'s amazing performance in '{title}'. "
            "This production sets new standards for quality and entertainment."
        ]
        
        return random.choice(templates)
    
    @classmethod
    def _generate_release_date(cls) -> date:
        """Generate a realistic release date."""
        # Generate dates from 2020 to present
        start_date = date(2020, 1, 1)
        end_date = date.today()
        
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        
        return start_date + timedelta(days=random_days)
    
    @classmethod
    def _generate_filenames(cls, count: int) -> List[str]:
        """Generate realistic video filenames."""
        filenames = []
        extensions = ['.mp4', '.mkv', '.avi', '.wmv', '.mov']
        
        for _ in range(count):
            # Generate code
            pattern = random.choice(cls.CODE_PATTERNS)
            if 'PPV' in pattern or 'PON' in pattern or 'CARIB' in pattern:
                code = pattern.format(random.randint(100000, 999999))
            else:
                code = pattern.format(random.randint(1, 999))
            
            extension = random.choice(extensions)
            
            # Add some variation to filenames
            variations = [
                f"{code}{extension}",
                f"[Studio] {code} [1080p]{extension}",
                f"{code}_HD{extension}",
                f"({code}) High Quality{extension}",
                f"{code} - Beautiful Actress{extension}"
            ]
            
            filename = random.choice(variations)
            filenames.append(filename)
        
        return filenames


class MockWebResponses:
    """Mock web responses for scraper testing."""
    
    @staticmethod
    def javdb_search_response(code: str) -> str:
        """Generate mock JavDB search response HTML."""
        return f"""
        <html>
        <head><title>JavDB - {code}</title></head>
        <body>
            <div class="movie-panel">
                <div class="movie-panel-info">
                    <h2 class="title">{MockDataGenerator._generate_title()}</h2>
                    <div class="panel-block">
                        <strong>番號:</strong>
                        <span>{code}</span>
                    </div>
                    <div class="panel-block">
                        <strong>演員:</strong>
                        <a href="#">{random.choice(MockDataGenerator.ACTRESSES)}</a>
                    </div>
                    <div class="panel-block">
                        <strong>製作商:</strong>
                        <span>{random.choice(MockDataGenerator.STUDIOS)}</span>
                    </div>
                    <div class="panel-block">
                        <strong>發行日期:</strong>
                        <span>2023-01-15</span>
                    </div>
                </div>
                <div class="column-video-cover">
                    <img src="https://example.com/covers/{code.lower()}_cover.jpg" alt="Cover">
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def javlibrary_search_response(code: str) -> str:
        """Generate mock JavLibrary search response HTML."""
        return f"""
        <html>
        <head><title>JAVLibrary - {code}</title></head>
        <body>
            <div id="video_info">
                <h3>{MockDataGenerator._generate_title()}</h3>
                <div id="video_id">
                    <table>
                        <tr><td>ID:</td><td>{code}</td></tr>
                        <tr><td>Release Date:</td><td>2023-01-15</td></tr>
                        <tr><td>Length:</td><td>120 min.</td></tr>
                        <tr><td>Studio:</td><td>{random.choice(MockDataGenerator.STUDIOS)}</td></tr>
                    </table>
                </div>
                <div id="video_cast">
                    <span class="cast">
                        <a href="#">{random.choice(MockDataGenerator.ACTRESSES)}</a>
                    </span>
                </div>
            </div>
            <div id="video_jacket_img">
                <img src="https://example.com/covers/{code.lower()}_cover.jpg" alt="Cover">
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def error_response(status_code: int = 404) -> str:
        """Generate mock error response."""
        return f"""
        <html>
        <head><title>Error {status_code}</title></head>
        <body>
            <h1>Error {status_code}</h1>
            <p>The requested resource was not found.</p>
        </body>
        </html>
        """


# Convenience functions for common test scenarios
def create_test_video_files(count: int = 10) -> List[VideoFile]:
    """Create a list of test video files."""
    return MockDataGenerator.generate_video_file_batch(count)


def create_test_metadata(count: int = 10) -> List[MovieMetadata]:
    """Create a list of test metadata objects."""
    return MockDataGenerator.generate_metadata_batch(count)


def create_test_environment(base_path: Path, file_count: int = 20) -> Dict:
    """Create a complete test environment."""
    source_dir = base_path / "source"
    target_dir = base_path / "target"
    
    # Create directories
    source_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate test files
    MockDataGenerator.generate_test_directory_structure(source_dir, file_count)
    
    # Create configuration
    config = MockDataGenerator.create_mock_config(str(source_dir), str(target_dir))
    
    return {
        'source_dir': source_dir,
        'target_dir': target_dir,
        'config': config,
        'base_path': base_path
    }