#!/usr/bin/env python3
"""
Test script for file scanner functionality.

This script demonstrates how to use the FileScanner to scan directories.
"""

import sys
import argparse
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.scanner.file_scanner import FileScanner


def main():
    """Main function for scanner testing."""
    parser = argparse.ArgumentParser(description='Test AV file scanner')
    parser.add_argument(
        'directory',
        type=str,
        help='Directory to scan for video files'
    )
    parser.add_argument(
        '--extensions', '-e',
        nargs='+',
        default=['.mp4', '.mkv', '.avi', '.wmv', '.mov'],
        help='Video file extensions to scan for'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--show-codes', '-c',
        action='store_true',
        help='Show detected codes'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize scanner
        scanner = FileScanner(args.directory, args.extensions)
        
        print(f"Scanning directory: {args.directory}")
        print(f"Supported extensions: {', '.join(args.extensions)}")
        print()
        
        # Scan for video files
        video_files = scanner.scan_directory()
        
        if not video_files:
            print("No video files found.")
            return 0
        
        # Show results
        print(f"Found {len(video_files)} video files:")
        print()
        
        for i, video_file in enumerate(video_files, 1):
            print(f"{i:3d}. {video_file.filename}")
            
            if args.verbose:
                print(f"     Path: {video_file.file_path}")
                print(f"     Size: {video_file.size_mb:.1f} MB")
                print(f"     Extension: {video_file.extension}")
            
            if args.show_codes or args.verbose:
                if video_file.detected_code:
                    print(f"     Code: {video_file.detected_code}")
                else:
                    print(f"     Code: Not detected")
            
            if args.verbose:
                print()
        
        # Show statistics
        stats = scanner.get_scan_statistics(video_files)
        print("\nScan Statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Total size: {stats['total_size_mb']:.1f} MB")
        print(f"  Average size: {stats['average_size_mb']:.1f} MB")
        print(f"  Files with codes: {stats['files_with_codes']}")
        print(f"  Files without codes: {stats['files_without_codes']}")
        
        if stats['extensions']:
            print(f"  Extensions found:")
            for ext, count in sorted(stats['extensions'].items()):
                print(f"    {ext}: {count} files")
        
        return 0
        
    except FileNotFoundError:
        print(f"Error: Directory not found: {args.directory}")
        return 1
    except PermissionError:
        print(f"Error: Permission denied accessing: {args.directory}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())