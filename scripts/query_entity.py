#!/usr/bin/env python3
"""
实体状态查询CLI工具
用于查询指定项目中某个实体的最新状态

更新: 2025-11-25 - 使用 Mem0Manager 作为唯一记忆源
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from novelgen.runtime.mem0_manager import Mem0Manager, Mem0InitializationError
from novelgen.config import ProjectConfig


def format_timestamp(ts: datetime) -> str:
    """格式化时间戳"""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def print_entity_state(state: dict, index: int = None, total: int = None, verbose: bool = False):
    """打印实体状态"""
    print(f"\n{'='*60}")
    if index and total:
        print(f"状态 {index}/{total}")
    
    memory = state.get('memory', 'N/A')
    metadata = state.get('metadata', {})
    
    print(f"实体ID: {metadata.get('entity_id', 'N/A')}")
    print(f"实体类型: {metadata.get('entity_type', 'N/A')}")
    print(f"章节: {metadata.get('chapter_index', 'N/A')}, 场景: {metadata.get('scene_index', 'N/A')}")
    print(f"时间戳: {metadata.get('timestamp', 'N/A')}")
    print(f"{'-'*60}")
    
    if verbose:
        print("完整记忆内容:")
        print(memory)
        print(f"\n元数据:")
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        # 简要显示
        if len(memory) > 200:
            memory = memory[:200] + "..."
        print(f"记忆摘要: {memory}")
    print(f"{'='*60}")


def query_latest(project_id: str, entity_id: str, mem0_manager: Mem0Manager, verbose: bool = False):
    """查询实体最新状态"""
    print(f"\n正在查询项目 '{project_id}' 中实体 '{entity_id}' 的最新状态...")
    
    # 查询最新状态
    states = mem0_manager.get_entity_state(
        entity_id=entity_id,
        query=f"{entity_id} 的最新状态",
        limit=1
    )
    
    if states:
        print(f"✅ 找到最新状态:")
        print_entity_state(states[0], verbose=verbose)
        return 0
    else:
        print(f"❌ 未找到实体 '{entity_id}' 的状态记录")
        return 1


def query_all_states(project_id: str, entity_id: str, mem0_manager: Mem0Manager, verbose: bool = False):
    """查询实体的所有历史状态"""
    print(f"\n正在查询项目 '{project_id}' 中实体 '{entity_id}' 的所有状态...")
    
    # 查询所有状态
    states = mem0_manager.get_all_entity_states(entity_id=entity_id)
    
    if states:
        print(f"✅ 找到 {len(states)} 个状态记录:")
        for i, state in enumerate(states, 1):
            print_entity_state(state, index=i, total=len(states), verbose=verbose)
        return 0
    else:
        print(f"❌ 未找到实体 '{entity_id}' 的状态记录")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="查询实体状态（使用 Mem0）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查询最新状态
  python scripts/query_entity.py my_project 张三 --latest
  
  # 查询所有历史状态
  python scripts/query_entity.py my_project 张三 --all
  
  # 显示详细状态数据
  python scripts/query_entity.py my_project 张三 --latest --verbose
        """
    )
    
    parser.add_argument("project_id", help="项目ID")
    parser.add_argument("entity_id", help="实体ID（如角色名）")
    
    # 查询模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--latest", action="store_true", help="查询最新状态")
    mode_group.add_argument("--all", action="store_true", help="查询所有历史状态")
    
    # 显示选项
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细状态数据")
    
    args = parser.parse_args()
    
    # 初始化 Mem0 管理器
    config = ProjectConfig(project_dir=f"projects/{args.project_id}")
    
    if not config.mem0_config or not config.mem0_config.enabled:
        print("❌ 错误: Mem0 未启用。请设置环境变量 MEM0_ENABLED=true")
        return 1
    
    try:
        mem0_manager = Mem0Manager(
            config=config.mem0_config,
            project_id=args.project_id,
            embedding_config=config.embedding_config
        )
    except Mem0InitializationError as e:
        print(f"❌ Mem0 初始化失败: {e}")
        return 1
    
    print(f"使用 Mem0 记忆层: {config.mem0_config.chroma_path}")
    
    # 执行查询
    try:
        if args.latest:
            return query_latest(args.project_id, args.entity_id, mem0_manager, args.verbose)
        elif args.all:
            return query_all_states(args.project_id, args.entity_id, mem0_manager, args.verbose)
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
