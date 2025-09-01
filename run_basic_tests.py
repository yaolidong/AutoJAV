#!/usr/bin/env python3
"""Simple test runner for basic validation."""

import subprocess
import sys
from pathlib import Path

def run_basic_tests():
    """Run basic tests to validate the test suite setup."""
    print("Running basic test validation...")
    
    # Set PYTHONPATH
    import os
    os.environ["PYTHONPATH"] = str(Path.cwd())
    
    try:
        # Run a simple test to validate setup
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_models.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Basic tests passed!")
            return True
        else:
            print("❌ Basic tests failed!")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out!")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)