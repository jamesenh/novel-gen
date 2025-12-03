#!/usr/bin/env python3
"""
项目记忆查看CLI工具
列出指定项目中的所有 Mem0 记忆内容，包括角色状态、时间线、场景记忆和用户偏好

使用方法:
    uv run python scripts/list_project_memory.py <project_id> --summary
    uv run python scripts/list_project_memory.py <project_id> --characters
    uv run python scripts/list_project_memory.py <project_id> --timeline
    uv run python scripts/list_project_memory.py <project_id> --scenes
    uv run python scripts/list_project_memory.py <project_id> --preferences
    uv run python scripts/list_project_memory.py <project_id> --all
    uv run python scripts/list_project_memory.py <project_id> --characters -v

开发者: Jamesenh, 开发时间: 2025-11-28
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novelgen.runtime.mem0_manager import Mem0Manager, Mem0InitializationError
from novelgen.config import ProjectConfig


def format_timestamp(ts: str) -> str:
    """格式化时间戳字符串"""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(ts) if ts else "N/A"


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本"""
    if not text:
        return "N/A"
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def print_separator(char: str = "=", length: int = 70):
    """打印分隔线"""
    print(char * length)


def print_header(title: str):
    """打印标题"""
    print_separator()
    print(f"  {title}")
    print_separator()


def print_subheader(title: str):
    """打印子标题"""
    print(f"\n{'-' * 50}")
    print(f"  {title}")
    print(f"{'-' * 50}")


# ==================== 角色相关函数 ====================

def load_characters(project_dir: Path) -> Dict[str, Any]:
    """从 characters.json 加载角色列表"""
    characters_file = project_dir / "characters.json"
    if not characters_file.exists():
        return {}
    
    with open(characters_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_character_names(characters_data: Dict[str, Any]) -> List[str]:
    """从角色数据中提取所有角色名"""
    names = []
    
    # 主角
    if "protagonist" in characters_data and characters_data["protagonist"]:
        names.append(characters_data["protagonist"]["name"])
    
    # 反派
    if "antagonist" in characters_data and characters_data["antagonist"]:
        names.append(characters_data["antagonist"]["name"])
    
    # 配角
    if "supporting_characters" in characters_data:
        for char in characters_data["supporting_characters"]:
            if char and "name" in char:
                names.append(char["name"])
    
    return names


def print_character_states(
    project_id: str,
    mem0_manager: Mem0Manager,
    characters_data: Dict[str, Any],
    verbose: bool = False
):
    """打印所有角色的 Mem0 状态"""
    print_header(f"角色状态记忆 - 项目: {project_id}")
    
    character_names = get_character_names(characters_data)
    
    if not character_names:
        print("⚠️  未找到角色数据（characters.json 为空或不存在）")
        return
    
    print(f"📋 共找到 {len(character_names)} 个角色\n")
    
    total_states = 0
    for name in character_names:
        print_subheader(f"角色: {name}")
        
        try:
            # 获取该角色的所有状态
            states = mem0_manager.get_all_entity_states(entity_id=name)
            
            if not states:
                print(f"  ❌ 未找到 Mem0 记忆")
                continue
            
            total_states += len(states)
            print(f"  ✅ 找到 {len(states)} 条状态记忆\n")
            
            for i, state in enumerate(states, 1):
                memory = state.get("memory", "")
                metadata = state.get("metadata", {})
                
                chapter_info = ""
                if metadata.get("chapter_index") is not None:
                    chapter_info = f"章节 {metadata['chapter_index']}"
                    if metadata.get("scene_index") is not None:
                        chapter_info += f"-场景 {metadata['scene_index']}"
                
                timestamp = format_timestamp(metadata.get("timestamp"))
                
                print(f"  [{i}] {chapter_info or '未知位置'} | {timestamp}")
                
                if verbose:
                    print(f"      记忆内容: {memory}")
                    print(f"      元数据: {json.dumps(metadata, ensure_ascii=False)}")
                else:
                    print(f"      摘要: {truncate_text(memory, 80)}")
                print()
                
        except Exception as e:
            print(f"  ❌ 查询失败: {e}")
    
    print_separator("-")
    print(f"📊 角色状态统计: {len(character_names)} 个角色, 共 {total_states} 条记忆")


# ==================== 时间线相关函数 ====================

def load_chapter_memory(project_dir: Path) -> List[Dict[str, Any]]:
    """从 chapter_memory.json 加载章节记忆"""
    memory_file = project_dir / "chapter_memory.json"
    if not memory_file.exists():
        return []
    
    with open(memory_file, "r", encoding="utf-8") as f:
        return json.load(f)


def print_timeline(project_id: str, project_dir: Path, verbose: bool = False):
    """打印时间线和章节记忆"""
    print_header(f"时间线 & 章节记忆 - 项目: {project_id}")
    
    chapter_memories = load_chapter_memory(project_dir)
    
    if not chapter_memories:
        print("⚠️  未找到章节记忆（chapter_memory.json 为空或不存在）")
        return
    
    print(f"📋 共找到 {len(chapter_memories)} 章记忆\n")
    
    for entry in chapter_memories:
        chapter_num = entry.get("chapter_number", "?")
        chapter_title = entry.get("chapter_title", "未命名")
        timeline_anchor = entry.get("timeline_anchor", "未知")
        
        print_subheader(f"第 {chapter_num} 章: {chapter_title}")
        print(f"  ⏰ 时间线锚点: {timeline_anchor}")
        
        # 主要地点
        location = entry.get("location_summary", "")
        if location:
            if verbose:
                print(f"  📍 地点: {location}")
            else:
                print(f"  📍 地点: {truncate_text(location, 60)}")
        
        # 关键事件
        key_events = entry.get("key_events", [])
        if key_events:
            print(f"  📌 关键事件 ({len(key_events)} 个):")
            display_count = len(key_events) if verbose else min(3, len(key_events))
            for i, event in enumerate(key_events[:display_count], 1):
                if verbose:
                    print(f"      {i}. {event}")
                else:
                    print(f"      {i}. {truncate_text(event, 70)}")
            if not verbose and len(key_events) > 3:
                print(f"      ... 还有 {len(key_events) - 3} 个事件")
        
        # 角色状态
        char_states = entry.get("character_states", {})
        if char_states:
            print(f"  👥 角色状态 ({len(char_states)} 个):")
            for name, state in char_states.items():
                if verbose:
                    print(f"      • {name}: {state}")
                else:
                    print(f"      • {name}: {truncate_text(state, 60)}")
        
        # 未解决的悬念
        unresolved = entry.get("unresolved_threads", [])
        if unresolved and verbose:
            print(f"  ❓ 未解决悬念 ({len(unresolved)} 个):")
            for thread in unresolved:
                print(f"      • {thread}")
        
        # 摘要
        summary = entry.get("summary", "")
        if summary:
            print(f"  📝 章节摘要:")
            if verbose:
                print(f"      {summary}")
            else:
                print(f"      {truncate_text(summary, 150)}")
        
        print()
    
    print_separator("-")
    print(f"📊 时间线统计: 共 {len(chapter_memories)} 章记忆")


# ==================== 场景记忆函数 ====================

def get_chapter_scene_info(project_dir: Path) -> List[Dict[str, Any]]:
    """扫描 chapters 目录获取章节场景信息"""
    chapters_dir = project_dir / "chapters"
    if not chapters_dir.exists():
        return []
    
    results = []
    
    # 查找所有 chapter_XXX.json 文件（不是 plan 文件）
    for chapter_file in sorted(chapters_dir.glob("chapter_*.json")):
        if "_plan" in chapter_file.name:
            continue
        
        try:
            with open(chapter_file, "r", encoding="utf-8") as f:
                chapter_data = json.load(f)
            
            chapter_num = chapter_data.get("chapter_number", 0)
            scenes = chapter_data.get("scenes", [])
            
            results.append({
                "chapter_number": chapter_num,
                "chapter_title": chapter_data.get("chapter_title", ""),
                "scene_count": len(scenes),
                "total_words": chapter_data.get("total_words", 0),
            })
        except Exception:
            continue
    
    return results


def print_scene_memories(
    project_id: str,
    mem0_manager: Mem0Manager,
    project_dir: Path,
    verbose: bool = False
):
    """打印场景记忆统计"""
    print_header(f"场景记忆 - 项目: {project_id}")
    
    # 获取章节场景信息
    chapter_info = get_chapter_scene_info(project_dir)
    
    if not chapter_info:
        print("⚠️  未找到已生成的章节（chapters/ 目录为空）")
        return
    
    print(f"📋 已生成 {len(chapter_info)} 章内容\n")
    
    total_memories = 0
    
    for info in chapter_info:
        chapter_num = info["chapter_number"]
        scene_count = info["scene_count"]
        
        print_subheader(f"第 {chapter_num} 章: {info['chapter_title']}")
        print(f"  📄 场景数: {scene_count}, 总字数: {info['total_words']}")
        
        # 搜索该章节的场景记忆
        try:
            chunks = mem0_manager.search_scene_content(
                query=f"第{chapter_num}章的内容",
                chapter_index=chapter_num,
                limit=50
            )
            
            if chunks:
                total_memories += len(chunks)
                print(f"  ✅ Mem0 记忆块: {len(chunks)} 个")
                
                if verbose:
                    # 按场景分组
                    scene_chunks: Dict[int, List] = {}
                    for chunk in chunks:
                        scene_idx = chunk.scene_index or 0
                        if scene_idx not in scene_chunks:
                            scene_chunks[scene_idx] = []
                        scene_chunks[scene_idx].append(chunk)
                    
                    for scene_idx in sorted(scene_chunks.keys()):
                        print(f"      场景 {scene_idx}: {len(scene_chunks[scene_idx])} 个块")
                        for chunk in scene_chunks[scene_idx][:2]:  # 每场景最多显示2个
                            print(f"        - {truncate_text(chunk.content, 60)}")
            else:
                print(f"  ⚠️  未找到 Mem0 记忆块")
                
        except Exception as e:
            print(f"  ❌ 查询失败: {e}")
        
        print()
    
    print_separator("-")
    print(f"📊 场景记忆统计: {len(chapter_info)} 章, 共 {total_memories} 个记忆块")


# ==================== 用户偏好函数 ====================

def print_user_preferences(
    project_id: str,
    mem0_manager: Mem0Manager,
    verbose: bool = False
):
    """打印用户偏好"""
    print_header(f"用户偏好 - 项目: {project_id}")
    
    try:
        preferences = mem0_manager.get_all_user_preferences()
        
        if not preferences:
            print("⚠️  未找到用户偏好记录")
            return
        
        print(f"📋 共找到 {len(preferences)} 条偏好记录\n")
        
        for i, pref in enumerate(preferences, 1):
            memory = pref.get("memory", "")
            metadata = pref.get("metadata", {})
            
            pref_type = metadata.get("preference_type", "未知类型")
            source = metadata.get("source", "未知来源")
            timestamp = format_timestamp(metadata.get("timestamp"))
            
            print(f"  [{i}] 类型: {pref_type} | 来源: {source}")
            print(f"      时间: {timestamp}")
            
            if verbose:
                print(f"      内容: {memory}")
                print(f"      元数据: {json.dumps(metadata, ensure_ascii=False)}")
            else:
                print(f"      摘要: {truncate_text(memory, 80)}")
            print()
        
        print_separator("-")
        print(f"📊 用户偏好统计: 共 {len(preferences)} 条记录")
        
    except Exception as e:
        print(f"❌ 查询用户偏好失败: {e}")


# ==================== 概览函数 ====================

def print_summary(
    project_id: str,
    mem0_manager: Mem0Manager,
    project_dir: Path,
    characters_data: Dict[str, Any]
):
    """打印记忆概览"""
    print_header(f"记忆概览 - 项目: {project_id}")
    
    stats = {
        "characters": 0,
        "character_states": 0,
        "chapters": 0,
        "chapter_memories": 0,
        "scene_memories": 0,
        "user_preferences": 0,
    }
    
    # 角色统计
    character_names = get_character_names(characters_data)
    stats["characters"] = len(character_names)
    
    for name in character_names:
        try:
            states = mem0_manager.get_all_entity_states(entity_id=name)
            stats["character_states"] += len(states)
        except Exception:
            pass
    
    # 章节记忆统计
    chapter_memories = load_chapter_memory(project_dir)
    stats["chapter_memories"] = len(chapter_memories)
    
    # 章节场景统计
    chapter_info = get_chapter_scene_info(project_dir)
    stats["chapters"] = len(chapter_info)
    
    for info in chapter_info:
        try:
            chunks = mem0_manager.search_scene_content(
                query=f"第{info['chapter_number']}章",
                chapter_index=info["chapter_number"],
                limit=100
            )
            stats["scene_memories"] += len(chunks)
        except Exception:
            pass
    
    # 用户偏好统计
    try:
        preferences = mem0_manager.get_all_user_preferences()
        stats["user_preferences"] = len(preferences)
    except Exception:
        pass
    
    # 打印统计
    print(f"""
  📁 项目目录: {project_dir}
  
  👥 角色数据:
     • 角色数量: {stats['characters']}
     • Mem0 状态记忆: {stats['character_states']} 条
  
  📖 章节数据:
     • 已生成章节: {stats['chapters']}
     • 章节记忆表: {stats['chapter_memories']} 条
     • Mem0 场景记忆: {stats['scene_memories']} 个块
  
  ⚙️  用户偏好:
     • 偏好记录: {stats['user_preferences']} 条
""")
    
    print_separator("-")
    total = stats['character_states'] + stats['scene_memories'] + stats['user_preferences']
    print(f"📊 Mem0 记忆总计: {total} 条")


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(
        description="列出项目中的所有 Mem0 记忆内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看记忆概览
  uv run python scripts/list_project_memory.py demo_013 --summary
  
  # 列出所有角色状态
  uv run python scripts/list_project_memory.py demo_013 --characters
  
  # 查看时间线和章节记忆
  uv run python scripts/list_project_memory.py demo_013 --timeline
  
  # 查看场景记忆
  uv run python scripts/list_project_memory.py demo_013 --scenes
  
  # 查看用户偏好
  uv run python scripts/list_project_memory.py demo_013 --preferences
  
  # 查看所有记忆
  uv run python scripts/list_project_memory.py demo_013 --all
  
  # 详细输出
  uv run python scripts/list_project_memory.py demo_013 --characters -v
        """
    )
    
    parser.add_argument("project_id", help="项目ID（如 demo_013）")
    
    # 查看模式
    mode_group = parser.add_argument_group("查看模式（至少选择一个）")
    mode_group.add_argument("--summary", action="store_true", help="显示记忆概览统计")
    mode_group.add_argument("--characters", action="store_true", help="列出所有角色的 Mem0 状态")
    mode_group.add_argument("--timeline", action="store_true", help="显示时间线和章节记忆")
    mode_group.add_argument("--scenes", action="store_true", help="显示场景记忆统计")
    mode_group.add_argument("--preferences", action="store_true", help="显示用户偏好")
    mode_group.add_argument("--all", action="store_true", help="显示所有记忆内容")
    
    # 通用选项
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细内容")
    
    args = parser.parse_args()
    
    # 检查是否选择了至少一个模式
    if not any([args.summary, args.characters, args.timeline, args.scenes, 
                args.preferences, args.all]):
        parser.error("请至少选择一个查看模式（--summary, --characters, --timeline, "
                    "--scenes, --preferences, 或 --all）")
    
    # 初始化项目配置
    project_dir = project_root / "projects" / args.project_id
    if not project_dir.exists():
        print(f"❌ 项目不存在: {project_dir}")
        return 1
    
    config = ProjectConfig(project_dir=str(project_dir))
    
    # 检查 Mem0 是否启用
    if not config.mem0_config or not config.mem0_config.enabled:
        print("❌ 错误: Mem0 未启用。请设置环境变量 MEM0_ENABLED=true")
        return 1
    
    # 初始化 Mem0 管理器
    try:
        mem0_manager = Mem0Manager(
            config=config.mem0_config,
            project_id=args.project_id,
            embedding_config=config.embedding_config
        )
    except Mem0InitializationError as e:
        print(f"❌ Mem0 初始化失败: {e}")
        return 1
    
    print(f"\n🔗 Mem0 已连接: {config.mem0_config.chroma_path}")
    print(f"📂 项目: {args.project_id}\n")
    
    # 加载角色数据
    characters_data = load_characters(project_dir)
    
    try:
        # 根据选择的模式执行
        if args.all:
            print_summary(args.project_id, mem0_manager, project_dir, characters_data)
            print("\n")
            print_character_states(args.project_id, mem0_manager, characters_data, args.verbose)
            print("\n")
            print_timeline(args.project_id, project_dir, args.verbose)
            print("\n")
            print_scene_memories(args.project_id, mem0_manager, project_dir, args.verbose)
            print("\n")
            print_user_preferences(args.project_id, mem0_manager, args.verbose)
        else:
            if args.summary:
                print_summary(args.project_id, mem0_manager, project_dir, characters_data)
            if args.characters:
                if args.summary:
                    print("\n")
                print_character_states(args.project_id, mem0_manager, characters_data, args.verbose)
            if args.timeline:
                if args.summary or args.characters:
                    print("\n")
                print_timeline(args.project_id, project_dir, args.verbose)
            if args.scenes:
                if args.summary or args.characters or args.timeline:
                    print("\n")
                print_scene_memories(args.project_id, mem0_manager, project_dir, args.verbose)
            if args.preferences:
                if args.summary or args.characters or args.timeline or args.scenes:
                    print("\n")
                print_user_preferences(args.project_id, mem0_manager, args.verbose)
        
        return 0
        
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

