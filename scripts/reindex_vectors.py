#!/usr/bin/env python3
"""
向量索引重建 CLI 工具
用于重建项目或章节的向量索引
"""
import sys
import argparse
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from novelgen.runtime.reindex_tools import reindex_project_vectors, reindex_chapter_vectors


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def print_stats(stats: dict):
    """打印统计信息"""
    print("\n" + "="*60)
    print("重建统计信息")
    print("="*60)
    print(f"项目 ID: {stats['project_id']}")
    
    if 'chapter_index' in stats:
        print(f"章节索引: {stats['chapter_index']}")
    
    if stats['dry_run']:
        print("\n[DRY-RUN 模式 - 未实际执行]")
    
    print(f"\n删除的旧向量: {stats['deleted_chunks']} 个")
    print(f"创建的新向量: {stats['created_chunks']} 个")
    
    if 'chapters_processed' in stats:
        print(f"处理的章节数: {stats['chapters_processed']}")
    
    if stats['errors']:
        print(f"\n错误: {len(stats['errors'])} 个")
        for error in stats['errors']:
            print(f"  - {error}")
    else:
        print("\n✅ 重建成功，无错误")
    
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="重建项目或章节的向量索引",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 重建整个项目的向量索引
  python scripts/reindex_vectors.py my_project
  
  # 重建指定章节的向量索引
  python scripts/reindex_vectors.py my_project --chapter 1
  
  # Dry-run 模式（仅统计，不实际执行）
  python scripts/reindex_vectors.py my_project --dry-run
  
  # 指定项目目录
  python scripts/reindex_vectors.py my_project --project-dir /path/to/project
  
  # 启用详细日志
  python scripts/reindex_vectors.py my_project --verbose
        """
    )
    
    parser.add_argument(
        "project_id",
        help="项目 ID"
    )
    
    parser.add_argument(
        "--chapter",
        type=int,
        help="章节索引（如果指定，则只重建该章节的向量索引）"
    )
    
    parser.add_argument(
        "--project-dir",
        help="项目目录路径（默认为 projects/<project_id>）"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run 模式：仅统计将被影响的向量数量，不实际执行"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细日志输出"
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging(args.verbose)
    
    # 确定项目目录
    project_dir = Path(args.project_dir) if args.project_dir else None
    
    try:
        if args.chapter is not None:
            # 章节级重建
            print(f"\n🔄 开始重建项目 '{args.project_id}' 章节 {args.chapter} 的向量索引...")
            if args.dry_run:
                print("   [DRY-RUN 模式]")
            
            stats = reindex_chapter_vectors(
                project_id=args.project_id,
                chapter_index=args.chapter,
                project_dir=project_dir,
                dry_run=args.dry_run
            )
        else:
            # 项目级重建
            print(f"\n🔄 开始重建项目 '{args.project_id}' 的向量索引...")
            if args.dry_run:
                print("   [DRY-RUN 模式]")
            
            stats = reindex_project_vectors(
                project_id=args.project_id,
                project_dir=project_dir,
                dry_run=args.dry_run
            )
        
        # 打印统计信息
        print_stats(stats)
        
        # 根据是否有错误决定退出码
        return 1 if stats['errors'] else 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
