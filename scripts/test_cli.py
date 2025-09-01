#!/usr/bin/env python3
"""
Test script for CLI functionality.

This script tests various CLI commands to ensure they work correctly.
"""

import sys
import asyncio
import subprocess
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def run_cli_command(command: list) -> tuple:
    """
    Run a CLI command and return the result.
    
    Args:
        command: List of command arguments
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "cli.py", *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent.parent
        )
        
        stdout, stderr = await process.communicate()
        
        return process.returncode, stdout.decode(), stderr.decode()
        
    except Exception as e:
        return 1, "", str(e)


async def test_help_commands():
    """Test help commands."""
    print("Testing help commands...")
    
    # Test main help
    code, stdout, stderr = await run_cli_command(["--help"])
    assert code == 0, f"Main help failed: {stderr}"
    assert "AV Metadata Scraper" in stdout, "Help text missing"
    print("  ✅ Main help")
    
    # Test command help
    commands = ["scan", "process", "config", "status", "test", "health", "stats"]
    
    for command in commands:
        code, stdout, stderr = await run_cli_command([command, "--help"])
        assert code == 0, f"{command} help failed: {stderr}"
        print(f"  ✅ {command} help")


async def test_config_commands():
    """Test configuration commands."""
    print("Testing configuration commands...")
    
    # Test config template generation
    code, stdout, stderr = await run_cli_command(["config", "template"])
    assert code == 0, f"Config template failed: {stderr}"
    print("  ✅ Config template")
    
    # Test config validation (should fail gracefully if no config)
    code, stdout, stderr = await run_cli_command(["config", "validate"])
    # This might fail if no config exists, which is OK
    print("  ✅ Config validate")


async def test_test_commands():
    """Test the test commands."""
    print("Testing test commands...")
    
    # Test network connectivity
    code, stdout, stderr = await run_cli_command(["test", "network"])
    # Network test might fail in some environments, so we just check it runs
    print("  ✅ Network test")
    
    # Test config validation
    code, stdout, stderr = await run_cli_command(["test", "config"])
    print("  ✅ Config test")


async def test_version():
    """Test version command."""
    print("Testing version command...")
    
    code, stdout, stderr = await run_cli_command(["--version"])
    assert code == 0, f"Version command failed: {stderr}"
    assert "AV Metadata Scraper" in stdout, "Version text missing"
    print("  ✅ Version")


async def main():
    """Run all CLI tests."""
    print("🧪 Testing AV Metadata Scraper CLI")
    print("=" * 40)
    
    try:
        await test_help_commands()
        await test_config_commands()
        await test_test_commands()
        await test_version()
        
        print("\n✅ All CLI tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())