#!/usr/bin/env python3
"""
CLI Usage Examples for AV Metadata Scraper

This script demonstrates various ways to use the CLI interface.
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.cli import AVScraperCLI


async def example_basic_usage():
    """Example of basic CLI usage."""
    print("=== Basic CLI Usage Examples ===\n")
    
    cli = AVScraperCLI()
    
    # Example 1: Show help
    print("1. Showing help:")
    print("   Command: av-scraper --help")
    result = await cli.run(["--help"])
    print(f"   Result: Exit code {result}\n")
    
    # Example 2: Configuration wizard (simulated)
    print("2. Configuration wizard:")
    print("   Command: av-scraper config wizard")
    print("   This would start an interactive configuration setup\n")
    
    # Example 3: Scan directory
    print("3. Scan directory:")
    print("   Command: av-scraper scan --source /path/to/videos")
    print("   This would scan for video files without processing them\n")
    
    # Example 4: Process files
    print("4. Process files:")
    print("   Command: av-scraper process --dry-run")
    print("   This would show what would be done without making changes\n")


async def example_advanced_usage():
    """Example of advanced CLI usage."""
    print("=== Advanced CLI Usage Examples ===\n")
    
    # Example 1: Custom configuration
    print("1. Using custom configuration:")
    print("   Command: av-scraper process --config /path/to/config.yaml")
    print("   This uses a specific configuration file\n")
    
    # Example 2: Detailed scanning
    print("2. Detailed file scanning:")
    print("   Command: av-scraper scan --show-codes --show-sizes --format table")
    print("   This shows detected codes and file sizes in table format\n")
    
    # Example 3: Processing with options
    print("3. Processing with custom options:")
    print("   Command: av-scraper process --max-concurrent 5 --skip-images")
    print("   This processes with 5 concurrent workers and skips image downloads\n")
    
    # Example 4: Monitoring
    print("4. Monitoring application:")
    print("   Command: av-scraper status --watch")
    print("   This continuously monitors the application status\n")
    
    # Example 5: Testing
    print("5. Testing connectivity:")
    print("   Command: av-scraper test scrapers")
    print("   This tests scraper connectivity and functionality\n")


async def example_configuration_management():
    """Example of configuration management."""
    print("=== Configuration Management Examples ===\n")
    
    # Example 1: Show configuration
    print("1. Show current configuration:")
    print("   Command: av-scraper config show")
    print("   This displays the current configuration\n")
    
    # Example 2: Validate configuration
    print("2. Validate configuration:")
    print("   Command: av-scraper config validate")
    print("   This checks if the configuration is valid\n")
    
    # Example 3: Set configuration value
    print("3. Set configuration value:")
    print("   Command: av-scraper config set scrapers.priority=javlibrary,javdb")
    print("   This changes the scraper priority order\n")
    
    # Example 4: Generate template
    print("4. Generate configuration template:")
    print("   Command: av-scraper config template --type advanced --output config.yaml")
    print("   This creates an advanced configuration template\n")


async def example_workflow():
    """Example of a complete workflow."""
    print("=== Complete Workflow Example ===\n")
    
    workflow_steps = [
        ("1. Setup", "av-scraper config wizard"),
        ("2. Test", "av-scraper test all"),
        ("3. Scan", "av-scraper scan --source /videos --show-codes"),
        ("4. Dry Run", "av-scraper process --dry-run"),
        ("5. Process", "av-scraper process"),
        ("6. Monitor", "av-scraper status"),
        ("7. Statistics", "av-scraper stats --detailed")
    ]
    
    print("Typical workflow for new users:")
    for step, command in workflow_steps:
        print(f"   {step}: {command}")
    
    print("\nThis workflow covers:")
    print("   - Initial configuration setup")
    print("   - System testing and validation")
    print("   - File discovery and preview")
    print("   - Safe processing with dry run")
    print("   - Actual file processing")
    print("   - Monitoring and statistics")


async def example_docker_usage():
    """Example of Docker usage with CLI."""
    print("=== Docker Usage Examples ===\n")
    
    docker_commands = [
        ("Build image", "docker build -t av-scraper ."),
        ("Run wizard", "docker run -it av-scraper av-scraper config wizard"),
        ("Process files", "docker run -v /videos:/app/source -v /organized:/app/target av-scraper"),
        ("Check status", "docker exec av-scraper av-scraper status"),
        ("View logs", "docker logs av-scraper")
    ]
    
    print("Using CLI with Docker:")
    for description, command in docker_commands:
        print(f"   {description}:")
        print(f"     {command}\n")


async def main():
    """Run all CLI usage examples."""
    print("🎬 AV Metadata Scraper CLI Usage Examples")
    print("=" * 50)
    
    await example_basic_usage()
    await example_advanced_usage()
    await example_configuration_management()
    await example_workflow()
    await example_docker_usage()
    
    print("For more information, run: av-scraper --help")
    print("Or visit the documentation for detailed guides.")


if __name__ == "__main__":
    asyncio.run(main())