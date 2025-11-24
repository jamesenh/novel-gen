"""
状态同步工具
提供 LangGraph 状态与 JSON 文件之间的双向同步功能

开发者: jamesenh, 开发时间: 2025-11-22
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from novelgen.models import (
    NovelGenerationState, Settings, WorldSetting, ThemeConflict,
    CharactersConfig, Outline, ChapterPlan, GeneratedChapter,
    ChapterMemoryEntry
)


def state_to_json_files(state: NovelGenerationState, project_dir: Optional[str] = None) -> Dict[str, str]:
    """
    将 LangGraph 状态导出到 JSON 文件
    
    Args:
        state: NovelGenerationState 对象
        project_dir: 项目目录（可选，默认使用 state.project_dir）
    
    Returns:
        已保存文件的路径字典 {文件类型: 文件路径}
    """
    if project_dir is None:
        project_dir = state.project_dir
    
    os.makedirs(project_dir, exist_ok=True)
    chapters_dir = os.path.join(project_dir, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)
    
    saved_files = {}
    
    # 保存 settings（如果存在）
    if state.settings:
        settings_path = os.path.join(project_dir, "settings.json")
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(state.settings.model_dump(), f, ensure_ascii=False, indent=2)
        saved_files['settings'] = settings_path
    
    # 保存 world（如果存在）
    if state.world:
        world_path = os.path.join(project_dir, "world.json")
        with open(world_path, 'w', encoding='utf-8') as f:
            json.dump(state.world.model_dump(), f, ensure_ascii=False, indent=2)
        saved_files['world'] = world_path
    
    # 保存 theme_conflict（如果存在）
    if state.theme_conflict:
        theme_path = os.path.join(project_dir, "theme_conflict.json")
        with open(theme_path, 'w', encoding='utf-8') as f:
            json.dump(state.theme_conflict.model_dump(), f, ensure_ascii=False, indent=2)
        saved_files['theme_conflict'] = theme_path
    
    # 保存 characters（如果存在）
    if state.characters:
        characters_path = os.path.join(project_dir, "characters.json")
        with open(characters_path, 'w', encoding='utf-8') as f:
            json.dump(state.characters.model_dump(), f, ensure_ascii=False, indent=2)
        saved_files['characters'] = characters_path
    
    # 保存 outline（如果存在）
    if state.outline:
        outline_path = os.path.join(project_dir, "outline.json")
        with open(outline_path, 'w', encoding='utf-8') as f:
            json.dump(state.outline.model_dump(), f, ensure_ascii=False, indent=2)
        saved_files['outline'] = outline_path
    
    # 保存章节计划（如果存在）
    for chapter_number, plan in state.chapters_plan.items():
        plan_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}_plan.json")
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)
        saved_files[f'chapter_{chapter_number}_plan'] = plan_path
    
    # 保存生成的章节（如果存在）
    for chapter_number, chapter in state.chapters.items():
        chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")
        with open(chapter_path, 'w', encoding='utf-8') as f:
            json.dump(chapter.model_dump(), f, ensure_ascii=False, indent=2)
        saved_files[f'chapter_{chapter_number}'] = chapter_path
    
    # 保存章节记忆（如果存在）
    if state.chapter_memories:
        memory_path = os.path.join(project_dir, "chapter_memory.json")
        serializable = [entry.model_dump() for entry in state.chapter_memories]
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        saved_files['chapter_memories'] = memory_path
    
    return saved_files


def json_files_to_state(project_dir: str, project_name: Optional[str] = None) -> NovelGenerationState:
    """
    从 JSON 文件加载并构造 LangGraph 状态
    
    Args:
        project_dir: 项目目录路径
        project_name: 项目名称（可选，默认从目录名推断）
    
    Returns:
        NovelGenerationState 对象
    """
    if project_name is None:
        project_name = os.path.basename(project_dir)
    
    chapters_dir = os.path.join(project_dir, "chapters")
    
    # 加载 settings
    settings = None
    settings_path = os.path.join(project_dir, "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
            settings = Settings(**settings_data)
    
    # 加载 world
    world = None
    world_path = os.path.join(project_dir, "world.json")
    if os.path.exists(world_path):
        with open(world_path, 'r', encoding='utf-8') as f:
            world_data = json.load(f)
            world = WorldSetting(**world_data)
    
    # 加载 theme_conflict
    theme_conflict = None
    theme_path = os.path.join(project_dir, "theme_conflict.json")
    if os.path.exists(theme_path):
        with open(theme_path, 'r', encoding='utf-8') as f:
            theme_data = json.load(f)
            theme_conflict = ThemeConflict(**theme_data)
    
    # 加载 characters
    characters = None
    characters_path = os.path.join(project_dir, "characters.json")
    if os.path.exists(characters_path):
        with open(characters_path, 'r', encoding='utf-8') as f:
            characters_data = json.load(f)
            characters = CharactersConfig(**characters_data)
    
    # 加载 outline
    outline = None
    outline_path = os.path.join(project_dir, "outline.json")
    if os.path.exists(outline_path):
        with open(outline_path, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
            outline = Outline(**outline_data)
    
    # 加载章节计划
    chapters_plan = {}
    if os.path.exists(chapters_dir):
        for filename in os.listdir(chapters_dir):
            if filename.endswith('_plan.json'):
                plan_path = os.path.join(chapters_dir, filename)
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    plan = ChapterPlan(**plan_data)
                    chapters_plan[plan.chapter_number] = plan
    
    # 加载生成的章节
    chapters = {}
    if os.path.exists(chapters_dir):
        for filename in os.listdir(chapters_dir):
            if filename.startswith('chapter_') and filename.endswith('.json') and '_plan' not in filename:
                chapter_path = os.path.join(chapters_dir, filename)
                with open(chapter_path, 'r', encoding='utf-8') as f:
                    chapter_data = json.load(f)
                    chapter = GeneratedChapter(**chapter_data)
                    chapters[chapter.chapter_number] = chapter
    
    # 加载章节记忆
    chapter_memories = []
    memory_path = os.path.join(project_dir, "chapter_memory.json")
    if os.path.exists(memory_path):
        with open(memory_path, 'r', encoding='utf-8') as f:
            memory_data = json.load(f)
            for item in memory_data:
                chapter_memories.append(ChapterMemoryEntry(**item))
    
    # 构造状态对象
    state = NovelGenerationState(
        project_name=project_name,
        project_dir=project_dir,
        settings=settings,
        world=world,
        theme_conflict=theme_conflict,
        characters=characters,
        outline=outline,
        chapters_plan=chapters_plan,
        chapters=chapters,
        chapter_memories=chapter_memories
    )
    
    return state


def sync_state_from_json(state: NovelGenerationState) -> NovelGenerationState:
    """
    从 JSON 文件同步更新状态
    
    用于在工作流执行过程中，从磁盘重新加载最新的数据
    
    Args:
        state: 当前状态对象
    
    Returns:
        更新后的状态对象
    """
    fresh_state = json_files_to_state(state.project_dir, state.project_name)
    
    # 保留工作流控制字段
    fresh_state.current_step = state.current_step
    fresh_state.completed_steps = state.completed_steps
    fresh_state.failed_steps = state.failed_steps
    fresh_state.error_messages = state.error_messages
    
    # 保留管理器引用
    fresh_state.db_manager = state.db_manager
    fresh_state.vector_manager = state.vector_manager
    
    return fresh_state


def validate_state_json_consistency(state: NovelGenerationState) -> Dict[str, bool]:
    """
    验证状态与 JSON 文件的一致性
    
    Args:
        state: NovelGenerationState 对象
    
    Returns:
        验证结果字典 {文件类型: 是否一致}
    """
    results = {}
    
    # 检查各个文件是否与状态一致
    if state.world:
        world_path = os.path.join(state.project_dir, "world.json")
        if os.path.exists(world_path):
            with open(world_path, 'r', encoding='utf-8') as f:
                disk_data = json.load(f)
                state_data = state.world.model_dump()
                results['world'] = disk_data == state_data
        else:
            results['world'] = False
    
    if state.theme_conflict:
        theme_path = os.path.join(state.project_dir, "theme_conflict.json")
        if os.path.exists(theme_path):
            with open(theme_path, 'r', encoding='utf-8') as f:
                disk_data = json.load(f)
                state_data = state.theme_conflict.model_dump()
                results['theme_conflict'] = disk_data == state_data
        else:
            results['theme_conflict'] = False
    
    # 可以继续添加其他文件的一致性检查...
    
    return results
