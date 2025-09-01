#!/usr/bin/env python3
"""
简化的刮削功能测试 - 不依赖浏览器
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """测试核心模块导入"""
    print("🔍 测试核心模块导入...")
    
    try:
        # 测试基础模型
        from src.models.config import Config
        from src.models.movie_metadata import MovieMetadata
        from src.models.video_file import VideoFile
        
        # 测试扫描器
        from src.scanner.file_scanner import FileScanner
        
        # 测试刮削器基类
        from src.scrapers.base_scraper import BaseScraper
        from src.scrapers.metadata_scraper import MetadataScraper
        
        # 测试工具类
        from src.utils.webdriver_manager import WebDriverManager
        from src.utils.login_manager import LoginManager
        
        print("✅ 所有核心模块导入成功")
        return True
        
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def test_config_creation():
    """测试配置创建"""
    print("\n🔍 测试配置创建...")
    
    try:
        from src.models.config import Config
        
        # 创建基本配置
        config = Config(
            source_directory="./test_source",
            target_directory="./test_target"
        )
        
        print(f"✅ 配置创建成功:")
        print(f"  - 源目录: {config.source_directory}")
        print(f"  - 目标目录: {config.target_directory}")
        print(f"  - 支持的扩展: {config.supported_extensions}")
        print(f"  - 刮削器优先级: {config.scraper_priority}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置创建失败: {e}")
        return False


def test_file_scanner():
    """测试文件扫描器"""
    print("\n🔍 测试文件扫描器...")
    
    try:
        from src.scanner.file_scanner import FileScanner
        
        # 创建测试文件
        test_dir = Path("./test_videos")
        test_dir.mkdir(exist_ok=True)
        
        test_files = [
            "SSIS-001.mp4",
            "STARS-123.mkv", 
            "MIDE-456.avi",
            "not_a_video.txt"
        ]
        
        for filename in test_files:
            (test_dir / filename).write_text("test content")
        
        # 初始化扫描器
        scanner = FileScanner(str(test_dir), ['.mp4', '.mkv', '.avi'])
        
        # 扫描文件
        video_files = scanner.scan_directory()
        
        print(f"✅ 扫描到 {len(video_files)} 个视频文件:")
        for video_file in video_files:
            print(f"  - {video_file.filename} (代码: {video_file.detected_code})")
        
        # 清理测试文件
        for filename in test_files:
            (test_dir / filename).unlink(missing_ok=True)
        test_dir.rmdir()
        
        return len(video_files) > 0
        
    except Exception as e:
        print(f"❌ 文件扫描器测试失败: {e}")
        return False


def test_metadata_model():
    """测试元数据模型"""
    print("\n🔍 测试元数据模型...")
    
    try:
        from src.models.movie_metadata import MovieMetadata
        from datetime import date
        
        # 创建测试元数据
        metadata = MovieMetadata(
            code="SSIS-001",
            title="测试电影",
            actresses=["测试演员1", "测试演员2"],
            release_date=date(2023, 1, 1),
            studio="测试工作室",
            genres=["测试类型1", "测试类型2"],
            source_url="https://example.com"
        )
        
        print("✅ 元数据模型创建成功:")
        print(f"  - 代码: {metadata.code}")
        print(f"  - 标题: {metadata.title}")
        print(f"  - 演员: {', '.join(metadata.actresses)}")
        print(f"  - 发布日期: {metadata.release_date}")
        print(f"  - 工作室: {metadata.studio}")
        print(f"  - 类型: {', '.join(metadata.genres)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 元数据模型测试失败: {e}")
        return False


def test_code_extraction():
    """测试代码提取功能"""
    print("\n🔍 测试代码提取功能...")
    
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
        
        print(f"\n代码提取测试: {success_count}/{len(test_cases)} 通过")
        return success_count == len(test_cases)
        
    except Exception as e:
        print(f"❌ 代码提取测试失败: {e}")
        return False


async def test_scraper_interfaces():
    """测试刮削器接口（不实际连接网络）"""
    print("\n🔍 测试刮削器接口...")
    
    try:
        from src.scrapers.base_scraper import BaseScraper
        
        # 创建一个测试刮削器
        class TestScraper(BaseScraper):
            def __init__(self):
                super().__init__("TestScraper")
            
            async def is_available(self) -> bool:
                return True
            
            async def search_movie(self, code: str):
                from src.models.movie_metadata import MovieMetadata
                return MovieMetadata(
                    code=code,
                    title=f"测试电影 {code}",
                    source_url="https://test.com"
                )
        
        scraper = TestScraper()
        
        # 测试接口
        is_available = await scraper.is_available()
        print(f"  ✅ 可用性检查: {is_available}")
        
        metadata = await scraper.search_movie("TEST-001")
        print(f"  ✅ 搜索功能: {metadata.title}")
        
        return True
        
    except Exception as e:
        print(f"❌ 刮削器接口测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始简化刮削功能测试...\n")
    
    results = []
    
    # 运行各项测试
    tests = [
        ("模块导入", test_imports),
        ("配置创建", test_config_creation),
        ("文件扫描器", test_file_scanner),
        ("元数据模型", test_metadata_model),
        ("代码提取", test_code_extraction),
        ("刮削器接口", test_scraper_interfaces),
    ]
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出总结
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有基础功能测试通过！")
        print("\n📝 说明:")
        print("- 核心模块和数据模型工作正常")
        print("- 文件扫描和代码提取功能正常")
        print("- 刮削器接口设计正确")
        print("- 网络刮削功能需要浏览器环境才能完整测试")
        return 0
    else:
        print("⚠️  部分基础功能测试失败，请检查代码实现。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))