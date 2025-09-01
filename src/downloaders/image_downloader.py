"""Image downloader for handling cover images, posters, and screenshots."""

import asyncio
import logging
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse, urljoin
from datetime import datetime
from enum import Enum

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ..utils.http_client import HttpClient
from ..models.movie_metadata import MovieMetadata


class ImageType(Enum):
    """Types of images that can be downloaded."""
    COVER = "cover"
    POSTER = "poster"
    SCREENSHOT = "screenshot"
    THUMBNAIL = "thumbnail"


class ImageFormat(Enum):
    """Supported image formats."""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    AUTO = "auto"  # Keep original format


class ImageDownloader:
    """
    Downloads and processes images from movie metadata.
    
    This class handles downloading cover images, posters, and screenshots
    with support for format conversion, resizing, and optimization.
    """
    
    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        max_concurrent_downloads: int = 3,
        timeout_seconds: int = 30,
        retry_attempts: int = 3,
        max_file_size_mb: int = 50,
        convert_format: ImageFormat = ImageFormat.AUTO,
        resize_images: bool = False,
        max_width: int = 1920,
        max_height: int = 1080,
        jpeg_quality: int = 85,
        create_thumbnails: bool = False,
        thumbnail_size: Tuple[int, int] = (300, 200)
    ):
        """
        Initialize the image downloader.
        
        Args:
            http_client: HTTP client for downloading images
            max_concurrent_downloads: Maximum concurrent downloads
            timeout_seconds: Download timeout per image
            retry_attempts: Number of retry attempts for failed downloads
            max_file_size_mb: Maximum file size in MB
            convert_format: Target image format for conversion
            resize_images: Whether to resize large images
            max_width: Maximum image width for resizing
            max_height: Maximum image height for resizing
            jpeg_quality: JPEG compression quality (1-100)
            create_thumbnails: Whether to create thumbnail versions
            thumbnail_size: Thumbnail dimensions (width, height)
        """
        self.http_client = http_client or HttpClient(
            timeout=timeout_seconds,
            max_retries=retry_attempts,
            rate_limit_delay=1.0
        )
        self.max_concurrent_downloads = max_concurrent_downloads
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.convert_format = convert_format
        self.resize_images = resize_images
        self.max_width = max_width
        self.max_height = max_height
        self.jpeg_quality = jpeg_quality
        self.create_thumbnails = create_thumbnails
        self.thumbnail_size = thumbnail_size
        
        self.logger = logging.getLogger(__name__)
        
        # Check PIL availability for image processing
        if not PIL_AVAILABLE and (resize_images or convert_format != ImageFormat.AUTO or create_thumbnails):
            self.logger.warning("PIL not available. Image processing features disabled.")
            self.resize_images = False
            self.convert_format = ImageFormat.AUTO
            self.create_thumbnails = False
        
        # Statistics tracking
        self.stats = {
            'images_downloaded': 0,
            'images_processed': 0,
            'images_converted': 0,
            'images_resized': 0,
            'thumbnails_created': 0,
            'download_failures': 0,
            'processing_failures': 0,
            'total_bytes_downloaded': 0
        }
        
        # Semaphore for concurrent downloads
        self._download_semaphore = asyncio.Semaphore(max_concurrent_downloads)
        
        self.logger.info(f"Initialized ImageDownloader with {max_concurrent_downloads} concurrent downloads")
    
    async def download_movie_images(
        self,
        metadata: MovieMetadata,
        target_directory: Path,
        image_types: Optional[List[ImageType]] = None
    ) -> Dict[str, Any]:
        """
        Download all images for a movie.
        
        Args:
            metadata: Movie metadata containing image URLs
            target_directory: Directory to save images
            image_types: Optional list of image types to download
            
        Returns:
            Dictionary with download results
        """
        if image_types is None:
            image_types = [ImageType.COVER, ImageType.POSTER, ImageType.SCREENSHOT]
        
        self.logger.info(f"Downloading images for {metadata.code}")
        
        # Ensure target directory exists
        target_directory.mkdir(parents=True, exist_ok=True)
        
        download_tasks = []
        
        # Download cover image
        if ImageType.COVER in image_types and metadata.cover_url:
            cover_filename = self._generate_filename(metadata.code, ImageType.COVER, metadata.cover_url)
            cover_path = target_directory / cover_filename
            download_tasks.append(
                self._download_single_image(metadata.cover_url, cover_path, ImageType.COVER)
            )
        
        # Download poster image
        if ImageType.POSTER in image_types and metadata.poster_url:
            poster_filename = self._generate_filename(metadata.code, ImageType.POSTER, metadata.poster_url)
            poster_path = target_directory / poster_filename
            download_tasks.append(
                self._download_single_image(metadata.poster_url, poster_path, ImageType.POSTER)
            )
        
        # Download screenshots
        if ImageType.SCREENSHOT in image_types and metadata.screenshots:
            for i, screenshot_url in enumerate(metadata.screenshots):
                screenshot_filename = self._generate_filename(
                    metadata.code, ImageType.SCREENSHOT, screenshot_url, index=i+1
                )
                screenshot_path = target_directory / screenshot_filename
                download_tasks.append(
                    self._download_single_image(screenshot_url, screenshot_path, ImageType.SCREENSHOT)
                )
        
        if not download_tasks:
            self.logger.warning(f"No images to download for {metadata.code}")
            return self._create_result(True, "No images available", {'downloaded_files': []})
        
        # Execute downloads concurrently
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # Process results
        downloaded_files = []
        failed_downloads = []
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Download task failed: {result}")
                failed_downloads.append(str(result))
            elif result and result.get('success'):
                downloaded_files.append(result['file_path'])
            else:
                failed_downloads.append(result.get('error', 'Unknown error'))
        
        success = len(downloaded_files) > 0
        message = f"Downloaded {len(downloaded_files)} images"
        if failed_downloads:
            message += f", {len(failed_downloads)} failed"
        
        return self._create_result(
            success,
            message,
            {
                'downloaded_files': downloaded_files,
                'failed_downloads': failed_downloads,
                'total_requested': len(download_tasks)
            }
        )
    
    async def _download_single_image(
        self,
        url: str,
        target_path: Path,
        image_type: ImageType
    ) -> Dict[str, Any]:
        """
        Download a single image with processing.
        
        Args:
            url: Image URL to download
            target_path: Target file path
            image_type: Type of image being downloaded
            
        Returns:
            Download result dictionary
        """
        async with self._download_semaphore:
            try:
                self.logger.debug(f"Downloading {image_type.value}: {url}")
                
                # Download image data
                image_data = await self._fetch_image_data(url)
                
                if not image_data:
                    return self._create_result(False, f"Failed to download {url}")
                
                # Process image if needed
                processed_data = await self._process_image_data(
                    image_data, target_path, image_type
                )
                
                # Save processed image
                await self._save_image_data(processed_data, target_path)
                
                # Create thumbnail if requested
                thumbnail_path = None
                if self.create_thumbnails and PIL_AVAILABLE:
                    thumbnail_path = await self._create_thumbnail(target_path)
                
                self.stats['images_downloaded'] += 1
                self.stats['total_bytes_downloaded'] += len(processed_data)
                
                result_data = {
                    'file_path': str(target_path),
                    'file_size': len(processed_data),
                    'image_type': image_type.value,
                    'source_url': url
                }
                
                if thumbnail_path:
                    result_data['thumbnail_path'] = str(thumbnail_path)
                
                self.logger.debug(f"Successfully downloaded: {target_path.name}")
                return self._create_result(True, "Download successful", result_data)
                
            except Exception as e:
                self.logger.error(f"Error downloading {url}: {e}")
                self.stats['download_failures'] += 1
                return self._create_result(False, f"Download error: {str(e)}")
    
    async def _fetch_image_data(self, url: str) -> Optional[bytes]:
        """
        Fetch image data from URL.
        
        Args:
            url: Image URL
            
        Returns:
            Image data bytes or None if failed
        """
        try:
            async with self.http_client as client:
                async with await client.get(url) as response:
                    if response.status != 200:
                        self.logger.warning(f"HTTP {response.status} for {url}")
                        return None
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'webp']):
                        self.logger.warning(f"Invalid content type {content_type} for {url}")
                        return None
                    
                    # Check content length
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_file_size_bytes:
                        self.logger.warning(f"Image too large: {content_length} bytes for {url}")
                        return None
                    
                    # Read image data
                    image_data = await response.read()
                    
                    # Check actual size
                    if len(image_data) > self.max_file_size_bytes:
                        self.logger.warning(f"Image too large: {len(image_data)} bytes for {url}")
                        return None
                    
                    return image_data
                    
        except Exception as e:
            self.logger.error(f"Error fetching image data from {url}: {e}")
            return None
    
    async def _process_image_data(
        self,
        image_data: bytes,
        target_path: Path,
        image_type: ImageType
    ) -> bytes:
        """
        Process image data (resize, convert format, etc.).
        
        Args:
            image_data: Original image data
            target_path: Target file path
            image_type: Type of image
            
        Returns:
            Processed image data
        """
        if not PIL_AVAILABLE:
            return image_data
        
        try:
            # Load image
            from io import BytesIO
            image = Image.open(BytesIO(image_data))
            
            # Convert to RGB if necessary (for JPEG conversion)
            if image.mode in ('RGBA', 'LA', 'P') and self.convert_format == ImageFormat.JPEG:
                # Create white background for transparency
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize image if needed
            if self._should_resize_image(image, image_type):
                image = self._resize_image(image)
                self.stats['images_resized'] += 1
            
            # Convert format if needed
            output_format = self._determine_output_format(target_path, image)
            
            # Save to bytes
            output_buffer = BytesIO()
            save_kwargs = {}
            
            if output_format.upper() == 'JPEG':
                save_kwargs['quality'] = self.jpeg_quality
                save_kwargs['optimize'] = True
            elif output_format.upper() == 'PNG':
                save_kwargs['optimize'] = True
            
            image.save(output_buffer, format=output_format, **save_kwargs)
            processed_data = output_buffer.getvalue()
            
            self.stats['images_processed'] += 1
            
            if len(processed_data) != len(image_data):
                self.stats['images_converted'] += 1
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            self.stats['processing_failures'] += 1
            return image_data  # Return original data on processing failure
    
    def _should_resize_image(self, image: 'Image.Image', image_type: ImageType) -> bool:
        """
        Determine if image should be resized.
        
        Args:
            image: PIL Image object
            image_type: Type of image
            
        Returns:
            True if image should be resized
        """
        if not self.resize_images:
            return False
        
        width, height = image.size
        
        # Different resize thresholds for different image types
        if image_type == ImageType.SCREENSHOT:
            # Screenshots can be larger
            return width > self.max_width * 1.5 or height > self.max_height * 1.5
        else:
            # Cover and poster images
            return width > self.max_width or height > self.max_height
    
    def _resize_image(self, image: 'Image.Image') -> 'Image.Image':
        """
        Resize image while maintaining aspect ratio.
        
        Args:
            image: PIL Image object
            
        Returns:
            Resized image
        """
        # Use PIL's thumbnail method which maintains aspect ratio
        image.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
        return image
    
    def _determine_output_format(self, target_path: Path, image: 'Image.Image') -> str:
        """
        Determine output format for image.
        
        Args:
            target_path: Target file path
            image: PIL Image object
            
        Returns:
            Output format string
        """
        if self.convert_format == ImageFormat.AUTO:
            # Keep original format based on file extension
            ext = target_path.suffix.lower()
            if ext in ['.jpg', '.jpeg']:
                return 'JPEG'
            elif ext == '.png':
                return 'PNG'
            elif ext == '.webp':
                return 'WEBP'
            else:
                # Default to JPEG for unknown extensions
                return 'JPEG'
        else:
            return self.convert_format.value.upper()
    
    async def _save_image_data(self, image_data: bytes, target_path: Path) -> None:
        """
        Save image data to file.
        
        Args:
            image_data: Image data to save
            target_path: Target file path
        """
        try:
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write image data
            with open(target_path, 'wb') as f:
                f.write(image_data)
                
        except Exception as e:
            self.logger.error(f"Error saving image to {target_path}: {e}")
            raise
    
    async def _create_thumbnail(self, image_path: Path) -> Optional[Path]:
        """
        Create thumbnail version of image.
        
        Args:
            image_path: Path to original image
            
        Returns:
            Path to thumbnail or None if failed
        """
        try:
            if not PIL_AVAILABLE:
                return None
            
            # Generate thumbnail path
            thumbnail_path = image_path.with_name(f"{image_path.stem}_thumb{image_path.suffix}")
            
            # Load and resize image
            with Image.open(image_path) as image:
                # Create thumbnail
                image.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                save_kwargs = {}
                if image_path.suffix.lower() in ['.jpg', '.jpeg']:
                    save_kwargs['quality'] = self.jpeg_quality
                    save_kwargs['optimize'] = True
                
                image.save(thumbnail_path, **save_kwargs)
            
            self.stats['thumbnails_created'] += 1
            self.logger.debug(f"Created thumbnail: {thumbnail_path.name}")
            
            return thumbnail_path
            
        except Exception as e:
            self.logger.error(f"Error creating thumbnail for {image_path}: {e}")
            return None
    
    def _generate_filename(
        self,
        code: str,
        image_type: ImageType,
        url: str,
        index: Optional[int] = None
    ) -> str:
        """
        Generate filename for downloaded image.
        
        Args:
            code: Movie code
            image_type: Type of image
            url: Source URL
            index: Optional index for multiple images of same type
            
        Returns:
            Generated filename
        """
        # Extract extension from URL
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Get extension from URL path
        original_ext = Path(path).suffix.lower()
        
        # Map common extensions
        ext_mapping = {
            '.jpg': '.jpg',
            '.jpeg': '.jpg',
            '.png': '.png',
            '.webp': '.webp',
            '.gif': '.jpg',  # Convert GIF to JPG
            '': '.jpg'  # Default extension
        }
        
        ext = ext_mapping.get(original_ext, '.jpg')
        
        # Override extension based on conversion format
        if self.convert_format == ImageFormat.JPEG:
            ext = '.jpg'
        elif self.convert_format == ImageFormat.PNG:
            ext = '.png'
        elif self.convert_format == ImageFormat.WEBP:
            ext = '.webp'
        
        # Generate base filename
        if image_type == ImageType.COVER:
            filename = f"{code}_cover{ext}"
        elif image_type == ImageType.POSTER:
            filename = f"{code}_poster{ext}"
        elif image_type == ImageType.SCREENSHOT:
            filename = f"{code}_screenshot_{index:02d}{ext}" if index else f"{code}_screenshot{ext}"
        else:
            filename = f"{code}_{image_type.value}{ext}"
        
        return filename
    
    def _create_result(self, success: bool, message: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create standardized result dictionary.
        
        Args:
            success: Whether operation was successful
            message: Result message
            data: Optional additional data
            
        Returns:
            Result dictionary
        """
        result = {
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if data:
            result.update(data)
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get download and processing statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'images_downloaded': self.stats['images_downloaded'],
            'images_processed': self.stats['images_processed'],
            'images_converted': self.stats['images_converted'],
            'images_resized': self.stats['images_resized'],
            'thumbnails_created': self.stats['thumbnails_created'],
            'download_failures': self.stats['download_failures'],
            'processing_failures': self.stats['processing_failures'],
            'total_bytes_downloaded': self.stats['total_bytes_downloaded'],
            'total_mb_downloaded': self.stats['total_bytes_downloaded'] / (1024 * 1024),
            'success_rate': (
                self.stats['images_downloaded'] / 
                max(1, self.stats['images_downloaded'] + self.stats['download_failures'])
            ) * 100
        }
    
    def reset_statistics(self) -> None:
        """Reset download statistics."""
        for key in self.stats:
            self.stats[key] = 0
        
        self.logger.info("Statistics reset")
    
    async def verify_image_integrity(self, image_path: Path) -> bool:
        """
        Verify image file integrity.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if image is valid, False otherwise
        """
        try:
            if not PIL_AVAILABLE:
                # Basic file existence check if PIL not available
                return image_path.exists() and image_path.stat().st_size > 0
            
            # Try to open and verify image
            with Image.open(image_path) as image:
                image.verify()  # Verify image integrity
                return True
                
        except Exception as e:
            self.logger.error(f"Image integrity check failed for {image_path}: {e}")
            return False
    
    async def cleanup_failed_downloads(self, directory: Path) -> Dict[str, Any]:
        """
        Clean up corrupted or incomplete image files.
        
        Args:
            directory: Directory to clean up
            
        Returns:
            Cleanup result dictionary
        """
        result = {
            'checked_files': 0,
            'corrupted_files': [],
            'removed_files': [],
            'errors': []
        }
        
        try:
            # Find image files
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(directory.glob(f"*{ext}"))
                image_files.extend(directory.glob(f"*{ext.upper()}"))
            
            # Check each image file
            for image_file in image_files:
                result['checked_files'] += 1
                
                try:
                    # Check file size
                    if image_file.stat().st_size == 0:
                        result['corrupted_files'].append(str(image_file))
                        continue
                    
                    # Verify image integrity
                    if not await self.verify_image_integrity(image_file):
                        result['corrupted_files'].append(str(image_file))
                        
                except Exception as e:
                    result['errors'].append(f"Error checking {image_file}: {e}")
            
            # Remove corrupted files
            for corrupted_file in result['corrupted_files']:
                try:
                    Path(corrupted_file).unlink()
                    result['removed_files'].append(corrupted_file)
                    self.logger.info(f"Removed corrupted image: {corrupted_file}")
                except Exception as e:
                    result['errors'].append(f"Error removing {corrupted_file}: {e}")
            
        except Exception as e:
            result['errors'].append(f"Error during cleanup: {e}")
        
        self.logger.info(f"Cleanup completed: {len(result['removed_files'])} files removed")
        return result