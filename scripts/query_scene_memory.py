#!/usr/bin/env python3
"""
场景记忆查询CLI工具
用于查询指定场景相关的记忆块
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from novelgen.runtime.vector_store import VectorStoreManager
from novelgen.config import ProjectConfig


def format_timestamp(ts: datetime) -> str:
    """格式化时间戳"""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def print_memory_chunk(chunk, index: int, total: int, verbose: bool = False):
    """打印记忆块信息"""
    print(f"\n{'='*60}")
    print(f"记忆块 {index}/{total}")
    print(f"{'-'*60}")
    print(f"ID: {chunk.chunk_id}")
    print(f"章节: {chunk.chapter_index}, 场景: {chunk.scene_index}")
    print(f"内容类型: {chunk.content_type}")
    print(f"创建时间: {format_timestamp(chunk.created_at)}")
    
    if chunk.entities_mentioned:
        print(f"提及实体: {', '.join(chunk.entities_mentioned)}")
    
    if chunk.tags:
        print(f"标签: {', '.join(chunk.tags)}")
    
    print(f"{'-'*60}")
    if verbose:
        print("内容:")
        print(chunk.content)
    else:
        # 简要显示内容
        content = chunk.content
        if len(content) > 200:
            content = content[:200] + "..."
        print(f"内容摘要: {content}")
    print(f"{'='*60}")


def query_scene_memory(project_id: str, chapter_index: int, scene_index: int,
                       vector_store_path: str, embedding_config = None, 
                       limit: int = 10, verbose: bool = False):
    """查询场景相关的记忆块"""
    print(f"\n正在查询项目 '{project_id}' 章节 {chapter_index} 场景 {scene_index} 的记忆块...")
    
    # 初始化向量存储管理器
    vector_manager = VectorStoreManager(
        persist_directory=vector_store_path, 
        enabled=True,
        embedding_config=embedding_config
    )
    
    if not vector_manager.is_enabled():
        print("❌ 错误: 向量存储未能成功初始化")
        return 1
    
    # 查询记忆块
    chunks = vector_manager.get_chunks_by_project(project_id, chapter_index)
    
    # 过滤指定场景的记忆块
    scene_chunks = [
        chunk for chunk in chunks 
        if chunk.scene_index == scene_index
    ]
    
    # 限制数量
    if len(scene_chunks) > limit:
        print(f"⚠️  找到 {len(scene_chunks)} 个记忆块，仅显示前 {limit} 个")
        scene_chunks = scene_chunks[:limit]
    
    if scene_chunks:
        print(f"✅ 找到 {len(scene_chunks)} 个记忆块:")
        for i, chunk in enumerate(scene_chunks, 1):
            print_memory_chunk(chunk, i, len(scene_chunks), verbose)
        return 0
    else:
        print(f"❌ 未找到章节 {chapter_index} 场景 {scene_index} 的记忆块")
        return 1


def query_by_entity(project_id: str, entity_ids: list, chapter_index: int = None,
                    vector_store_path: str = None, embedding_config = None,
                    limit: int = 10, verbose: bool = False):
    """根据实体ID查询相关记忆块"""
    entity_str = ', '.join(entity_ids)
    print(f"\n正在查询项目 '{project_id}' 中与实体 [{entity_str}] 相关的记忆块...")
    if chapter_index is not None:
        print(f"限定章节: {chapter_index}")
    
    # 初始化向量存储管理器
    vector_manager = VectorStoreManager(
        persist_directory=vector_store_path, 
        enabled=True,
        embedding_config=embedding_config
    )
    
    if not vector_manager.is_enabled():
        print("❌ 错误: 向量存储未能成功初始化")
        return 1
    
    # 查询记忆块
    chunks = vector_manager.get_chunks_by_entities(project_id, entity_ids, chapter_index)
    
    # 限制数量
    if len(chunks) > limit:
        print(f"⚠️  找到 {len(chunks)} 个记忆块，仅显示前 {limit} 个")
        chunks = chunks[:limit]
    
    if chunks:
        print(f"✅ 找到 {len(chunks)} 个记忆块:")
        for i, chunk in enumerate(chunks, 1):
            print_memory_chunk(chunk, i, len(chunks), verbose)
        return 0
    else:
        print(f"❌ 未找到与实体相关的记忆块")
        return 1


def search_memory(project_id: str, query: str, vector_store_path: str,
                 content_type: str = None, entities: list = None,
                 tags: list = None, embedding_config = None,
                 limit: int = 10, verbose: bool = False):
    """搜索记忆块"""
    print(f"\n正在搜索项目 '{project_id}' 中的记忆块...")
    print(f"查询: {query}")
    if content_type:
        print(f"内容类型: {content_type}")
    if entities:
        print(f"实体过滤: {', '.join(entities)}")
    if tags:
        print(f"标签过滤: {', '.join(tags)}")
    
    # 初始化向量存储管理器
    vector_manager = VectorStoreManager(
        persist_directory=vector_store_path, 
        enabled=True,
        embedding_config=embedding_config
    )
    
    if not vector_manager.is_enabled():
        print("❌ 错误: 向量存储未能成功初始化")
        return 1
    
    # 搜索记忆块
    chunks = vector_manager.search_memory_with_filters(
        query, project_id, content_type, entities, tags, limit
    )
    
    if chunks:
        print(f"✅ 找到 {len(chunks)} 个相关记忆块:")
        for i, chunk in enumerate(chunks, 1):
            print_memory_chunk(chunk, i, len(chunks), verbose)
        return 0
    else:
        print(f"❌ 未找到相关记忆块")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="查询场景记忆块",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查询指定场景的记忆块
  python scripts/query_scene_memory.py my_project --chapter 1 --scene 0
  
  # 根据实体查询记忆块
  python scripts/query_scene_memory.py my_project --entity char_001 char_002
  
  # 搜索记忆块
  python scripts/query_scene_memory.py my_project --search "主角决定离开"
  
  # 限制返回数量并显示详细内容
  python scripts/query_scene_memory.py my_project --chapter 1 --scene 0 --limit 5 --verbose
        """
    )
    
    parser.add_argument("project_id", help="项目ID")
    parser.add_argument("--vector-store", default=None, help="向量存储路径（默认从配置读取）")
    
    # 查询模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--scene", action="store_true", help="按场景查询（需配合--chapter和--scene-index）")
    mode_group.add_argument("--entity", nargs="+", help="按实体ID查询")
    mode_group.add_argument("--search", help="搜索记忆块")
    
    # 场景查询选项
    parser.add_argument("--chapter", type=int, help="章节索引")
    parser.add_argument("--scene-index", type=int, help="场景索引")
    
    # 搜索选项
    parser.add_argument("--content-type", help="内容类型过滤")
    parser.add_argument("--entities", nargs="+", help="实体过滤（用于搜索）")
    parser.add_argument("--tags", nargs="+", help="标签过滤")
    
    # 通用选项
    parser.add_argument("--limit", type=int, default=10, help="返回记忆块数量限制（默认10）")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示完整内容")
    
    args = parser.parse_args()
    
    # 确定向量存储路径和embedding配置
    if args.vector_store:
        vector_store_path = args.vector_store
        embedding_config = None  # 使用默认配置
    else:
        config = ProjectConfig(project_dir=f"projects/{args.project_id}")
        vector_store_path = config.get_vector_store_dir()
        embedding_config = config.embedding_config
    
    print(f"使用向量存储: {vector_store_path}")
    if embedding_config:
        print(f"使用 embedding 模型: {embedding_config.model_name}")
    
    # 执行查询
    try:
        if args.scene:
            if args.chapter is None or args.scene_index is None:
                print("❌ 错误: --scene 模式需要同时指定 --chapter 和 --scene-index")
                return 1
            return query_scene_memory(
                args.project_id, args.chapter, args.scene_index,
                vector_store_path, embedding_config, args.limit, args.verbose
            )
        elif args.entity:
            return query_by_entity(
                args.project_id, args.entity, args.chapter,
                vector_store_path, embedding_config, args.limit, args.verbose
            )
        elif args.search:
            return search_memory(
                args.project_id, args.search, vector_store_path,
                args.content_type, args.entities, args.tags,
                embedding_config, args.limit, args.verbose
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
