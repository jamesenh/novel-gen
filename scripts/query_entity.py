#!/usr/bin/env python3
"""
实体状态查询CLI工具
用于查询指定项目中某个实体的最新状态或完整时间线
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from novelgen.runtime.db import DatabaseManager
from novelgen.config import ProjectConfig


def format_timestamp(ts: datetime) -> str:
    """格式化时间戳"""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def print_entity_state(snapshot, verbose: bool = False):
    """打印实体状态"""
    print(f"\n{'='*60}")
    print(f"实体ID: {snapshot.entity_id}")
    print(f"实体类型: {snapshot.entity_type}")
    print(f"章节: {snapshot.chapter_index}, 场景: {snapshot.scene_index}")
    print(f"时间戳: {format_timestamp(snapshot.timestamp)}")
    print(f"版本: {snapshot.version}")
    print(f"{'-'*60}")
    
    if verbose:
        print("状态数据:")
        print(json.dumps(snapshot.state_data, ensure_ascii=False, indent=2))
    else:
        # 简要显示状态数据的关键字段
        state_data = snapshot.state_data
        if isinstance(state_data, dict):
            print("关键状态字段:")
            for key, value in list(state_data.items())[:5]:  # 只显示前5个字段
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {key}: {value}")
            if len(state_data) > 5:
                print(f"  ... (还有 {len(state_data) - 5} 个字段)")
    print(f"{'='*60}")


def query_latest(project_id: str, entity_id: str, db_path: str, verbose: bool = False):
    """查询实体最新状态"""
    print(f"\n正在查询项目 '{project_id}' 中实体 '{entity_id}' 的最新状态...")
    
    # 初始化数据库管理器
    db_manager = DatabaseManager(db_path=db_path, enabled=True)
    
    if not db_manager.is_enabled():
        print("❌ 错误: 数据库未能成功初始化")
        return 1
    
    # 查询最新状态
    snapshot = db_manager.get_latest_entity_state(project_id, entity_id)
    
    if snapshot:
        print(f"✅ 找到最新状态:")
        print_entity_state(snapshot, verbose)
        return 0
    else:
        print(f"❌ 未找到实体 '{entity_id}' 的状态记录")
        return 1


def query_timeline(project_id: str, entity_id: str, db_path: str, 
                   start_chapter: int = None, end_chapter: int = None,
                   verbose: bool = False):
    """查询实体时间线"""
    print(f"\n正在查询项目 '{project_id}' 中实体 '{entity_id}' 的时间线...")
    if start_chapter is not None or end_chapter is not None:
        print(f"章节范围: {start_chapter or '开始'} ~ {end_chapter or '结束'}")
    
    # 初始化数据库管理器
    db_manager = DatabaseManager(db_path=db_path, enabled=True)
    
    if not db_manager.is_enabled():
        print("❌ 错误: 数据库未能成功初始化")
        return 1
    
    # 查询时间线
    snapshots = db_manager.get_entity_timeline(
        project_id, entity_id, start_chapter, end_chapter
    )
    
    if snapshots:
        print(f"✅ 找到 {len(snapshots)} 个状态快照:")
        for i, snapshot in enumerate(snapshots, 1):
            print(f"\n--- 快照 {i}/{len(snapshots)} ---")
            print_entity_state(snapshot, verbose)
        return 0
    else:
        print(f"❌ 未找到实体 '{entity_id}' 的时间线记录")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="查询实体状态",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查询最新状态
  python scripts/query_entity.py my_project char_001 --latest
  
  # 查询完整时间线
  python scripts/query_entity.py my_project char_001 --timeline
  
  # 查询指定章节范围的时间线
  python scripts/query_entity.py my_project char_001 --timeline --start 1 --end 5
  
  # 显示详细状态数据
  python scripts/query_entity.py my_project char_001 --latest --verbose
        """
    )
    
    parser.add_argument("project_id", help="项目ID")
    parser.add_argument("entity_id", help="实体ID")
    parser.add_argument("--db", default=None, help="数据库路径（默认从配置读取）")
    
    # 查询模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--latest", action="store_true", help="查询最新状态")
    mode_group.add_argument("--timeline", action="store_true", help="查询时间线")
    
    # 时间线选项
    parser.add_argument("--start", type=int, help="起始章节索引")
    parser.add_argument("--end", type=int, help="结束章节索引")
    
    # 显示选项
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细状态数据")
    
    args = parser.parse_args()
    
    # 确定数据库路径
    if args.db:
        db_path = args.db
    else:
        config = ProjectConfig(project_dir=f"projects/{args.project_id}")
        db_path = config.get_db_path()
    
    print(f"使用数据库: {db_path}")
    
    # 执行查询
    try:
        if args.latest:
            return query_latest(args.project_id, args.entity_id, db_path, args.verbose)
        elif args.timeline:
            return query_timeline(
                args.project_id, args.entity_id, db_path,
                args.start, args.end, args.verbose
            )
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
