#!/usr/bin/env python3
"""Example usage of the FileOrganizer."""

import tempfile
import shutil
from pathlib import Path
from datetime import date

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.organizers.file_organizer import FileOrganizer, ConflictResolution
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata


def create_sample_files(source_dir: Path) -> list:
    """Create sample video files for demonstration."""
    sample_files = []
    
    # Sample file data
    files_data = [
        {
            'filename': 'SSIS-001.mp4',
            'content': b'Sample video content for SSIS-001',
            'metadata': MovieMetadata(
                code='SSIS-001',
                title='Beautiful Secretary',
                actresses=['Yua Mikami'],
                release_date=date(2021, 1, 15),
                studio='S1 NO.1 STYLE',
                series='SSIS',
                genres=['Drama', 'Office']
            )
        },
        {
            'filename': 'STARS-123.mkv',
            'content': b'Sample video content for STARS-123',
            'metadata': MovieMetadata(
                code='STARS-123',
                title='Summer Romance',
                actresses=['Rei Kuroshima', 'Mana Sakura'],
                release_date=date(2021, 7, 20),
                studio='SOD Create',
                series='STARS',
                genres=['Romance', 'Drama']
            )
        },
        {
            'filename': 'MIDE-789.avi',
            'content': b'Sample video content for MIDE-789',
            'metadata': MovieMetadata(
                code='MIDE-789',
                title='Office Lady Special',
                actresses=['Shoko Takahashi'],
                release_date=date(2020, 12, 10),
                studio='MOODYZ',
                genres=['Office', 'Mature']
            )
        }
    ]
    
    # Create sample files
    for file_data in files_data:
        file_path = source_dir / file_data['filename']
        file_path.write_bytes(file_data['content'])
        
        video_file = VideoFile(
            file_path=str(file_path),
            filename=file_data['filename'],
            file_size=len(file_data['content']),
            extension=file_path.suffix,
            detected_code=file_data['metadata'].code
        )
        
        sample_files.append((video_file, file_data['metadata']))
    
    return sample_files


def basic_organization_example():
    """Demonstrate basic file organization."""
    print("=== Basic File Organization Example ===\n")
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir) / "source"
        target_dir = Path(temp_dir) / "target"
        
        source_dir.mkdir(parents=True)
        
        # Create sample files
        sample_files = create_sample_files(source_dir)
        
        # Create organizer with default settings
        organizer = FileOrganizer(
            target_directory=str(target_dir),
            safe_mode=True  # Copy files instead of moving
        )
        
        print(f"Created organizer with target: {target_dir}")
        print(f"Naming pattern: {organizer.naming_pattern}")
        
        # Organize first file
        video_file, metadata = sample_files[0]
        print(f"\nOrganizing: {video_file.filename}")
        
        result = organizer.organize_file(video_file, metadata)
        
        if result['success']:
            print("✓ File organized successfully!")
            print(f"  Original: {result['details']['original_path']}")
            print(f"  Target: {result['details']['target_path']}")
            print(f"  Metadata: {result['details']['metadata_file']}")
            print(f"  Operation: {result['details']['operation']}")
        else:
            print(f"✗ Organization failed: {result['message']}")
        
        # Show statistics
        stats = organizer.get_statistics()
        print(f"\nStatistics:")
        print(f"  Files processed: {stats['files_processed']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")


def custom_naming_patterns_example():
    """Demonstrate custom naming patterns."""
    print("\n=== Custom Naming Patterns Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir) / "source"
        target_dir = Path(temp_dir) / "target"
        
        source_dir.mkdir(parents=True)
        sample_files = create_sample_files(source_dir)
        
        # Different naming patterns
        patterns = [
            ("{code}/{title}.{ext}", "Code-based organization"),
            ("{studio}/{actress}/{code}.{ext}", "Studio-actress organization"),
            ("{year}/{month}/{code}_{title}.{ext}", "Date-based organization"),
            ("{actress}/{series}/{code}.{ext}", "Actress-series organization")
        ]
        
        for pattern, description in patterns:
            print(f"{description}: {pattern}")
            
            organizer = FileOrganizer(
                target_directory=str(target_dir / description.replace(' ', '_')),
                naming_pattern=pattern,
                safe_mode=True
            )
            
            video_file, metadata = sample_files[0]  # Use first sample file
            result = organizer.organize_file(video_file, metadata)
            
            if result['success']:
                target_path = Path(result['details']['target_path'])
                relative_path = target_path.relative_to(target_dir)
                print(f"  Result: {relative_path}")
            else:
                print(f"  Failed: {result['message']}")
            
            print()


def conflict_resolution_example():
    """Demonstrate different conflict resolution strategies."""
    print("\n=== Conflict Resolution Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir) / "source"
        target_dir = Path(temp_dir) / "target"
        
        source_dir.mkdir(parents=True)
        sample_files = create_sample_files(source_dir)
        
        # Create organizer and organize first file
        organizer = FileOrganizer(
            target_directory=str(target_dir),
            conflict_resolution=ConflictResolution.RENAME,
            safe_mode=True
        )
        
        video_file, metadata = sample_files[0]
        
        # Organize file first time
        print("First organization:")
        result1 = organizer.organize_file(video_file, metadata)
        print(f"  Target: {Path(result1['details']['target_path']).name}")
        
        # Try to organize same file again (should create conflict)
        print("\nSecond organization (conflict):")
        result2 = organizer.organize_file(video_file, metadata)
        print(f"  Target: {Path(result2['details']['target_path']).name}")
        
        # Test different conflict resolution strategies
        strategies = [
            (ConflictResolution.SKIP, "Skip existing files"),
            (ConflictResolution.OVERWRITE, "Overwrite existing files"),
            (ConflictResolution.RENAME, "Rename conflicting files")
        ]
        
        for strategy, description in strategies:
            print(f"\nTesting {description}:")
            
            test_organizer = FileOrganizer(
                target_directory=str(target_dir / strategy.value),
                conflict_resolution=strategy,
                safe_mode=True
            )
            
            # Create existing file to test conflict
            test_video, test_metadata = sample_files[1]
            
            # Organize once
            result1 = test_organizer.organize_file(test_video, test_metadata)
            
            # Organize again to create conflict
            result2 = test_organizer.organize_file(test_video, test_metadata)
            
            if result2['success']:
                print(f"  ✓ Handled conflict: {Path(result2['details']['target_path']).name}")
            else:
                print(f"  ✓ Skipped due to conflict: {result2['message']}")


def batch_organization_example():
    """Demonstrate batch file organization."""
    print("\n=== Batch Organization Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir) / "source"
        target_dir = Path(temp_dir) / "target"
        
        source_dir.mkdir(parents=True)
        sample_files = create_sample_files(source_dir)
        
        # Create organizer
        organizer = FileOrganizer(
            target_directory=str(target_dir),
            safe_mode=True
        )
        
        print(f"Organizing {len(sample_files)} files in batch...")
        
        # Organize all files at once
        batch_result = organizer.organize_multiple(sample_files)
        
        print(f"\nBatch Results:")
        print(f"  Total files: {batch_result['total_files']}")
        print(f"  Successful: {batch_result['successful']}")
        print(f"  Failed: {batch_result['failed']}")
        
        print(f"\nIndividual Results:")
        for file_result in batch_result['results']:
            filename = file_result['file']
            success = file_result['result']['success']
            status = "✓" if success else "✗"
            print(f"  {status} {filename}")
        
        # Show final statistics
        final_stats = batch_result['statistics']
        print(f"\nFinal Statistics:")
        print(f"  Files processed: {final_stats['files_processed']}")
        print(f"  Files copied: {final_stats['files_copied']}")
        print(f"  Metadata files created: {final_stats['metadata_files_created']}")
        print(f"  Success rate: {final_stats['success_rate']:.1f}%")


def directory_validation_example():
    """Demonstrate directory validation."""
    print("\n=== Directory Validation Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test with valid directory
        valid_dir = Path(temp_dir) / "valid_target"
        organizer = FileOrganizer(str(valid_dir))
        
        print("Validating target directory...")
        validation_result = organizer.validate_target_directory()
        
        print(f"Valid: {validation_result['valid']}")
        
        if validation_result['errors']:
            print("Errors:")
            for error in validation_result['errors']:
                print(f"  ✗ {error}")
        
        if validation_result['warnings']:
            print("Warnings:")
            for warning in validation_result['warnings']:
                print(f"  ⚠ {warning}")
        
        if validation_result['info']:
            print("Info:")
            for key, value in validation_result['info'].items():
                print(f"  • {key}: {value}")


def cleanup_example():
    """Demonstrate directory cleanup."""
    print("\n=== Directory Cleanup Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / "target"
        
        # Create organizer
        organizer = FileOrganizer(str(target_dir))
        
        # Create some empty directories
        empty_dirs = [
            target_dir / "empty1",
            target_dir / "empty2" / "nested_empty",
            target_dir / "actress1" / "empty_series"
        ]
        
        for empty_dir in empty_dirs:
            empty_dir.mkdir(parents=True, exist_ok=True)
        
        # Create non-empty directory
        non_empty_dir = target_dir / "actress2" / "series1"
        non_empty_dir.mkdir(parents=True, exist_ok=True)
        (non_empty_dir / "movie.mp4").touch()
        
        print("Created test directory structure with empty directories")
        
        # Dry run cleanup
        print("\nDry run cleanup:")
        dry_result = organizer.cleanup_empty_directories(dry_run=True)
        print(f"  Found {len(dry_result['empty_directories'])} empty directories")
        
        for empty_dir in dry_result['empty_directories']:
            print(f"    - {empty_dir}")
        
        # Actual cleanup
        print("\nActual cleanup:")
        cleanup_result = organizer.cleanup_empty_directories(dry_run=False)
        print(f"  Removed {len(cleanup_result['removed_directories'])} directories")
        
        if cleanup_result['errors']:
            print("  Errors:")
            for error in cleanup_result['errors']:
                print(f"    ✗ {error}")


def advanced_features_example():
    """Demonstrate advanced features."""
    print("\n=== Advanced Features Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir) / "source"
        target_dir = Path(temp_dir) / "target"
        
        source_dir.mkdir(parents=True)
        sample_files = create_sample_files(source_dir)
        
        # Create organizer with advanced settings
        organizer = FileOrganizer(
            target_directory=str(target_dir),
            naming_pattern="{actress}/{year}/{code}_{title}.{ext}",
            conflict_resolution=ConflictResolution.RENAME,
            create_metadata_files=True,
            verify_file_integrity=True,
            max_filename_length=50,  # Short limit for demo
            safe_mode=False  # Move files instead of copy
        )
        
        print("Advanced organizer settings:")
        print(f"  Naming pattern: {organizer.naming_pattern}")
        print(f"  Conflict resolution: {organizer.conflict_resolution.value}")
        print(f"  Create metadata files: {organizer.create_metadata_files}")
        print(f"  Verify integrity: {organizer.verify_file_integrity}")
        print(f"  Max filename length: {organizer.max_filename_length}")
        print(f"  Safe mode: {organizer.safe_mode}")
        
        # Organize file with long title to test truncation
        video_file, metadata = sample_files[0]
        metadata.title = "Very Long Movie Title That Exceeds Maximum Length Limits"
        
        print(f"\nOrganizing file with long title...")
        result = organizer.organize_file(video_file, metadata)
        
        if result['success']:
            target_path = Path(result['details']['target_path'])
            print(f"  ✓ Organized: {target_path.name}")
            print(f"  Length: {len(target_path.name)} characters")
            
            # Check if metadata file was created
            metadata_file = Path(result['details']['metadata_file'])
            if metadata_file.exists():
                print(f"  ✓ Metadata file created: {metadata_file.name}")
        else:
            print(f"  ✗ Failed: {result['message']}")


def main():
    """Run all examples."""
    print("FileOrganizer Examples")
    print("=" * 50)
    
    try:
        basic_organization_example()
        custom_naming_patterns_example()
        conflict_resolution_example()
        batch_organization_example()
        directory_validation_example()
        cleanup_example()
        advanced_features_example()
        
        print("\n" + "=" * 50)
        print("All examples completed!")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error in examples: {e}")


if __name__ == "__main__":
    main()