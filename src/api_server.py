#!/usr/bin/env python3
"""
API Server for AV Metadata Scraper
Provides REST API for scraping operations
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import queue

from src.config.config_manager import ConfigManager
from src.scanner.file_scanner import FileScanner
from src.scrapers.scraper_factory import ScraperFactory
from src.scrapers.parallel_metadata_scraper import ParallelMetadataScraper
from src.organizers.file_organizer import FileOrganizer, ConflictResolution
from src.downloaders.image_downloader import ImageDownloader, ImageType
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata
from src.models.scrape_history import ProcessStatus
from src.utils.logging_config import setup_application_logging
from src.utils.history_manager import HistoryManager
from src.utils.vnc_login_manager import VNCLoginManager

# Setup logging
setup_application_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-container communication

# Global variables
config_manager = None
scraper_factory = None
file_organizer = None
parallel_scraper = None
history_manager = None
image_downloader = None
vnc_login_manager = None # Global VNC manager instance
task_queue = queue.Queue()
current_task = None

def initialize_components():
    """Initialize scraper components"""
    global config_manager, scraper_factory, file_organizer, parallel_scraper, history_manager, image_downloader, vnc_login_manager
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config_data = config_manager.load_config()
        
        # Create scraper factory
        scraper_factory = ScraperFactory(config=config_data)
        
        # Create parallel scraper for faster metadata retrieval
        parallel_scraper = scraper_factory.create_parallel_metadata_scraper()
        
        # Get configuration sections
        directories_config = config_data.get('directories', {})
        organization_config = config_data.get('organization', {})
        
        # Create file organizer with move mode (not safe mode)
        file_organizer = FileOrganizer(
            target_directory=directories_config.get('target', '/app/target'),
            naming_pattern=organization_config.get('naming_pattern', '{actress}/{code}/{code}.{ext}'),
            conflict_resolution=ConflictResolution(organization_config.get('conflict_resolution', 'rename')),
            create_metadata_files=organization_config.get('create_metadata_files', True),
            safe_mode=False,  # Move files instead of copying
            move_source_files=True  # Enable source file deletion after successful move
        )
        
        # Initialize history manager
        history_file = directories_config.get('history_file', '/app/logs/scrape_history.json')
        history_manager = HistoryManager(history_file=history_file)
        
        # Initialize image downloader
        downloader_config = config_data.get('downloader', {})
        image_downloader = ImageDownloader(
            max_concurrent_downloads=downloader_config.get('max_concurrent', 3),
            timeout_seconds=downloader_config.get('timeout', 30),
            resize_images=downloader_config.get('resize_images', False),
            create_thumbnails=downloader_config.get('create_thumbnails', False)
        )

        # Initialize VNC Login Manager
        vnc_login_manager = VNCLoginManager(config_dir='/app/config')
        
        logger.info("API server components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'av-metadata-scraper-api',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/scrape', methods=['POST'])
def scrape_metadata():
    """Scrape metadata for a single file"""
    try:
        data = request.json
        file_path = data.get('file_path')
        code = data.get('code')
        
        if not code and not file_path:
            return jsonify({'success': False, 'error': 'No code or file path provided'}), 400
        
        # If file path is provided, extract code from filename if not provided
        if file_path and not code:
            video_file = VideoFile(
                file_path=file_path,
                filename=Path(file_path).name,
                file_size=0,
                extension=Path(file_path).suffix
            )
            code = video_file.detected_code
            
        if not code:
            return jsonify({'success': False, 'error': 'Could not detect code from file'}), 400
        
        logger.info(f"API: Scraping metadata for code: {code}")
        
        # Use parallel scraper for faster results
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            metadata = loop.run_until_complete(
                parallel_scraper.scrape_metadata_parallel(code)
            )
        finally:
            loop.close()
        
        if metadata:
            logger.info(f"API: Successfully scraped metadata for {code}")
            
            # If file path is provided, organize the file
            if file_path and Path(file_path).exists():
                # Check if we have valid actresses
                invalid_names = ['Censored', 'censored', 'CENSORED', 'Uncensored', 'uncensored', 'UNCENSORED', 'Western', 'western', '暂无', '未知', 'Unknown', 'N/A', '-', '---', '']
                
                scraping_successful = False
                if metadata.actresses:
                    valid_actresses = [a for a in metadata.actresses if a and a not in invalid_names]
                    if valid_actresses:
                        metadata.actresses = valid_actresses
                        scraping_successful = True
                        
                if scraping_successful:
                    # Create VideoFile object
                    video_file = VideoFile(
                        file_path=file_path,
                        filename=Path(file_path).name,
                        file_size=Path(file_path).stat().st_size if Path(file_path).exists() else 0,
                        extension=Path(file_path).suffix,
                        detected_code=code
                    )
                    
                    # Organize file
                    result = file_organizer.organize_file(video_file, metadata)
                    
                    # Download images if organization was successful
                    if result.get('success'):
                        target_path = result.get('data', {}).get('target_path')
                        if target_path:
                            target_dir = Path(target_path).parent
                            
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                download_result = loop.run_until_complete(
                                    image_downloader.download_movie_images(
                                        metadata,
                                        target_dir,
                                        download_types=[ImageType.COVER, ImageType.POSTER]
                                    )
                                )
                                
                                if download_result['success']:
                                    logger.info(f"Downloaded {download_result['downloaded_count']} images for {code}")
                            except Exception as img_error:
                                logger.error(f"Failed to download images: {img_error}")
                            finally:
                                loop.close()
                    
                    # Record in history
                    if result.get('success'):
                        history_manager.record_success(
                            original_filename=Path(file_path).name,
                            original_path=file_path,
                            file_size=Path(file_path).stat().st_size if Path(file_path).exists() else 0,
                            file_extension=Path(file_path).suffix,
                            detected_code=code,
                            new_filename=Path(result.get('data', {}).get('target_path', file_path)).name,
                            new_path=result.get('data', {}).get('target_path', file_path),
                            metadata={
                                'code': metadata.code,
                                'title': metadata.title,
                                'actresses': metadata.actresses,
                                'release_date': metadata.release_date.isoformat() if metadata.release_date else None,
                                'studio': metadata.studio,
                                'genres': metadata.genres,
                                'cover_downloaded': True
                            },
                            scraper_used='Multiple'
                        )
                    else:
                        history_manager.record_failure(
                            original_filename=Path(file_path).name,
                            original_path=file_path,
                            file_size=Path(file_path).stat().st_size if Path(file_path).exists() else 0,
                            file_extension=Path(file_path).suffix,
                            detected_code=code,
                            error_message=result.get('error', 'Unknown error')
                        )
                    
                    return jsonify({
                        'success': True,
                        'organized': True,
                        'target_path': result.get('data', {}).get('target_path'),
                        'metadata': {
                            'code': metadata.code,
                            'title': metadata.title,
                            'title_en': metadata.title_en,
                            'actresses': metadata.actresses,
                            'release_date': metadata.release_date.isoformat() if metadata.release_date else None,
                            'duration': metadata.duration,
                            'studio': metadata.studio,
                            'series': metadata.series,
                            'genres': metadata.genres,
                            'cover_url': metadata.cover_url,
                            'poster_url': metadata.poster_url,
                            'screenshots': metadata.screenshots,
                            'description': metadata.description,
                            'rating': metadata.rating
                        }
                    })
                else:
                    # Scraping failed - file stays in source
                    logger.warning(f"No valid actresses found for {code}, file remains in source")
                    # Record as partial success
                    history_manager.record_success(
                        original_filename=Path(file_path).name,
                        original_path=file_path,
                        file_size=Path(file_path).stat().st_size if Path(file_path).exists() else 0,
                        file_extension=Path(file_path).suffix,
                        detected_code=code,
                        new_filename=Path(file_path).name,
                        new_path=file_path,
                        metadata={
                            'code': metadata.code,
                            'title': metadata.title,
                            'actresses': metadata.actresses,
                            'release_date': metadata.release_date.isoformat() if metadata.release_date else None,
                            'studio': metadata.studio,
                            'genres': metadata.genres,
                            'cover_downloaded': False
                        },
                        scraper_used='Multiple'
                    )
                    
            return jsonify({
                'success': True,
                'organized': False,
                'metadata': {
                    'code': metadata.code,
                    'title': metadata.title,
                    'title_en': metadata.title_en,
                    'actresses': metadata.actresses,
                    'release_date': metadata.release_date.isoformat() if metadata.release_date else None,
                    'duration': metadata.duration,
                    'studio': metadata.studio,
                    'series': metadata.series,
                    'genres': metadata.genres,
                    'cover_url': metadata.cover_url,
                    'poster_url': metadata.poster_url,
                    'screenshots': metadata.screenshots,
                    'description': metadata.description,
                    'rating': metadata.rating
                }
            })
        else:
            logger.warning(f"API: No metadata found for {code}")
            # Record failure in history
            if file_path:
                history_manager.record_failure(
                    original_filename=Path(file_path).name,
                    original_path=file_path,
                    file_size=Path(file_path).stat().st_size if Path(file_path).exists() else 0,
                    file_extension=Path(file_path).suffix,
                    detected_code=code,
                    error_message=f'No metadata found for {code}'
                )
            return jsonify({
                'success': False,
                'error': f'No metadata found for {code}'
            })
            
    except Exception as e:
        logger.error(f"API scraping error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_files():
    """Process a batch of files"""
    try:
        data = request.json
        files = data.get('files', [])
        
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        logger.info(f"API: Processing {len(files)} files")
        
        results = []
        successful_moves = []
        failed_files = []
        
        for file_info in files:
            try:
                # Extract file information
                file_path = Path(file_info['path'])
                filename = file_info.get('filename', file_path.name)
                extension = file_path.suffix
                
                # Create VideoFile object with required parameters
                video_file = VideoFile(
                    file_path=str(file_path),
                    filename=filename,
                    file_size=file_info.get('size', 0),
                    extension=extension,
                    detected_code=file_info.get('detected_code')
                )
                
                # Scrape metadata using parallel scraper if code is detected
                metadata = None
                if video_file.detected_code:
                    logger.info(f"API: Parallel scraping metadata for {video_file.detected_code}")
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        metadata = loop.run_until_complete(
                            parallel_scraper.scrape_metadata_parallel(video_file.detected_code)
                        )
                    finally:
                        loop.close()
                
                # Check if we have valid metadata and actresses
                scraping_successful = False
                
                if metadata:
                    # Filter out invalid actress names
                    invalid_names = ['Censored', 'censored', 'CENSORED', 'Uncensored', 'uncensored', 'UNCENSORED', 'Western', 'western', '暂无', '未知', 'Unknown', 'N/A', '-', '---', '']
                    
                    if metadata.actresses:
                        valid_actresses = [a for a in metadata.actresses if a and a not in invalid_names]
                        
                        # If we have valid actresses, use them
                        if valid_actresses:
                            metadata.actresses = valid_actresses
                            scraping_successful = True
                            logger.info(f"Found valid actresses for {video_file.detected_code}: {valid_actresses}")
                        else:
                            # No valid actresses found
                            logger.warning(f"No valid actresses found for {video_file.detected_code}, keeping file in source")
                    else:
                        logger.warning(f"No actresses data for {video_file.detected_code}, keeping file in source")
                else:
                    logger.warning(f"No metadata found for {video_file.detected_code}, keeping file in source")
                
                # Only organize file if scraping was successful
                if scraping_successful:
                    # Organize file (will move from source to target)
                    result = file_organizer.organize_file(video_file, metadata)
                    
                    # If file was successfully organized, download cover images
                    if result.get('success') and metadata:
                        target_path = result.get('data', {}).get('target_path')
                        if target_path:
                            # Get the directory where the file was organized
                            target_dir = Path(target_path).parent
                            
                            # Download cover images asynchronously
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                # Download cover, poster, and screenshots
                                download_result = loop.run_until_complete(
                                    image_downloader.download_movie_images(
                                        metadata,
                                        str(target_dir),
                                        [ImageType.COVER, ImageType.POSTER, ImageType.SCREENSHOT]
                                    )
                                )
                                
                                loop.close()
                                
                                if download_result.get('success'):
                                    logger.info(f"Downloaded {download_result.get('downloaded_count', 0)} images for {video_file.detected_code}")
                                    result['cover_downloaded'] = True
                                    result['images_downloaded'] = download_result.get('downloaded_count', 0)
                                else:
                                    logger.warning(f"Failed to download images for {video_file.detected_code}")
                                    result['cover_downloaded'] = False
                                    
                            except Exception as e:
                                logger.error(f"Error downloading images for {video_file.detected_code}: {e}")
                                result['cover_downloaded'] = False
                else:
                    # Don't move the file, keep it in source
                    result = {
                        'success': False,
                        'message': 'Scraping failed or no valid actress found, file kept in source folder'
                    }
                
                file_result = {
                    'file': file_info['filename'],
                    'success': result['success'],
                    'message': result.get('message', ''),
                    'original_path': str(video_file.file_path),
                    'new_path': result.get('data', {}).get('target_path', '') if result.get('success') else '',
                    'metadata': {
                        'code': metadata.code if metadata else video_file.detected_code,
                        'title': metadata.title if metadata else 'N/A',
                        'actresses': metadata.actresses if metadata else [],
                        'studio': metadata.studio if metadata else 'N/A',
                        'sources': list(metadata.source_urls.keys()) if metadata and hasattr(metadata, 'source_urls') else [],
                        'cover_downloaded': result.get('cover_downloaded', False),
                        'images_downloaded': result.get('images_downloaded', 0)
                    }
                }
                
                results.append(file_result)
                
                # Record history
                if history_manager:
                    if result['success']:
                        history_manager.record_success(
                            original_filename=file_info['filename'],
                            original_path=str(video_file.file_path),
                            file_size=file_info.get('size', 0),
                            file_extension=file_path.suffix,
                            detected_code=video_file.detected_code,
                            new_filename=Path(result.get('data', {}).get('target_path', '')).name if result.get('data', {}).get('target_path') else file_info['filename'],
                            new_path=result.get('data', {}).get('target_path', ''),
                            metadata={
                                'title': metadata.title if metadata else 'N/A',
                                'actresses': metadata.actresses if metadata else [],
                                'studio': metadata.studio if metadata else 'N/A',
                                'release_date': str(metadata.release_date) if metadata and metadata.release_date else None,
                                'genres': metadata.genres if metadata and hasattr(metadata, 'genres') else [],
                                'cover_downloaded': result.get('cover_downloaded', False)
                            },
                            scraper_used='Multiple' if metadata else 'None'
                        )
                    else:
                        history_manager.record_failure(
                            original_filename=file_info['filename'],
                            original_path=str(video_file.file_path),
                            file_size=file_info.get('size', 0),
                            file_extension=file_path.suffix,
                            detected_code=video_file.detected_code,
                            error_message=result.get('message', 'Scraping failed - file kept in source')
                        )
                
                if result['success']:
                    successful_moves.append(file_info['filename'])
                    logger.info(f"Successfully moved {file_info['filename']} to target directory")
                else:
                    failed_files.append(file_info['filename'])
                
            except Exception as e:
                logger.error(f"API: Error processing {file_info.get('filename')}: {e}")
                results.append({
                    'file': file_info.get('filename'),
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'successful': len(successful_moves),
            'failed': len(failed_files),
            'successful_files': successful_moves,
            'failed_files': failed_files,
            'message': f"Moved {len(successful_moves)} files from source to target"
        })
        
    except Exception as e:
        logger.error(f"API processing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scan', methods=['POST'])
def scan_directory():
    """Scan directory for video files"""
    try:
        data = request.json
        directory = data.get('directory', '/app/source')
        
        logger.info(f"API: Scanning directory: {directory}")
        
        # Get supported formats from config
        config = config_manager.get_config_data()
        supported_formats = config.get('supported_extensions', [
            '.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v', '.ts', '.m2ts'
        ])
        
        # Create scanner
        scanner = FileScanner(directory, supported_formats)
        video_files = scanner.scan_directory()
        
        # Convert to JSON-serializable format
        files = []
        for vf in video_files:
            files.append({
                'filename': vf.filename,
                'path': str(vf.file_path),
                'extension': vf.extension,
                'size_mb': vf.size_mb,
                'detected_code': vf.detected_code
            })
        
        return jsonify({
            'success': True,
            'directory': directory,
            'total': len(files),
            'files': files
        })
        
    except Exception as e:
        logger.error(f"API scanning error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current processing status"""
    return jsonify({
        'success': True,
        'current_task': current_task,
        'queue_size': task_queue.qsize()
    })

@app.route('/api/javdb/vnc_login', methods=['POST'])
def javdb_vnc_login():
    """Manages JAVDB login via a VNC session."""
    global vnc_login_manager
    if not vnc_login_manager:
        return jsonify({'success': False, 'error': 'VNC Login Manager not initialized'}), 500

    try:
        data = request.json or {}
        action = data.get('action', 'start')

        if action == 'start':
            result = vnc_login_manager.start_login_session()
            return jsonify(result)
        
        elif action == 'check':
            result = vnc_login_manager.check_and_save_cookies()
            return jsonify(result)

        else:
            return jsonify({'success': False, 'error': f'Unknown action: {action}'})

    except Exception as e:
        logger.error(f"VNC login operation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get scraping history"""
    try:
        if not history_manager:
            return jsonify({'success': False, 'error': 'History manager not initialized'}), 500
        
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        status = request.args.get('status')
        search = request.args.get('search')
        
        # Get history entries
        if search:
            entries = history_manager.search_entries(search)
        elif status:
            try:
                status_enum = ProcessStatus(status)
                entries = history_manager.get_entries_by_status(status_enum)
            except ValueError:
                entries = history_manager.get_recent_entries(limit)
        else:
            entries = history_manager.get_recent_entries(limit)
        
        # Convert to JSON format
        history_data = [entry.to_dict() for entry in entries]
        
        return jsonify({
            'success': True,
            'total': len(history_data),
            'entries': history_data
        })
        
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/stats', methods=['GET'])
def get_history_stats():
    """Get history statistics"""
    try:
        if not history_manager:
            return jsonify({'success': False, 'error': 'History manager not initialized'}), 500
        
        stats = history_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting history stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/clear', methods=['POST'])
def clear_old_history():
    """Clear old history entries"""
    try:
        if not history_manager:
            return jsonify({'success': False, 'error': 'History manager not initialized'}), 500
        
        data = request.json
        days = data.get('days', 90)
        
        removed = history_manager.clear_old_entries(days)
        
        return jsonify({
            'success': True,
            'removed': removed,
            'message': f'Removed {removed} entries older than {days} days'
        })
        
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history/export', methods=['GET'])
def export_history():
    """Export history to CSV"""
    try:
        if not history_manager:
            return jsonify({'success': False, 'error': 'History manager not initialized'}), 500
        
        # Create export file
        export_file = '/app/logs/history_export.csv'
        history_manager.export_to_csv(export_file)
        
        # Return file for download
        from flask import send_file
        return send_file(export_file, as_attachment=True, download_name='scrape_history.csv')
        
    except Exception as e:
        logger.error(f"Error exporting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def run_api_server(host='0.0.0.0', port=5555):
    """Run the API server"""
    logger.info(f"Starting API server on {host}:{port}")
    
    # Initialize components
    if not initialize_components():
        logger.error("Failed to initialize components, exiting")
        return
    
    # Run Flask app
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    run_api_server()