#!/usr/bin/env python3
"""Comprehensive test suite validation script."""

import sys
import subprocess
from pathlib import Path


def validate_test_structure():
    """Validate that all test files and directories exist."""
    print("🔍 Validating test suite structure...")
    
    required_files = [
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/README.md",
        "tests/fixtures/__init__.py",
        "tests/fixtures/mock_data.py",
        "tests/integration/__init__.py",
        "tests/integration/test_end_to_end.py",
        "tests/performance/__init__.py",
        "tests/performance/test_performance.py",
        "pytest.ini",
        ".coveragerc",
        ".github/workflows/test.yml",
        "scripts/run_tests.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required test files exist")
    return True


def validate_test_imports():
    """Validate that test modules can be imported."""
    print("🔍 Validating test module imports...")
    
    test_modules = [
        "tests.fixtures.mock_data",
        "tests.integration.test_end_to_end",
        "tests.performance.test_performance"
    ]
    
    for module in test_modules:
        try:
            __import__(module)
            print(f"✅ {module} imports successfully")
        except Exception as e:
            print(f"❌ Failed to import {module}: {e}")
            return False
    
    return True


def validate_mock_data():
    """Validate mock data generation."""
    print("🔍 Validating mock data generation...")
    
    try:
        from tests.fixtures.mock_data import MockDataGenerator
        
        # Test video file generation
        video_file = MockDataGenerator.generate_video_file()
        assert video_file.filename is not None
        assert video_file.detected_code is not None
        print("✅ Video file generation works")
        
        # Test metadata generation
        metadata = MockDataGenerator.generate_movie_metadata()
        assert metadata.code is not None
        assert metadata.title is not None
        assert len(metadata.actresses) > 0
        print("✅ Metadata generation works")
        
        # Test batch generation
        video_files = MockDataGenerator.generate_video_file_batch(5)
        assert len(video_files) == 5
        print("✅ Batch generation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock data validation failed: {e}")
        return False


def validate_pytest_config():
    """Validate pytest configuration."""
    print("🔍 Validating pytest configuration...")
    
    try:
        # Check pytest.ini exists and has required sections
        pytest_ini = Path("pytest.ini")
        if not pytest_ini.exists():
            print("❌ pytest.ini not found")
            return False
        
        content = pytest_ini.read_text()
        required_sections = ["testpaths", "markers", "addopts"]
        
        for section in required_sections:
            if section not in content:
                print(f"❌ Missing {section} in pytest.ini")
                return False
        
        print("✅ pytest.ini is properly configured")
        
        # Check .coveragerc
        coveragerc = Path(".coveragerc")
        if not coveragerc.exists():
            print("❌ .coveragerc not found")
            return False
        
        print("✅ .coveragerc exists")
        return True
        
    except Exception as e:
        print(f"❌ Pytest config validation failed: {e}")
        return False


def run_sample_tests():
    """Run a sample of tests to verify they work."""
    print("🔍 Running sample tests...")
    
    try:
        # Run unit tests
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_models.py", 
            "-v", "--tb=short", "-q"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Sample unit tests pass")
        else:
            print(f"❌ Sample unit tests failed: {result.stderr}")
            return False
        
        # Test that we can collect all tests without errors
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--collect-only", "-q"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ All tests can be collected successfully")
        else:
            print(f"❌ Test collection failed: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Sample tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running sample tests: {e}")
        return False


def validate_ci_config():
    """Validate CI/CD configuration."""
    print("🔍 Validating CI/CD configuration...")
    
    try:
        workflow_file = Path(".github/workflows/test.yml")
        if not workflow_file.exists():
            print("❌ GitHub Actions workflow not found")
            return False
        
        content = workflow_file.read_text()
        required_jobs = ["code-quality", "unit-tests", "integration-tests"]
        
        for job in required_jobs:
            if job not in content:
                print(f"❌ Missing {job} job in workflow")
                return False
        
        print("✅ GitHub Actions workflow is properly configured")
        return True
        
    except Exception as e:
        print(f"❌ CI config validation failed: {e}")
        return False


def generate_test_summary():
    """Generate a summary of the test suite."""
    print("\n" + "="*60)
    print("TEST SUITE SUMMARY")
    print("="*60)
    
    try:
        # Count test files
        test_files = list(Path("tests").rglob("test_*.py"))
        print(f"📁 Test files: {len(test_files)}")
        
        # Count test functions (approximate)
        total_tests = 0
        for test_file in test_files:
            content = test_file.read_text()
            total_tests += content.count("def test_")
        
        print(f"🧪 Estimated test functions: {total_tests}")
        
        # List test categories
        categories = []
        if Path("tests/integration").exists():
            categories.append("Integration Tests")
        if Path("tests/performance").exists():
            categories.append("Performance Tests")
        if any(Path("tests").glob("test_*.py")):
            categories.append("Unit Tests")
        
        print(f"📋 Test categories: {', '.join(categories)}")
        
        # Check for fixtures
        fixtures_file = Path("tests/fixtures/mock_data.py")
        if fixtures_file.exists():
            content = fixtures_file.read_text()
            fixture_count = content.count("def generate_")
            print(f"🎭 Mock data generators: {fixture_count}")
        
        print("\n📖 Documentation:")
        print("   - tests/README.md: Comprehensive test documentation")
        print("   - scripts/run_tests.py: Test runner script")
        print("   - .github/workflows/test.yml: CI/CD pipeline")
        
        print("\n🚀 Quick Start:")
        print("   pytest                    # Run all tests")
        print("   pytest -m unit           # Run unit tests only")
        print("   pytest -m integration    # Run integration tests only")
        print("   pytest --cov=src         # Run with coverage")
        print("   python scripts/run_tests.py ci  # Run full CI pipeline")
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")


def main():
    """Main validation function."""
    print("🧪 AV Metadata Scraper Test Suite Validation")
    print("="*60)
    
    validations = [
        validate_test_structure,
        validate_test_imports,
        validate_mock_data,
        validate_pytest_config,
        validate_ci_config,
        run_sample_tests
    ]
    
    all_passed = True
    
    for validation in validations:
        try:
            if not validation():
                all_passed = False
        except Exception as e:
            print(f"❌ Validation error: {e}")
            all_passed = False
        print()  # Add spacing
    
    generate_test_summary()
    
    if all_passed:
        print("\n🎉 TEST SUITE VALIDATION SUCCESSFUL!")
        print("✅ All components are properly configured and working")
        print("✅ Ready for development and CI/CD")
    else:
        print("\n❌ TEST SUITE VALIDATION FAILED!")
        print("Some components need attention before the test suite is ready")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)