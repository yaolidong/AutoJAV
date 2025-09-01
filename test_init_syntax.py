#!/usr/bin/env python3
"""
Test __init__.py files for syntax errors without importing external dependencies.
"""

import ast
import sys
from pathlib import Path

def check_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content, filename=str(file_path))
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def test_init_files():
    """Test all __init__.py files for syntax errors."""
    print("🔍 Testing __init__.py files syntax...\n")
    
    success_count = 0
    total_count = 0
    
    # Find all __init__.py files
    init_files = list(Path('src').rglob('__init__.py'))
    
    for init_file in sorted(init_files):
        total_count += 1
        is_valid, error = check_syntax(init_file)
        
        if is_valid:
            print(f"✅ {init_file} - Syntax OK")
            success_count += 1
        else:
            print(f"❌ {init_file} - {error}")
    
    print(f"\n📊 Results: {success_count}/{total_count} __init__.py files have valid syntax")
    
    if success_count == total_count:
        print("🎉 All __init__.py files have valid syntax!")
        return 0
    else:
        print("⚠️  Some __init__.py files have syntax errors.")
        return 1

if __name__ == "__main__":
    sys.exit(test_init_files())