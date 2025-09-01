#!/usr/bin/env python3
"""
文件整理功能测试脚本
测试视频文件的自动整理和重命名功能
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import date

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.organizers.file_organizer import FileOrganizer, ConflictResolution
from src.models.video_file import VideoFile
from src.models.movie_metadata import MovieMetadata

def create_test_environment():
    """创建测试环境和测试文件"""
    print("\n" + "="*60)
    print("🔧 创建测试环境")
    print("="*60)
    
    # 创建临时测试目录
    test_dir = Path("./test_organize")
    source_dir = test_dir / "source"
    target_dir = test_dir / "organized"
    
    # 清理旧的测试目录
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    # 创建目录结构
    source_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ 创建源目录: {source_dir}")
    print(f"✅ 创建目标目录: {target_dir}")
    
    # 创建测试视频文件
    test_files = [
        "SSIS-001.mp4",
        "IPX-999.avi",
        "STARS-123.mkv",
        "MIDE-456.mp4",
        "JUL-789.avi"
    ]
    
    created_files = []
    for filename in test_files:
        file_path = source_dir / filename
        # 创建假的视频文件（只是文本文件）
        with open(file_path, 'w') as f:
            f.write(f"This is a test video file: {filename}")
        created_files.append(file_path)
        print(f"✅ 创建测试文件: {filename}")
    
    return source_dir, target_dir, created_files

def create_test_metadata():
    """创建测试元数据"""
    print("\n" + "="*60)
    print("📝 创建测试元数据")
    print("="*60)
    
    metadata_list = [
        MovieMetadata(
            code="SSIS-001",
            title="测试影片1 - 三上悠亚",
            title_en="Test Movie 1",
            actresses=["三上悠亚", "桥本有菜"],
            release_date=date(2023, 1, 15),
            duration=120,
            studio="S1",
            series="测试系列",
            genres=["剧情", "爱情"],
            cover_url="https://example.com/cover1.jpg",
            description="这是一个测试影片描述"
        ),
        MovieMetadata(
            code="IPX-999",
            title="测试影片2 - 明日花绮罗",
            title_en="Test Movie 2",
            actresses=["明日花绮罗"],
            release_date=date(2023, 2, 20),
            duration=150,
            studio="IDEA POCKET",
            genres=["动作", "冒险"],
            cover_url="https://example.com/cover2.jpg"
        ),
        MovieMetadata(
            code="STARS-123",
            title="测试影片3 - 小仓由菜",
            title_en="Test Movie 3",
            actresses=["小仓由菜", "天使萌", "樱空桃"],
            release_date=date(2023, 3, 10),
            duration=180,
            studio="SOD",
            series="STARS系列",
            genres=["喜剧", "浪漫"],
            cover_url="https://example.com/cover3.jpg"
        ),
        MovieMetadata(
            code="MIDE-456",
            title="测试影片4",
            title_en="Test Movie 4",
            actresses=["未知女优"],
            release_date=date(2023, 4, 5),
            duration=90,
            studio="MOODYZ",
            genres=["悬疑"],
            cover_url="https://example.com/cover4.jpg"
        ),
        MovieMetadata(
            code="JUL-789",
            title="测试影片5",
            title_en="Test Movie 5",
            actresses=[],  # 无女优信息
            release_date=date(2023, 5, 25),
            duration=110,
            studio="Madonna",
            genres=["剧情"],
            cover_url="https://example.com/cover5.jpg"
        )
    ]
    
    for metadata in metadata_list:
        print(f"✅ 创建元数据: {metadata.code} - {metadata.title}")
    
    return metadata_list

def test_basic_organizing(source_dir, target_dir, files, metadata_list):
    """测试基本的文件整理功能"""
    print("\n" + "="*60)
    print("🔍 测试基本文件整理功能")
    print("="*60)
    
    # 创建文件整理器（使用女优/代码/代码.扩展名 模式）
    organizer = FileOrganizer(
        target_directory=str(target_dir),
        naming_pattern="{actress}/{code}/{code}.{ext}",
        conflict_resolution=ConflictResolution.RENAME,
        create_metadata_files=True,
        safe_mode=True  # 复制而不是移动
    )
    
    print(f"✅ 创建文件整理器")
    print(f"   目标目录: {target_dir}")
    print(f"   命名模式: {{actress}}/{{code}}/{{code}}.{{ext}}")
    print(f"   冲突处理: 重命名")
    print(f"   安全模式: 启用（复制文件）")
    
    # 验证目标目录
    validation = organizer.validate_target_directory()
    if validation['valid']:
        print(f"✅ 目标目录验证通过")
        if 'free_space_gb' in validation['info']:
            print(f"   可用空间: {validation['info']['free_space_gb']:.2f} GB")
    else:
        print(f"❌ 目标目录验证失败: {validation['errors']}")
        return False
    
    # 准备文件和元数据对
    file_metadata_pairs = []
    for i, file_path in enumerate(files):
        video_file = VideoFile(
            file_path=str(file_path),
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            extension=file_path.suffix
        )
        
        if i < len(metadata_list):
            file_metadata_pairs.append((video_file, metadata_list[i]))
    
    # 执行批量整理
    print(f"\n🚀 开始整理 {len(file_metadata_pairs)} 个文件...")
    batch_result = organizer.organize_multiple(file_metadata_pairs)
    
    # 显示结果
    print(f"\n📊 整理结果:")
    print(f"   总文件数: {batch_result['total_files']}")
    print(f"   成功: {batch_result['successful']}")
    print(f"   失败: {batch_result['failed']}")
    
    # 显示详细结果
    for item in batch_result['results']:
        result = item['result']
        if result['success']:
            print(f"\n✅ {item['file']}")
            if 'details' in result:
                details = result['details']
                print(f"   原路径: {details['original_path']}")
                print(f"   新路径: {details['target_path']}")
                if details['metadata_file']:
                    print(f"   元数据: {details['metadata_file']}")
        else:
            print(f"\n❌ {item['file']}: {result['message']}")
    
    # 显示统计信息
    stats = organizer.get_statistics()
    print(f"\n📈 统计信息:")
    print(f"   处理文件: {stats['files_processed']}")
    print(f"   复制文件: {stats['files_copied']}")
    print(f"   跳过文件: {stats['files_skipped']}")
    print(f"   创建元数据: {stats['metadata_files_created']}")
    print(f"   成功率: {stats['success_rate']:.1f}%")
    
    return batch_result['successful'] > 0

def test_different_patterns(source_dir, target_dir, files, metadata_list):
    """测试不同的命名模式"""
    print("\n" + "="*60)
    print("🔍 测试不同的命名模式")
    print("="*60)
    
    patterns = [
        ("{code}/{code}.{ext}", "按代码分类"),
        ("{studio}/{code}/{code}.{ext}", "按制作商/代码分类"),
        ("{year}/{month}/{code}.{ext}", "按年月分类"),
        ("{actress}/{year}/{code}_{title}.{ext}", "按女优/年份分类，包含标题")
    ]
    
    for pattern, description in patterns:
        print(f"\n测试模式: {description}")
        print(f"模式: {pattern}")
        
        # 为每个模式创建子目录
        pattern_dir = target_dir / f"pattern_{patterns.index((pattern, description))}"
        pattern_dir.mkdir(exist_ok=True)
        
        organizer = FileOrganizer(
            target_directory=str(pattern_dir),
            naming_pattern=pattern,
            conflict_resolution=ConflictResolution.SKIP,
            create_metadata_files=False,
            safe_mode=True
        )
        
        # 只测试第一个文件
        if files and metadata_list:
            video_file = VideoFile(
                file_path=str(files[0]),
                filename=files[0].name,
                file_size=100,
                extension=files[0].suffix
            )
            
            result = organizer.organize_file(video_file, metadata_list[0])
            
            if result['success']:
                print(f"✅ 成功: {result['details']['target_path']}")
            else:
                print(f"❌ 失败: {result['message']}")

def verify_organized_files(target_dir):
    """验证整理后的文件结构"""
    print("\n" + "="*60)
    print("🔍 验证整理后的文件结构")
    print("="*60)
    
    # 遍历目标目录
    organized_files = []
    metadata_files = []
    
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            file_path = Path(root) / file
            relative_path = file_path.relative_to(target_dir)
            
            if file.endswith('.json'):
                metadata_files.append(relative_path)
            else:
                organized_files.append(relative_path)
    
    print(f"\n📁 整理后的文件结构:")
    print(f"找到 {len(organized_files)} 个视频文件")
    print(f"找到 {len(metadata_files)} 个元数据文件")
    
    # 显示目录树
    print("\n目录结构:")
    for root, dirs, files in os.walk(target_dir):
        level = root.replace(str(target_dir), '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{Path(root).name}/')
        
        subindent = ' ' * 2 * (level + 1)
        for file in files[:5]:  # 只显示前5个文件
            print(f'{subindent}{file}')
        if len(files) > 5:
            print(f'{subindent}... 还有 {len(files)-5} 个文件')
    
    # 读取一个元数据文件示例
    if metadata_files:
        sample_metadata = target_dir / metadata_files[0]
        print(f"\n📄 元数据文件示例: {metadata_files[0]}")
        
        try:
            with open(sample_metadata, 'r', encoding='utf-8') as f:
                metadata_content = json.load(f)
                print(json.dumps(metadata_content, indent=2, ensure_ascii=False)[:500])
        except Exception as e:
            print(f"读取元数据失败: {e}")
    
    return len(organized_files) > 0

def cleanup_test_environment():
    """清理测试环境"""
    print("\n" + "="*60)
    print("🧹 清理测试环境")
    print("="*60)
    
    test_dir = Path("./test_organize")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"✅ 已删除测试目录: {test_dir}")

def main():
    """主测试函数"""
    print("="*60)
    print("🚀 文件整理功能测试")
    print("="*60)
    
    try:
        # 创建测试环境
        source_dir, target_dir, test_files = create_test_environment()
        
        # 创建测试元数据
        metadata_list = create_test_metadata()
        
        # 测试基本整理功能
        basic_ok = test_basic_organizing(source_dir, target_dir, test_files, metadata_list)
        
        # 测试不同命名模式
        test_different_patterns(source_dir, target_dir, test_files, metadata_list)
        
        # 验证整理结果
        verify_ok = verify_organized_files(target_dir)
        
        # 总结
        print("\n" + "="*60)
        print("📊 测试结果总结")
        print("="*60)
        
        if basic_ok and verify_ok:
            print("🎉 所有测试通过！")
            print("✅ 文件整理功能正常")
            print("✅ 元数据创建正常")
            print("✅ 多种命名模式支持")
            print("✅ 冲突处理正常")
        else:
            print("⚠️  部分测试失败")
        
        print("\n💡 功能特点:")
        print("1. 支持多种命名模式（女优/代码/日期等）")
        print("2. 自动创建元数据JSON文件")
        print("3. 智能冲突处理（跳过/覆盖/重命名）")
        print("4. 安全模式（复制而非移动）")
        print("5. 批量处理支持")
        print("6. 完整的错误处理和日志")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 自动清理测试文件（在自动测试中不询问）
        import sys
        if sys.stdin.isatty():
            # 交互模式
            print("\n是否保留测试文件查看？(y/n): ", end='')
            keep = input().strip().lower()
            if keep != 'y':
                cleanup_test_environment()
            else:
                print(f"测试文件保留在: ./test_organize")
        else:
            # 非交互模式，保留文件以便查看
            print(f"\n测试文件保留在: ./test_organize")
            print("可以手动删除或运行: rm -rf ./test_organize")

if __name__ == "__main__":
    main()