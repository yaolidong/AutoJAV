#!/usr/bin/env python3
"""
API Server for AV Metadata Scraper
Provides REST API for scraping operations
Refactored to be thread-safe by creating scraper instances per request.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

from src.config.config_manager import ConfigManager
from src.models.video_file import VideoFile
from src.scanner.file_scanner import FileScanner
from src.scrapers.scraper_factory import ScraperFactory
from src.organizers.file_organizer import FileOrganizer, ConflictResolution
from src.utils.logging_config import setup_application_logging
from src.utils.history_manager import HistoryManager

# Setup logging at the application level
setup_application_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# --- Global components that are safe to share ---
config_manager = ConfigManager()
history_manager = HistoryManager(history_file=config_manager.get_config_data().get('directories', {}).get('history_file', '/app/logs/scrape_history.json'))


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'av-metadata-scraper-api',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/scrape', methods=['POST'])
def scrape_metadata_endpoint():
    """Scrape metadata for a single file. This endpoint is now thread-safe."""
    metadata_scraper = None  # Ensure scraper is defined for the finally block
    try:
        # --- Per-request instance creation for thread safety ---
        logger.info("Creating new scraper and organizer instances for this request.")
        config_data = config_manager.load_config()
        scraper_factory = ScraperFactory(config=config_data)
        metadata_scraper = scraper_factory.create_metadata_scraper()
        
        directories_config = config_data.get('directories', {})
        organization_config = config_data.get('organization', {})
        file_organizer = FileOrganizer(
            target_directory=directories_config.get('target', '/app/target'),
            naming_pattern=organization_config.get('naming_pattern', '{actress}/{code}/{code}.{ext}'),
            conflict_resolution=ConflictResolution(organization_config.get('conflict_resolution', 'rename')),
            create_metadata_files=organization_config.get('create_metadata_files', True),
            safe_mode=False,
            move_source_files=True
        )
        # --- End of per-request instance creation ---

        data = request.json
        file_path_str = data.get('file_path')
        code = data.get('code')

        if not code and not file_path_str:
            return jsonify({'success': False, 'error': 'No code or file path provided'}), 400

        file_path = Path(file_path_str) if file_path_str else None

        if file_path and not code:
            scanner = FileScanner(source_directory=str(file_path.parent), supported_formats=[file_path.suffix])
            code = scanner.extract_code_from_filename(file_path.name)

        if not code:
            return jsonify({'success': False, 'error': 'Could not detect code from file'}), 400

        # --- New logic to find file_path if only code is provided ---
        if not file_path and code:
            logger.info(f"File path not provided. Searching for file with code '{code}' in source directory...")
            source_dir = directories_config.get('source', '/app/source')
            scanner = FileScanner(source_directory=source_dir, supported_formats=config_data.get('supported_extensions', ['.mp4', '.mkv']))
            found_files = scanner.scan_directory()
            logger.info(f"Scanner found the following files: {[f.filename for f in found_files]}")
            for f in found_files:
                if code.lower() in f.filename.lower():
                    file_path = f.file_path
                    logger.info(f"Found matching file: {file_path}")
                    break
        # --- End of new logic ---

        logger.info(f"API: Scraping metadata for code: {code}")
        
        metadata = asyncio.run(metadata_scraper.scrape_metadata(code))

        if metadata:
            logger.info(f"API: Successfully scraped metadata for {code}")
            
            if file_path and file_path.exists():
                # Create VideoFile instance from path
                file_stat = file_path.stat()
                video_file = VideoFile(
                    file_path=str(file_path),
                    filename=file_path.name,
                    file_size=file_stat.st_size,
                    extension=file_path.suffix,
                    detected_code=code
                )
                
                logger.info(f"Organizing file: {file_path_str}")
                result = file_organizer.organize_file(video_file, metadata)
                
                if result.get('success'):
                    # Get details from the correct field
                    details = result.get('details', {})
                    target_path = details.get('target_path', '')
                    logger.info(f"Successfully organized file to: {target_path}")
                    history_manager.record_success(
                        original_filename=video_file.filename,
                        original_path=str(video_file.file_path),
                        file_size=video_file.file_size,
                        file_extension=video_file.extension,
                        detected_code=code,
                        new_filename=Path(target_path).name if target_path else '',
                        new_path=target_path,
                        metadata=metadata.to_dict(),
                        scraper_used=getattr(metadata, 'source', 'Unknown')
                    )
                    # Add data field for frontend compatibility
                    result['data'] = details
                else:
                    # Check if it's due to invalid actress
                    details = result.get('details', {})
                    if details.get('reason') == 'invalid_actress':
                        logger.warning(f"File kept in original location due to invalid actress: {video_file.filename}")
                        error_message = "No valid actress information - file preserved in original location"
                    else:
                        error_message = result.get('message', result.get('error', 'Unknown organization error'))
                    logger.error(f"Failed to organize file: {error_message}")
                    history_manager.record_failure(
                        original_filename=video_file.filename,
                        original_path=str(video_file.file_path),
                        file_size=video_file.file_size,
                        file_extension=video_file.extension,
                        detected_code=code,
                        error_message=error_message
                    )
                
                return jsonify(result)
            
            return jsonify({'success': True, 'metadata': metadata.to_dict()})
        else:
            logger.warning(f"API: No metadata found for {code}")
            if file_path and file_path.exists():
                file_stat = file_path.stat()
                history_manager.record_failure(
                    original_filename=file_path.name,
                    original_path=file_path_str,
                    file_size=file_stat.st_size,
                    file_extension=file_path.suffix,
                    detected_code=code,
                    error_message=f'No metadata found for {code}'
                )
            return jsonify({'success': False, 'error': f'No metadata found for {code}'})
            
    except Exception as e:
        logger.error(f"API scraping error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Ensure the webdriver is always cleaned up
        if metadata_scraper:
            logger.info("Cleaning up scraper resources from API request...")
            asyncio.run(metadata_scraper.cleanup())


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get scraping history"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get history from history manager - use get_recent_entries with a large limit
        all_history = history_manager.get_recent_entries(limit=10000)
        
        # Convert entries to dict format
        history_dicts = [entry.to_dict() for entry in all_history]
        
        # Apply pagination
        total = len(history_dicts)
        paginated = history_dicts[offset:offset + limit]
        
        return jsonify({
            'success': True,
            'data': paginated,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history/stats', methods=['GET'])
def get_history_stats():
    """Get history statistics"""
    try:
        stats = history_manager.get_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error getting history stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear history records"""
    try:
        # Optional: filter by date or type
        data = request.json or {}
        days = data.get('days', 0)
        
        if days > 0:
            # Clear history older than specified days
            cleared_count = history_manager.clear_old_entries(days)
            return jsonify({
                'success': True,
                'message': f'Cleared {cleared_count} old entries'
            })
        else:
            # Clear all history by setting to empty list and saving
            history_manager.history = []
            history_manager.save_history()
            return jsonify({
                'success': True,
                'message': 'All history cleared successfully'
            })
        
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/history/export', methods=['GET'])
def export_history():
    """Export history as JSON"""
    try:
        # Get all history entries
        all_history = history_manager.get_recent_entries(limit=10000)
        
        # Convert to dict format
        history_data = [entry.to_dict() for entry in all_history]
        
        # Create response with proper headers for download
        response = jsonify(history_data)
        response.headers['Content-Disposition'] = 'attachment; filename=history.json'
        return response
    except Exception as e:
        logger.error(f"Error exporting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def run_api_server(host='0.0.0.0', port=5555):
    """Run the API server"""
    logger.info(f"Starting API server on {host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    run_api_server()
