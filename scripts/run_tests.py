#!/usr/bin/env python3
"""Test runner script with various test execution options."""

import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    if description:
        print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "unit"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml"
        ])
    
    return run_command(cmd, "Unit Tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "tests/integration/", "-m", "integration"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Integration Tests")


def run_performance_tests(verbose=False):
    """Run performance tests."""
    cmd = ["python", "-m", "pytest", "tests/performance/", "-m", "performance"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Performance Tests")


def run_load_tests(verbose=False):
    """Run load tests."""
    cmd = ["python", "-m", "pytest", "tests/performance/", "-m", "load"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Load Tests")


def run_all_tests(verbose=False, coverage=False):
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml"
        ])
    
    return run_command(cmd, "All Tests")


def run_specific_test(test_path, verbose=False):
    """Run a specific test file or test function."""
    cmd = ["python", "-m", "pytest", test_path]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, f"Specific Test: {test_path}")


def run_failed_tests(verbose=False):
    """Run only previously failed tests."""
    cmd = ["python", "-m", "pytest", "--lf"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd, "Failed Tests (Last Failed)")


def run_code_quality_checks():
    """Run code quality checks."""
    success = True
    
    # Run flake8
    print("\n" + "="*60)
    print("Running: Code Style Check (flake8)")
    print("="*60)
    result = subprocess.run(["flake8", "src/", "tests/"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Flake8 issues found:")
        print(result.stdout)
        success = False
    else:
        print("✓ No flake8 issues found")
    
    # Run mypy
    print("\n" + "="*60)
    print("Running: Type Check (mypy)")
    print("="*60)
    result = subprocess.run(["mypy", "src/"], capture_output=True, text=True)
    if result.returncode != 0:
        print("MyPy issues found:")
        print(result.stdout)
        success = False
    else:
        print("✓ No mypy issues found")
    
    # Run isort check
    print("\n" + "="*60)
    print("Running: Import Sort Check (isort)")
    print("="*60)
    result = subprocess.run(["isort", "--check-only", "src/", "tests/"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Import sorting issues found:")
        print(result.stdout)
        success = False
    else:
        print("✓ No import sorting issues found")
    
    # Run black check
    print("\n" + "="*60)
    print("Running: Code Format Check (black)")
    print("="*60)
    result = subprocess.run(["black", "--check", "src/", "tests/"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Code formatting issues found:")
        print(result.stdout)
        success = False
    else:
        print("✓ No code formatting issues found")
    
    return success


def generate_test_report():
    """Generate comprehensive test report."""
    print("\n" + "="*60)
    print("Generating Comprehensive Test Report")
    print("="*60)
    
    # Run tests with detailed reporting
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-report=term-missing",
        "--junit-xml=test-results.xml",
        "-v"
    ]
    
    success = run_command(cmd, "Comprehensive Test Report")
    
    if success:
        print("\n" + "="*60)
        print("Test Report Generated Successfully")
        print("="*60)
        print("Coverage Report: htmlcov/index.html")
        print("JUnit XML: test-results.xml")
        print("Coverage XML: coverage.xml")
    
    return success


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="AV Metadata Scraper Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    
    subparsers = parser.add_subparsers(dest="command", help="Test commands")
    
    # Unit tests
    unit_parser = subparsers.add_parser("unit", help="Run unit tests")
    
    # Integration tests
    integration_parser = subparsers.add_parser("integration", help="Run integration tests")
    
    # Performance tests
    performance_parser = subparsers.add_parser("performance", help="Run performance tests")
    
    # Load tests
    load_parser = subparsers.add_parser("load", help="Run load tests")
    
    # All tests
    all_parser = subparsers.add_parser("all", help="Run all tests")
    
    # Specific test
    specific_parser = subparsers.add_parser("test", help="Run specific test")
    specific_parser.add_argument("path", help="Path to test file or test function")
    
    # Failed tests
    failed_parser = subparsers.add_parser("failed", help="Run previously failed tests")
    
    # Code quality
    quality_parser = subparsers.add_parser("quality", help="Run code quality checks")
    
    # Test report
    report_parser = subparsers.add_parser("report", help="Generate comprehensive test report")
    
    # CI pipeline
    ci_parser = subparsers.add_parser("ci", help="Run full CI pipeline")
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ["PYTHONPATH"] = str(Path.cwd())
    
    success = True
    
    if args.command == "unit":
        success = run_unit_tests(args.verbose, args.coverage)
    elif args.command == "integration":
        success = run_integration_tests(args.verbose)
    elif args.command == "performance":
        success = run_performance_tests(args.verbose)
    elif args.command == "load":
        success = run_load_tests(args.verbose)
    elif args.command == "all":
        success = run_all_tests(args.verbose, args.coverage)
    elif args.command == "test":
        success = run_specific_test(args.path, args.verbose)
    elif args.command == "failed":
        success = run_failed_tests(args.verbose)
    elif args.command == "quality":
        success = run_code_quality_checks()
    elif args.command == "report":
        success = generate_test_report()
    elif args.command == "ci":
        # Run full CI pipeline
        print("Running Full CI Pipeline...")
        
        # 1. Code quality checks
        if not run_code_quality_checks():
            print("❌ Code quality checks failed")
            success = False
        
        # 2. Unit tests with coverage
        if success and not run_unit_tests(verbose=True, coverage=True):
            print("❌ Unit tests failed")
            success = False
        
        # 3. Integration tests
        if success and not run_integration_tests(verbose=True):
            print("❌ Integration tests failed")
            success = False
        
        # 4. Performance tests (optional, may be skipped in CI)
        if success:
            print("\nRunning performance tests (may be skipped in CI)...")
            run_performance_tests(verbose=True)  # Don't fail CI on performance tests
        
        if success:
            print("\n✅ CI Pipeline completed successfully!")
        else:
            print("\n❌ CI Pipeline failed!")
    
    else:
        # Default: run unit tests
        success = run_unit_tests(args.verbose, args.coverage)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()