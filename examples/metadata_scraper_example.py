#!/usr/bin/env python3
"""Example usage of the MetadataScraper coordinator."""

import asyncio
import logging
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import required modules
from src.scrapers.scraper_factory import ScraperFactory
from src.utils.webdriver_manager import WebDriverManager
from src.utils.http_client import HttpClient


async def basic_usage_example():
    """Demonstrate basic usage of MetadataScraper."""
    print("=== Basic MetadataScraper Usage Example ===\n")
    
    # Create factory with default configuration
    factory = ScraperFactory()
    
    # Create MetadataScraper with all available scrapers
    try:
        metadata_scraper = factory.create_metadata_scraper()
        print(f"Created MetadataScraper with {len(metadata_scraper.scrapers)} scrapers")
        
        # Get available scrapers
        available_scrapers = metadata_scraper.get_available_scrapers()
        print(f"Available scrapers: {available_scrapers}")
        
        # Scrape metadata for a single movie code
        print("\n--- Scraping single movie ---")
        movie_code = "SSIS-001"
        metadata = await metadata_scraper.scrape_metadata(movie_code)
        
        if metadata:
            print(f"Successfully scraped metadata for {movie_code}:")
            print(f"  Title: {metadata.title}")
            print(f"  Actresses: {', '.join(metadata.actresses)}")
            print(f"  Release Date: {metadata.release_date}")
            print(f"  Studio: {metadata.studio}")
            print(f"  Source: {metadata.source_url}")
        else:
            print(f"Failed to scrape metadata for {movie_code}")
        
        # Get statistics
        stats = metadata_scraper.get_scraper_stats()
        print(f"\nStatistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Scraper usage: {stats['scraper_usage']}")
        
    except Exception as e:
        print(f"Error creating MetadataScraper: {e}")


async def batch_scraping_example():
    """Demonstrate batch scraping with MetadataScraper."""
    print("\n=== Batch Scraping Example ===\n")
    
    # Configuration for batch processing
    config = {
        'coordinator': {
            'max_concurrent_requests': 2,  # Limit concurrent requests
            'timeout_seconds': 30,
            'retry_attempts': 1
        },
        'scrapers': {
            'javdb': {'enabled': True, 'use_login': False},  # Disable login for demo
            'javlibrary': {'enabled': True}
        }
    }
    
    factory = ScraperFactory(config)
    
    try:
        metadata_scraper = factory.create_metadata_scraper()
        
        # List of movie codes to scrape
        movie_codes = [
            "SSIS-001",
            "SSIS-002", 
            "SSIS-003",
            "NONEXISTENT-001",  # This should fail
            "SSIS-004"
        ]
        
        print(f"Scraping metadata for {len(movie_codes)} movies...")
        
        # Scrape multiple movies concurrently
        results = await metadata_scraper.scrape_multiple(movie_codes)
        
        # Process results
        successful = 0
        failed = 0
        
        for code, metadata in results.items():
            if metadata:
                print(f"✓ {code}: {metadata.title}")
                successful += 1
            else:
                print(f"✗ {code}: Failed to scrape")
                failed += 1
        
        print(f"\nBatch results: {successful} successful, {failed} failed")
        
        # Show final statistics
        stats = metadata_scraper.get_scraper_stats()
        print(f"Final statistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Cache hit rate: {stats['cache_hit_rate']:.1f}%")
        
    except Exception as e:
        print(f"Error in batch scraping: {e}")


async def custom_scraper_priority_example():
    """Demonstrate custom scraper priority and preferences."""
    print("\n=== Custom Scraper Priority Example ===\n")
    
    # Configuration with custom priorities
    config = {
        'scrapers': {
            'javdb': {'enabled': True, 'priority': 2, 'use_login': False},
            'javlibrary': {'enabled': True, 'priority': 1}  # Higher priority
        }
    }
    
    factory = ScraperFactory(config)
    
    try:
        metadata_scraper = factory.create_metadata_scraper()
        
        movie_code = "SSIS-005"
        
        # Scrape with default priority (javlibrary first)
        print("Scraping with default priority (javlibrary first)...")
        metadata1 = await metadata_scraper.scrape_metadata(movie_code)
        
        if metadata1:
            print(f"Result from: {metadata1.source_url}")
        
        # Clear cache to force fresh scraping
        metadata_scraper.clear_cache()
        
        # Scrape with preferred scrapers (javdb first)
        print("\nScraping with preferred scrapers (javdb first)...")
        metadata2 = await metadata_scraper.scrape_metadata(
            movie_code,
            preferred_scrapers=["javdb", "javlibrary"]
        )
        
        if metadata2:
            print(f"Result from: {metadata2.source_url}")
        
    except Exception as e:
        print(f"Error in priority example: {e}")


async def health_check_example():
    """Demonstrate health checking functionality."""
    print("\n=== Health Check Example ===\n")
    
    factory = ScraperFactory()
    
    try:
        metadata_scraper = factory.create_metadata_scraper()
        
        print("Performing health check on all scrapers...")
        health_status = await metadata_scraper.health_check()
        
        for scraper_name, status in health_status.items():
            availability = "✓ Available" if status['available'] else "✗ Unavailable"
            print(f"{scraper_name}: {availability}")
            
            if status['error']:
                print(f"  Error: {status['error']}")
            
            if status['last_check']:
                print(f"  Last check: {status['last_check']}")
            
            print(f"  Usage count: {status['usage_count']}")
            print()
        
    except Exception as e:
        print(f"Error in health check: {e}")


async def error_handling_example():
    """Demonstrate error handling and failover."""
    print("\n=== Error Handling and Failover Example ===\n")
    
    # Configuration with short timeouts to trigger errors
    config = {
        'coordinator': {
            'timeout_seconds': 1,  # Very short timeout
            'retry_attempts': 1
        }
    }
    
    factory = ScraperFactory(config)
    
    try:
        metadata_scraper = factory.create_metadata_scraper()
        
        # Try to scrape with short timeout (likely to fail)
        movie_code = "SSIS-006"
        print(f"Attempting to scrape {movie_code} with short timeout...")
        
        metadata = await metadata_scraper.scrape_metadata(movie_code)
        
        if metadata:
            print(f"Successfully scraped despite short timeout: {metadata.title}")
        else:
            print("Failed to scrape due to timeout/errors")
        
        # Show statistics including failures
        stats = metadata_scraper.get_scraper_stats()
        print(f"\nError handling statistics:")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Successful: {stats['successful_requests']}")
        print(f"  Failed: {stats['failed_requests']}")
        
    except Exception as e:
        print(f"Error in error handling example: {e}")


async def configuration_validation_example():
    """Demonstrate configuration validation."""
    print("\n=== Configuration Validation Example ===\n")
    
    # Test with invalid configuration
    invalid_config = {
        'coordinator': {
            'max_concurrent_requests': 0,  # Invalid
            'timeout_seconds': -1,  # Invalid
            'retry_attempts': -1  # Invalid
        },
        'scrapers': {
            'javdb': {'enabled': False},
            'javlibrary': {'enabled': False}  # No scrapers enabled
        }
    }
    
    factory = ScraperFactory(invalid_config)
    
    print("Validating invalid configuration...")
    validation_result = factory.validate_config()
    
    if validation_result['errors']:
        print("Configuration errors found:")
        for error in validation_result['errors']:
            print(f"  ✗ {error}")
    
    if validation_result['warnings']:
        print("Configuration warnings:")
        for warning in validation_result['warnings']:
            print(f"  ⚠ {warning}")
    
    # Test with valid configuration
    print("\nValidating valid configuration...")
    valid_factory = ScraperFactory()
    valid_result = valid_factory.validate_config()
    
    if not valid_result['errors']:
        print("✓ Configuration is valid")
    
    if valid_result['warnings']:
        print("Warnings:")
        for warning in valid_result['warnings']:
            print(f"  ⚠ {warning}")


async def main():
    """Run all examples."""
    print("MetadataScraper Coordinator Examples")
    print("=" * 50)
    
    try:
        await basic_usage_example()
        await batch_scraping_example()
        await custom_scraper_priority_example()
        await health_check_example()
        await error_handling_example()
        await configuration_validation_example()
        
        print("\n" + "=" * 50)
        print("All examples completed!")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error in examples: {e}")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())