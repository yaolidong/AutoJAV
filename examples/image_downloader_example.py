#!/usr/bin/env python3
"""Example usage of the ImageDownloader."""

import asyncio
import tempfile
from pathlib import Path
from datetime import date

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.downloaders.image_downloader import ImageDownloader, ImageType, ImageFormat
from src.models.movie_metadata import MovieMetadata
from src.utils.http_client import HttpClient


def create_sample_metadata() -> MovieMetadata:
    """Create sample movie metadata with image URLs."""
    return MovieMetadata(
        code="SSIS-001",
        title="Beautiful Secretary",
        actresses=["Yua Mikami"],
        release_date=date(2021, 1, 15),
        studio="S1 NO.1 STYLE",
        cover_url="https://pics.dmm.co.jp/digital/video/ssis00001/ssis00001pl.jpg",
        poster_url="https://pics.dmm.co.jp/digital/video/ssis00001/ssis00001ps.jpg",
        screenshots=[
            "https://pics.dmm.co.jp/digital/video/ssis00001/ssis00001jp-1.jpg",
            "https://pics.dmm.co.jp/digital/video/ssis00001/ssis00001jp-2.jpg",
            "https://pics.dmm.co.jp/digital/video/ssis00001/ssis00001jp-3.jpg"
        ]
    )


async def basic_download_example():
    """Demonstrate basic image downloading."""
    print("=== Basic Image Download Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / "images"
        
        # Create downloader with default settings
        downloader = ImageDownloader()
        
        # Create sample metadata
        metadata = create_sample_metadata()
        
        print(f"Downloading images for: {metadata.code}")
        print(f"Target directory: {target_dir}")
        print(f"Cover URL: {metadata.cover_url}")
        print(f"Poster URL: {metadata.poster_url}")
        print(f"Screenshots: {len(metadata.screenshots)} images")
        
        # Download all images
        result = await downloader.download_movie_images(metadata, target_dir)
        
        if result['success']:
            print(f"\n✓ Download completed successfully!")
            print(f"  Downloaded files: {len(result['downloaded_files'])}")
            print(f"  Failed downloads: {len(result['failed_downloads'])}")
            
            # List downloaded files
            if result['downloaded_files']:
                print("\n  Downloaded files:")
                for file_path in result['downloaded_files']:
                    file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                    print(f"    - {Path(file_path).name} ({file_size} bytes)")
            
            # Show any failures
            if result['failed_downloads']:
                print("\n  Failed downloads:")
                for failure in result['failed_downloads']:
                    print(f"    - {failure}")
        else:
            print(f"✗ Download failed: {result['message']}")
        
        # Show statistics
        stats = downloader.get_statistics()
        print(f"\nStatistics:")
        print(f"  Images downloaded: {stats['images_downloaded']}")
        print(f"  Download failures: {stats['download_failures']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Total MB downloaded: {stats['total_mb_downloaded']:.2f}")


async def specific_image_types_example():
    """Demonstrate downloading specific image types."""
    print("\n=== Specific Image Types Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / "images"
        
        downloader = ImageDownloader()
        metadata = create_sample_metadata()
        
        # Download only cover and poster (no screenshots)
        print("Downloading only cover and poster images...")
        
        result = await downloader.download_movie_images(
            metadata,
            target_dir,
            image_types=[ImageType.COVER, ImageType.POSTER]
        )
        
        print(f"Result: {result['message']}")
        print(f"Files downloaded: {len(result['downloaded_files'])}")
        print(f"Total requested: {result['total_requested']}")
        
        # Download only screenshots
        print("\nDownloading only screenshots...")
        
        result = await downloader.download_movie_images(
            metadata,
            target_dir / "screenshots",
            image_types=[ImageType.SCREENSHOT]
        )
        
        print(f"Result: {result['message']}")
        print(f"Screenshot files: {len(result['downloaded_files'])}")


async def image_processing_example():
    """Demonstrate image processing features."""
    print("\n=== Image Processing Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / "processed"
        
        # Create downloader with processing options
        downloader = ImageDownloader(
            convert_format=ImageFormat.JPEG,
            resize_images=True,
            max_width=800,
            max_height=600,
            jpeg_quality=80,
            create_thumbnails=True,
            thumbnail_size=(200, 150)
        )
        
        print("Downloader settings:")
        print(f"  Convert format: {downloader.convert_format.value}")
        print(f"  Resize images: {downloader.resize_images}")
        print(f"  Max dimensions: {downloader.max_width}x{downloader.max_height}")
        print(f"  JPEG quality: {downloader.jpeg_quality}")
        print(f"  Create thumbnails: {downloader.create_thumbnails}")
        print(f"  Thumbnail size: {downloader.thumbnail_size}")
        
        metadata = create_sample_metadata()
        
        print(f"\nProcessing images for: {metadata.code}")
        
        result = await downloader.download_movie_images(metadata, target_dir)
        
        if result['success']:
            print(f"✓ Processing completed!")
            
            # Show processing statistics
            stats = downloader.get_statistics()
            print(f"\nProcessing statistics:")
            print(f"  Images processed: {stats['images_processed']}")
            print(f"  Images converted: {stats['images_converted']}")
            print(f"  Images resized: {stats['images_resized']}")
            print(f"  Thumbnails created: {stats['thumbnails_created']}")
        else:
            print(f"✗ Processing failed: {result['message']}")


async def concurrent_downloads_example():
    """Demonstrate concurrent downloading."""
    print("\n=== Concurrent Downloads Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create multiple movie metadata
        movies = []
        for i in range(3):
            movie = MovieMetadata(
                code=f"TEST-{i:03d}",
                title=f"Test Movie {i}",
                cover_url=f"https://example.com/cover_{i}.jpg",
                poster_url=f"https://example.com/poster_{i}.jpg",
                screenshots=[
                    f"https://example.com/screenshot_{i}_1.jpg",
                    f"https://example.com/screenshot_{i}_2.jpg"
                ]
            )
            movies.append(movie)
        
        # Create downloader with high concurrency
        downloader = ImageDownloader(max_concurrent_downloads=5)
        
        print(f"Downloading images for {len(movies)} movies concurrently...")
        
        # Download all movies concurrently
        tasks = []
        for movie in movies:
            target_dir = Path(temp_dir) / movie.code
            task = downloader.download_movie_images(movie, target_dir)
            tasks.append(task)
        
        # Wait for all downloads to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"✗ {movies[i].code}: Exception - {result}")
                failed += 1
            elif result['success']:
                print(f"✓ {movies[i].code}: {len(result['downloaded_files'])} files")
                successful += 1
            else:
                print(f"✗ {movies[i].code}: {result['message']}")
                failed += 1
        
        print(f"\nConcurrent download results: {successful} successful, {failed} failed")
        
        # Show final statistics
        stats = downloader.get_statistics()
        print(f"Total images downloaded: {stats['images_downloaded']}")
        print(f"Total failures: {stats['download_failures']}")


async def error_handling_example():
    """Demonstrate error handling and retry mechanisms."""
    print("\n=== Error Handling Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / "error_test"
        
        # Create downloader with retry settings
        downloader = ImageDownloader(
            retry_attempts=2,
            timeout_seconds=5
        )
        
        # Create metadata with invalid URLs
        metadata = MovieMetadata(
            code="ERROR-TEST",
            title="Error Test Movie",
            cover_url="https://nonexistent-domain-12345.com/cover.jpg",
            poster_url="https://httpstat.us/404",  # Returns 404
            screenshots=[
                "https://httpstat.us/500",  # Returns 500 error
                "https://httpstat.us/timeout"  # Times out
            ]
        )
        
        print("Testing error handling with invalid URLs:")
        print(f"  Cover: {metadata.cover_url}")
        print(f"  Poster: {metadata.poster_url}")
        print(f"  Screenshots: {len(metadata.screenshots)} URLs")
        
        result = await downloader.download_movie_images(metadata, target_dir)
        
        print(f"\nResult: {result['message']}")
        print(f"Downloaded files: {len(result['downloaded_files'])}")
        print(f"Failed downloads: {len(result['failed_downloads'])}")
        
        if result['failed_downloads']:
            print("\nFailure details:")
            for failure in result['failed_downloads']:
                print(f"  - {failure}")
        
        # Show error statistics
        stats = downloader.get_statistics()
        print(f"\nError statistics:")
        print(f"  Download failures: {stats['download_failures']}")
        print(f"  Processing failures: {stats['processing_failures']}")


async def file_management_example():
    """Demonstrate file management features."""
    print("\n=== File Management Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / "management_test"
        
        downloader = ImageDownloader()
        
        # Create some test files (simulating previous downloads)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create valid image file
        valid_image = target_dir / "valid.jpg"
        valid_image.write_bytes(b'\xFF\xD8\xFF\xE0' + b'0' * 100 + b'\xFF\xD9')
        
        # Create empty/corrupted files
        empty_image = target_dir / "empty.jpg"
        empty_image.touch()
        
        corrupted_image = target_dir / "corrupted.png"
        corrupted_image.write_bytes(b'invalid image data')
        
        # Create non-image file (should be ignored)
        text_file = target_dir / "readme.txt"
        text_file.write_text("This is not an image")
        
        print(f"Created test files in: {target_dir}")
        print(f"  Valid image: {valid_image.name}")
        print(f"  Empty image: {empty_image.name}")
        print(f"  Corrupted image: {corrupted_image.name}")
        print(f"  Text file: {text_file.name}")
        
        # Test image integrity verification
        print(f"\nTesting image integrity:")
        
        for image_file in [valid_image, empty_image, corrupted_image]:
            is_valid = await downloader.verify_image_integrity(image_file)
            status = "✓ Valid" if is_valid else "✗ Invalid"
            print(f"  {image_file.name}: {status}")
        
        # Test cleanup of failed downloads
        print(f"\nCleaning up corrupted files...")
        
        cleanup_result = await downloader.cleanup_failed_downloads(target_dir)
        
        print(f"Cleanup results:")
        print(f"  Files checked: {cleanup_result['checked_files']}")
        print(f"  Corrupted files found: {len(cleanup_result['corrupted_files'])}")
        print(f"  Files removed: {len(cleanup_result['removed_files'])}")
        
        if cleanup_result['errors']:
            print(f"  Errors: {len(cleanup_result['errors'])}")
            for error in cleanup_result['errors']:
                print(f"    - {error}")
        
        # Check which files remain
        remaining_files = list(target_dir.glob("*"))
        print(f"\nRemaining files: {len(remaining_files)}")
        for file_path in remaining_files:
            print(f"  - {file_path.name}")


async def configuration_examples():
    """Demonstrate different configuration options."""
    print("\n=== Configuration Examples ===\n")
    
    configurations = [
        {
            'name': 'High Quality',
            'config': {
                'convert_format': ImageFormat.PNG,
                'resize_images': False,
                'create_thumbnails': True,
                'max_file_size_mb': 100
            }
        },
        {
            'name': 'Optimized Size',
            'config': {
                'convert_format': ImageFormat.JPEG,
                'resize_images': True,
                'max_width': 1024,
                'max_height': 768,
                'jpeg_quality': 70,
                'create_thumbnails': False
            }
        },
        {
            'name': 'Fast Download',
            'config': {
                'max_concurrent_downloads': 10,
                'timeout_seconds': 10,
                'retry_attempts': 1,
                'convert_format': ImageFormat.AUTO,
                'resize_images': False
            }
        }
    ]
    
    for config_info in configurations:
        print(f"{config_info['name']} Configuration:")
        
        for key, value in config_info['config'].items():
            print(f"  {key}: {value}")
        
        # Create downloader with this configuration
        downloader = ImageDownloader(**config_info['config'])
        
        print(f"  Created downloader with {config_info['name'].lower()} settings")
        print()


async def main():
    """Run all examples."""
    print("ImageDownloader Examples")
    print("=" * 50)
    
    try:
        await basic_download_example()
        await specific_image_types_example()
        await image_processing_example()
        await concurrent_downloads_example()
        await error_handling_example()
        await file_management_example()
        await configuration_examples()
        
        print("\n" + "=" * 50)
        print("All examples completed!")
        print("\nNote: Some examples may show failures due to using")
        print("example URLs that don't exist. This is expected and")
        print("demonstrates the error handling capabilities.")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error in examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())