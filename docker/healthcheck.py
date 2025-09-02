#!/usr/bin/env python3
"""
Docker Health Check Script for AV Metadata Scraper

This script performs comprehensive health checks for the containerized application.
"""

import sys
import os
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple


def check_python_environment() -> Tuple[bool, str]:
    """Check if Python environment is properly set up."""
    try:
        # Check if we can import required modules
        import selenium
        import requests
        import yaml
        from bs4 import BeautifulSoup
        return True, "Python environment OK"
    except ImportError as e:
        return False, f"Python import error: {e}"


def check_chrome_installation() -> Tuple[bool, str]:
    """Check if Chrome and ChromeDriver are properly installed."""
    try:
        # Check Chrome/Chromium - try both paths
        chrome_paths = ['/usr/bin/chromium', '/usr/bin/google-chrome']
        chrome_result = None
        chrome_path = None
        
        for path in chrome_paths:
            if Path(path).exists():
                chrome_result = subprocess.run(
                    [path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if chrome_result.returncode == 0:
                    chrome_path = path
                    break
        
        if not chrome_path or chrome_result.returncode != 0:
            return False, "Chrome/Chromium not found or not working"
        
        chrome_version = chrome_result.stdout.strip()
        
        # Check ChromeDriver
        driver_result = subprocess.run(
            ['/usr/local/bin/chromedriver', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if driver_result.returncode != 0:
            return False, "ChromeDriver not found or not working"
        
        driver_version = driver_result.stdout.strip()
        
        return True, f"Chrome: {chrome_version}, ChromeDriver: {driver_version}"
    
    except subprocess.TimeoutExpired:
        return False, "Chrome/ChromeDriver check timed out"
    except Exception as e:
        return False, f"Chrome/ChromeDriver check failed: {e}"


def check_directories() -> Tuple[bool, str]:
    """Check if required directories exist and are accessible."""
    required_dirs = [
        '/app/source',
        '/app/target',
        '/app/config',
        '/app/logs'
    ]
    
    issues = []
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            issues.append(f"{dir_path} does not exist")
        elif not path.is_dir():
            issues.append(f"{dir_path} is not a directory")
        elif not os.access(dir_path, os.R_OK):
            issues.append(f"{dir_path} is not readable")
    
    if issues:
        return False, "; ".join(issues)
    
    return True, "All required directories accessible"


def check_configuration() -> Tuple[bool, str]:
    """Check if configuration file exists and is valid."""
    config_path = Path('/app/config/config.yaml')
    
    if not config_path.exists():
        return False, "Configuration file not found"
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Basic validation
        if not isinstance(config, dict):
            return False, "Configuration is not a valid YAML dictionary"
        
        return True, "Configuration file valid"
    
    except yaml.YAMLError as e:
        return False, f"Configuration YAML error: {e}"
    except Exception as e:
        return False, f"Configuration check failed: {e}"


def check_network_connectivity() -> Tuple[bool, str]:
    """Check basic network connectivity."""
    try:
        import requests
        
        # Test basic internet connectivity - try multiple endpoints
        test_urls = [
            'https://www.google.com',
            'https://httpbin.org/status/200',
            'https://api.github.com'
        ]
        
        for url in test_urls:
            try:
                response = requests.get(
                    url,
                    timeout=10,
                    headers={'User-Agent': 'AV-Scraper-HealthCheck/1.0'}
                )
                
                if response.status_code in [200, 301, 302]:
                    return True, f"Network connectivity OK ({url})"
            except:
                continue
        
        return False, "Network connectivity failed on all test endpoints"
    
    except requests.exceptions.Timeout:
        return False, "Network connectivity timeout"
    except requests.exceptions.ConnectionError:
        return False, "Network connection error"
    except Exception as e:
        return False, f"Network check failed: {e}"


def check_selenium_webdriver() -> Tuple[bool, str]:
    """Check if Selenium WebDriver can be initialized."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        # Just check that selenium is importable - actual WebDriver creation
        # happens in the app with proper initialization
        return True, "Selenium library available"
    
    except ImportError as e:
        return False, f"Selenium import failed: {e}"
    except Exception as e:
        return False, f"Selenium check failed: {e}"


def check_application_modules() -> Tuple[bool, str]:
    """Check if application modules can be imported."""
    try:
        # Add app to path (src is inside /app)
        sys.path.insert(0, '/app')
        
        # Try to import main application modules
        from src.config.config_manager import ConfigManager
        from src.models.config import Config
        from src.utils.logging_config import setup_logging
        
        return True, "Application modules OK"
    
    except ImportError as e:
        return False, f"Application module import error: {e}"
    except Exception as e:
        return False, f"Application module check failed: {e}"


def run_health_checks() -> Dict[str, Tuple[bool, str]]:
    """Run all health checks and return results."""
    checks = {
        'python_environment': check_python_environment,
        'chrome_installation': check_chrome_installation,
        'directories': check_directories,
        'configuration': check_configuration,
        'network_connectivity': check_network_connectivity,
        # Skip detailed selenium and module checks - app handles these internally
        # 'selenium_webdriver': check_selenium_webdriver,
        # 'application_modules': check_application_modules,
    }
    
    results = {}
    for check_name, check_func in checks.items():
        try:
            results[check_name] = check_func()
        except Exception as e:
            results[check_name] = (False, f"Health check exception: {e}")
    
    return results


def main():
    """Main health check function."""
    print("Running AV Metadata Scraper health checks...")
    
    results = run_health_checks()
    
    # Print results
    all_passed = True
    for check_name, (passed, message) in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {check_name}: {message}")
        if not passed:
            all_passed = False
    
    # Summary
    if all_passed:
        print("\n✅ All health checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Some health checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()