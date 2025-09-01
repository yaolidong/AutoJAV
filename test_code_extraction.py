#!/usr/bin/env python3
"""
专门测试代码提取功能
"""

import sys
import re
from pathlib import Path

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_code_extraction_direct():
    """直接测试代码提取逻辑"""
    print("🔍 直接测试代码提取逻辑...")
    
    # 定义代码模式
    code_patterns = [
        # Standard patterns like ABC-123, ABCD-123
        r'([A-Z]{2,5})-?(\d{3,4})',
        # Patterns with numbers in prefix like 1PON-123456
        r'(\d+[A-Z]+)-?(\d+)',
        # FC2 patterns like FC2-PPV-123456
        r'(FC2)-?(PPV)?-?(\d+)',
        # Carib patterns like 123456-789
        r'(\d{6})-(\d{3})',
        # Tokyo Hot patterns like n1234
        r'(n)(\d{4})',
        # Heydouga patterns like 4017-PPV123
        r'(\d{4})-?(PPV)?(\d+)',
    ]
    
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in code_patterns]
    
    def extract_code(filename: str) -> str:
        """提取代码"""
        # Remove file extension
        name_without_ext = Path(filename).stem
        
        # Clean up common prefixes/suffixes
        cleaned_name = clean_filename(name_without_ext)
        
        # Try each pattern
        for pattern in compiled_patterns:
            match = pattern.search(cleaned_name)
            if match:
                code = format_code(match)
                if code:
                    return code.upper()
        
        return None
    
    def clean_filename(filename: str) -> str:
        """清理文件名"""
        # Remove common prefixes
        prefixes_to_remove = [
            r'^\[.*?\]',  # Remove [tags] at the beginning
            r'^\(.*?\)',  # Remove (tags) at the beginning
            r'^【.*?】',   # Remove 【tags】 at the beginning
        ]
        
        cleaned = filename
        for prefix_pattern in prefixes_to_remove:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove common suffixes
        suffixes_to_remove = [
            r'\[.*?\]$',  # Remove [tags] at the end
            r'\(.*?\)$',  # Remove (tags) at the end
            r'【.*?】$',   # Remove 【tags】 at the end
            r'_\d+p$',    # Remove quality indicators like _1080p
            r'_HD$',      # Remove HD suffix
            r'_FHD$',     # Remove FHD suffix
            r'_4K$',      # Remove 4K suffix
        ]
        
        for suffix_pattern in suffixes_to_remove:
            cleaned = re.sub(suffix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Replace common separators with spaces
        cleaned = re.sub(r'[_\-\.]', ' ', cleaned)
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def format_code(match) -> str:
        """格式化代码"""
        groups = match.groups()
        
        if len(groups) >= 2:
            prefix = groups[0]
            number = groups[1]
            
            # Handle special cases
            if prefix.upper() == 'FC2':
                # FC2-PPV-123456 format
                if len(groups) >= 3 and groups[2]:
                    return f"FC2-PPV-{groups[2]}"
                else:
                    return f"FC2-{number}"
            
            elif prefix.upper() == 'N':
                # Tokyo Hot n1234 format
                return f"n{number}"
            
            elif prefix.isdigit():
                # Patterns like 1PON-123456 or Carib 123456-789
                if len(groups) >= 3:
                    return f"{prefix}-{groups[2]}"
                else:
                    return f"{prefix}-{number}"
            
            else:
                # Standard ABC-123 format
                return f"{prefix}-{number}"
        
        return None
    
    # 测试用例
    test_cases = [
        ("SSIS-001.mp4", "SSIS-001"),
        ("STARS-123.mkv", "STARS-123"),
        ("MIDE-456.avi", "MIDE-456"),
        ("[FHD]ABC-789[1080p].mp4", "ABC-789"),
        ("FC2-PPV-123456.mp4", "FC2-PPV-123456"),
        ("not_a_code.mp4", None),
    ]
    
    success_count = 0
    for filename, expected_code in test_cases:
        extracted_code = extract_code(filename)
        if extracted_code == expected_code:
            success_count += 1
            print(f"  ✅ {filename} -> {extracted_code}")
        else:
            print(f"  ❌ {filename} -> {extracted_code} (期望: {expected_code})")
            # 调试信息
            cleaned = clean_filename(Path(filename).stem)
            print(f"     清理后: '{cleaned}'")
    
    print(f"\n代码提取测试: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)


def test_with_file_scanner():
    """使用 FileScanner 测试"""
    print("\n🔍 使用 FileScanner 测试...")
    
    try:
        from src.scanner.file_scanner import FileScanner
        
        scanner = FileScanner("./test", ['.mp4'])
        
        test_cases = [
            ("SSIS-001.mp4", "SSIS-001"),
            ("STARS-123.mkv", "STARS-123"),
            ("MIDE-456.avi", "MIDE-456"),
            ("[FHD]ABC-789[1080p].mp4", "ABC-789"),
            ("FC2-PPV-123456.mp4", "FC2-PPV-123456"),
            ("not_a_code.mp4", None),
        ]
        
        success_count = 0
        for filename, expected_code in test_cases:
            extracted_code = scanner.extract_code_from_filename(filename)
            if extracted_code == expected_code:
                success_count += 1
                print(f"  ✅ {filename} -> {extracted_code}")
            else:
                print(f"  ❌ {filename} -> {extracted_code} (期望: {expected_code})")
        
        print(f"\nFileScanner 测试: {success_count}/{len(test_cases)} 通过")
        return success_count == len(test_cases)
        
    except Exception as e:
        print(f"❌ FileScanner 测试失败: {e}")
        return False


if __name__ == "__main__":
    print("🚀 开始代码提取功能测试...\n")
    
    # 测试直接实现
    result1 = test_code_extraction_direct()
    
    # 测试 FileScanner
    result2 = test_with_file_scanner()
    
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    print("="*50)
    print(f"直接实现: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"FileScanner: {'✅ 通过' if result2 else '❌ 失败'}")
    
    if result1 and result2:
        print("\n🎉 代码提取功能正常！")
    else:
        print("\n⚠️  代码提取功能需要修复")