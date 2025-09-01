#!/usr/bin/env python3
"""
测试刮削功能是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_javdb_scraper():
    """测试 JavDB 刮削器"""
    print("🔍 测试 JavDB 刮削器...")

    try:
        from src.scrapers.javdb_scraper import JavDBScraper
        from src.utils.webdriver_manager import WebDriverManager
        from src.models.config import Config

        # 创建基本配置
        config = Config(
            source_directory="./test",
            target_directory="./test",
            headless_browser=True,
            browser_timeout=30,
        )

        # 创建 WebDriver 管理器
        driver_manager = WebDriverManager(config)

        # 初始化刮削器
        scraper = JavDBScraper(driver_manager)

        # 测试可用性
        is_available = await scraper.is_available()
        print(f"JavDB 可用性: {'✅' if is_available else '❌'}")

        if is_available:
            # 测试搜索一个常见的代码
            test_code = "SSIS-001"
            print(f"测试搜索代码: {test_code}")

            metadata = await scraper.search_movie(test_code)

            if metadata:
                print("✅ 成功获取元数据:")
                print(f"  - 代码: {metadata.code}")
                print(f"  - 标题: {metadata.title}")
                print(
                    f"  - 演员: {', '.join(metadata.actresses) if metadata.actresses else 'N/A'}"
                )
                print(f"  - 发布日期: {metadata.release_date or 'N/A'}")
                print(f"  - 工作室: {metadata.studio or 'N/A'}")
                return True
            else:
                print("❌ 未找到元数据")
                return False
        else:
            print("❌ JavDB 不可用")
            return False

    except Exception as e:
        print(f"❌ JavDB 测试失败: {e}")
        return False


async def test_javlibrary_scraper():
    """测试 JavLibrary 刮削器"""
    print("\n🔍 测试 JavLibrary 刮削器...")

    try:
        from src.scrapers.javlibrary_scraper import JavLibraryScraper
        from src.utils.webdriver_manager import WebDriverManager
        from src.models.config import Config

        # 创建基本配置
        config = Config(
            source_directory="./test",
            target_directory="./test",
            headless_browser=True,
            browser_timeout=30,
        )

        # 创建 WebDriver 管理器
        driver_manager = WebDriverManager(config)

        # 初始化刮削器
        scraper = JavLibraryScraper(driver_manager)

        # 测试可用性
        is_available = await scraper.is_available()
        print(f"JavLibrary 可用性: {'✅' if is_available else '❌'}")

        if is_available:
            # 测试搜索一个常见的代码
            test_code = "SSIS-001"
            print(f"测试搜索代码: {test_code}")

            metadata = await scraper.search_movie(test_code)

            if metadata:
                print("✅ 成功获取元数据:")
                print(f"  - 代码: {metadata.code}")
                print(f"  - 标题: {metadata.title}")
                print(
                    f"  - 演员: {', '.join(metadata.actresses) if metadata.actresses else 'N/A'}"
                )
                print(f"  - 发布日期: {metadata.release_date or 'N/A'}")
                print(f"  - 工作室: {metadata.studio or 'N/A'}")
                return True
            else:
                print("❌ 未找到元数据")
                return False
        else:
            print("❌ JavLibrary 不可用")
            return False

    except Exception as e:
        print(f"❌ JavLibrary 测试失败: {e}")
        return False


async def test_file_scanner():
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
            "not_a_video.txt",
        ]

        for filename in test_files:
            (test_dir / filename).write_text("test content")

        # 初始化扫描器 - 修复参数
        scanner = FileScanner(str(test_dir), [".mp4", ".mkv", ".avi"])

        # 扫描文件 - 这是同步方法，不需要 await
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


async def test_metadata_scraper():
    """测试元数据刮削器协调器"""
    print("\n🔍 测试元数据刮削器协调器...")

    try:
        from src.scrapers.metadata_scraper import MetadataScraper
        from src.scrapers.javdb_scraper import JavDBScraper
        from src.scrapers.javlibrary_scraper import JavLibraryScraper
        from src.utils.webdriver_manager import WebDriverManager
        from src.models.config import Config

        # 创建配置
        config = Config(
            source_directory="./test",
            target_directory="./test",
            scraper_priority=["javdb", "javlibrary"],
            headless_browser=True,
            browser_timeout=30,
        )

        # 创建 WebDriver 管理器
        driver_manager = WebDriverManager(config)

        # 创建刮削器列表
        scrapers = [JavDBScraper(driver_manager), JavLibraryScraper(driver_manager)]

        # 初始化协调器
        metadata_scraper = MetadataScraper(scrapers, config)

        # 测试搜索
        test_code = "SSIS-001"
        print(f"测试搜索代码: {test_code}")

        metadata = await metadata_scraper.scrape_metadata(test_code)

        if metadata:
            print("✅ 成功获取元数据:")
            print(f"  - 代码: {metadata.code}")
            print(f"  - 标题: {metadata.title}")
            print(
                f"  - 演员: {', '.join(metadata.actresses) if metadata.actresses else 'N/A'}"
            )
            print(f"  - 来源: {metadata.source_url}")
            return True
        else:
            print("❌ 未找到元数据")
            return False

    except Exception as e:
        print(f"❌ 元数据刮削器测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始测试 AV Metadata Scraper 刮削功能...\n")

    results = []

    # 运行各项测试
    tests = [
        ("文件扫描器", test_file_scanner),
        ("JavDB 刮削器", test_javdb_scraper),
        ("JavLibrary 刮削器", test_javlibrary_scraper),
        ("元数据刮削器协调器", test_metadata_scraper),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))

    # 输出总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有刮削功能测试通过！")
        return 0
    else:
        print("⚠️  部分刮削功能测试失败，请检查网络连接和依赖。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
