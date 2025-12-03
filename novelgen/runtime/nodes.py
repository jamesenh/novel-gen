"""
LangGraph 节点包装器
为现有 LangChain chains 提供 LangGraph 节点接口

开发者: jamesenh, 开发时间: 2025-11-21
更新: 2025-11-27 - 修复 Mem0 集成问题，添加记忆上下文检索功能
更新: 2025-11-28 - 添加动态章节扩展节点（evaluate_story_progress, extend_outline, plan_new_chapters）
更新: 2025-11-29 - 添加 Ctrl+C 信号处理支持
更新: 2025-11-30 - 添加递归限制预估机制，每个节点更新 node_execution_count
"""
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from novelgen.models import (
    NovelGenerationState, Settings, WorldSetting, ThemeConflict,
    CharactersConfig, Outline, ChapterPlan, GeneratedChapter, GeneratedScene,
    ChapterMemoryEntry, ConsistencyReport, SceneMemoryContext,
    StoryProgressEvaluation, SceneGenerationState
)
from novelgen.chains.world_chain import generate_world
from novelgen.chains.theme_conflict_chain import generate_theme_conflict
from novelgen.chains.characters_chain import generate_characters
from novelgen.chains.outline_chain import generate_outline, generate_initial_outline, extend_outline
from novelgen.chains.chapters_plan_chain import generate_chapter_plan
from novelgen.chains.scene_text_chain import generate_scene_text
from novelgen.chains.story_progress_chain import evaluate_story_progress
from novelgen.runtime.consistency import run_consistency_check
from novelgen.chains.chapter_revision_chain import revise_chapter
from novelgen.runtime.memory import generate_chapter_memory_entry
from novelgen.runtime.summary import summarize_scenes


def _increment_node_count(state: NovelGenerationState) -> int:
    """递增节点执行计数
    
    每个节点执行时调用此函数获取新的计数值。
    用于递归限制预估机制。
    
    Args:
        state: 当前工作流状态
        
    Returns:
        int: 递增后的节点执行计数
    
    更新: 2025-11-30 - 新增，支持递归限制预估
    """
    return state.node_execution_count + 1


def load_settings_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    加载项目配置节点
    
    从项目目录加载 settings.json 文件到状态中
    支持旧配置格式自动迁移（num_chapters → initial_chapters + max_chapters）
    
    更新: 2025-11-28 - 添加旧配置格式迁移支持和日志
    更新: 2025-11-30 - 添加 node_execution_count 更新
    """
    new_count = _increment_node_count(state)
    
    try:
        settings_path = os.path.join(state.project_dir, "settings.json")
        
        if not os.path.exists(settings_path):
            return {
                "current_step": "load_settings",
                "failed_steps": state.failed_steps + ["load_settings"],
                "error_messages": {**state.error_messages, "load_settings": f"settings.json 不存在: {settings_path}"},
                "node_execution_count": new_count
            }
        
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        
        # 检测旧配置格式（向后兼容）
        is_old_format = "num_chapters" in settings_data and "initial_chapters" not in settings_data
        
        settings = Settings(**settings_data)
        
        # 如果是旧格式，打印迁移信息
        if is_old_format:
            print(f"⚠️  检测到旧配置格式，已自动迁移:")
            print(f"   num_chapters={settings_data.get('num_chapters')} → initial_chapters={settings.initial_chapters}, max_chapters={settings.max_chapters}")
        
        return {
            "settings": settings,
            "current_step": "load_settings",
            "completed_steps": state.completed_steps + ["load_settings"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "load_settings",
            "failed_steps": state.failed_steps + ["load_settings"],
            "error_messages": {**state.error_messages, "load_settings": str(e)},
            "node_execution_count": new_count
        }


def world_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    世界观生成节点
    
    调用 generate_world chain 生成世界观设定
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.settings is None:
            raise ValueError("settings 未加载，无法生成世界观")
        
        # 调用现有 chain
        world = generate_world(
            user_input=state.settings.world_description,
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )
        
        # 保存到 JSON
        world_path = os.path.join(state.project_dir, "world.json")
        with open(world_path, 'w', encoding='utf-8') as f:
            json.dump(world.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {
            "world": world,
            "current_step": "world_creation",
            "completed_steps": state.completed_steps + ["world_creation"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "world_creation",
            "failed_steps": state.failed_steps + ["world_creation"],
            "error_messages": {**state.error_messages, "world_creation": str(e)},
            "node_execution_count": new_count
        }


def theme_conflict_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    主题冲突生成节点
    
    调用 generate_theme_conflict chain 生成主题与冲突
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.settings is None or state.world is None:
            raise ValueError("settings 或 world 未加载")
        
        theme_conflict = generate_theme_conflict(
            world_setting=state.world,
            user_input=state.settings.theme_description or "",
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )
        
        # 保存到 JSON
        theme_path = os.path.join(state.project_dir, "theme_conflict.json")
        with open(theme_path, 'w', encoding='utf-8') as f:
            json.dump(theme_conflict.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {
            "theme_conflict": theme_conflict,
            "current_step": "theme_conflict_creation",
            "completed_steps": state.completed_steps + ["theme_conflict_creation"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "theme_conflict_creation",
            "failed_steps": state.failed_steps + ["theme_conflict_creation"],
            "error_messages": {**state.error_messages, "theme_conflict_creation": str(e)},
            "node_execution_count": new_count
        }


def character_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    角色生成节点
    
    调用 generate_characters chain 生成角色配置
    并初始化角色状态到 Mem0
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.settings is None or state.world is None or state.theme_conflict is None:
            raise ValueError("settings, world 或 theme_conflict 未加载")
        
        characters = generate_characters(
            world_setting=state.world,
            theme_conflict=state.theme_conflict,
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )
        
        # 保存到 JSON
        characters_path = os.path.join(state.project_dir, "characters.json")
        with open(characters_path, 'w', encoding='utf-8') as f:
            json.dump(characters.model_dump(), f, ensure_ascii=False, indent=2)
        
        # 初始化角色状态到 Mem0
        mem0_manager = _get_mem0_manager(state.project_dir, state.project_name)
        if mem0_manager:
            _initialize_character_states_to_mem0(mem0_manager, characters)
        
        return {
            "characters": characters,
            "current_step": "character_creation",
            "completed_steps": state.completed_steps + ["character_creation"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "character_creation",
            "failed_steps": state.failed_steps + ["character_creation"],
            "error_messages": {**state.error_messages, "character_creation": str(e)},
            "node_execution_count": new_count
        }


def outline_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    大纲生成节点
    
    根据配置决定生成模式：
    - 动态模式（initial_chapters 设置）：调用 generate_initial_outline 只生成开篇章节
    - 固定模式（num_chapters 设置或旧项目）：调用 generate_outline 生成完整大纲
    
    更新: 2025-11-28 - 支持动态章节模式
    """
    new_count = _increment_node_count(state)
    
    try:
        if not all([state.settings, state.world, state.theme_conflict, state.characters]):
            raise ValueError("前置步骤未完成，无法生成大纲")
        
        settings = state.settings
        
        # 判断使用哪种模式
        # 如果 max_chapters > initial_chapters，说明是动态模式
        use_dynamic_mode = settings.max_chapters > settings.initial_chapters
        
        if use_dynamic_mode:
            # 动态模式：只生成初始章节
            print(f"📖 使用动态章节模式，初始生成 {settings.initial_chapters} 章（最大 {settings.max_chapters} 章）")
            outline = generate_initial_outline(
                world_setting=state.world,
                theme_conflict=state.theme_conflict,
                characters=state.characters,
                initial_chapters=settings.initial_chapters,
                verbose=state.verbose,
                show_prompt=state.show_prompt
            )
        else:
            # 固定模式：生成完整大纲（兼容旧项目）
            print(f"📖 使用固定章节模式，生成 {settings.initial_chapters} 章")
            outline = generate_outline(
                world_setting=state.world,
                theme_conflict=state.theme_conflict,
                characters=state.characters,
                num_chapters=settings.initial_chapters,
                verbose=state.verbose,
                show_prompt=state.show_prompt
            )
            # 固定模式下，大纲视为完整
            outline.is_complete = True
            outline.current_phase = "complete"
        
        # 保存到 JSON
        outline_path = os.path.join(state.project_dir, "outline.json")
        with open(outline_path, 'w', encoding='utf-8') as f:
            json.dump(outline.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {
            "outline": outline,
            "current_step": "outline_creation",
            "completed_steps": state.completed_steps + ["outline_creation"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "outline_creation",
            "failed_steps": state.failed_steps + ["outline_creation"],
            "error_messages": {**state.error_messages, "outline_creation": str(e)},
            "node_execution_count": new_count
        }


def init_chapter_loop_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    初始化章节循环节点

    设置 current_chapter_number 为第一个未完成的章节，支持断点续跑。
    如果所有章节都已完成，则设置为最后一章+1（将触发结束条件）。

    更新: 2025-11-27 - 修改为找到第一个未完成的章节，而不是总是从第1章开始
    更新: 2025-11-28 - 修复 completed_steps 重复添加问题（动态扩展时会多次调用此节点）
    更新: 2025-11-30 - 添加 node_execution_count 更新
    """
    new_count = _increment_node_count(state)
    
    try:
        if not state.chapters_plan:
            raise ValueError("chapters_plan 为空，无法初始化章节循环")

        # 获取所有计划中的章节编号（按顺序）
        planned_chapters = sorted(state.chapters_plan.keys())

        # 找到第一个未完成的章节
        # 章节已完成的标准：存在于 state.chapters 中且有实际内容
        first_incomplete_chapter = None
        completed_count = 0

        for chapter_num in planned_chapters:
            if chapter_num in state.chapters:
                chapter = state.chapters[chapter_num]
                # 检查章节是否有实际内容
                if chapter.scenes and len(chapter.scenes) > 0:
                    completed_count += 1
                    continue
            # 找到第一个未完成的章节
            first_incomplete_chapter = chapter_num
            break

        # 避免 completed_steps 重复添加（动态扩展时会多次调用此节点）
        step_name = "init_chapter_loop"
        if step_name in state.completed_steps:
            new_completed_steps = state.completed_steps  # 不重复添加
        else:
            new_completed_steps = state.completed_steps + [step_name]

        if first_incomplete_chapter is not None:
            # 有未完成的章节，从该章节开始
            if completed_count > 0:
                print(f"🔄 检测到已完成 {completed_count} 章，从第 {first_incomplete_chapter} 章继续")
            else:
                print(f"🔄 初始化章节循环，从第 {first_incomplete_chapter} 章开始")

            return {
                "current_chapter_number": first_incomplete_chapter,
                "current_step": "init_chapter_loop",
                "completed_steps": new_completed_steps,
                "node_execution_count": new_count
            }
        else:
            # 所有章节都已完成
            last_chapter = max(planned_chapters)
            print(f"✅ 所有 {len(planned_chapters)} 章都已完成，无需生成")

            # 设置为最后一章，让后续的条件边能正确处理
            return {
                "current_chapter_number": last_chapter,
                "current_step": "init_chapter_loop",
                "completed_steps": new_completed_steps,
                "node_execution_count": new_count
            }

    except Exception as e:
        return {
            "current_step": "init_chapter_loop",
            "failed_steps": state.failed_steps + ["init_chapter_loop"],
            "error_messages": {**state.error_messages, "init_chapter_loop": str(e)},
            "node_execution_count": new_count
        }


def next_chapter_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    递增章节编号节点
    
    将 current_chapter_number 增加 1，准备处理下一章
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.current_chapter_number is None:
            raise ValueError("current_chapter_number 未设置")
        
        next_chapter_number = state.current_chapter_number + 1
        
        print(f"➡️  准备处理第 {next_chapter_number} 章")
        
        return {
            "current_chapter_number": next_chapter_number,
            "current_step": "next_chapter",
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "next_chapter",
            "failed_steps": state.failed_steps + ["next_chapter"],
            "error_messages": {**state.error_messages, "next_chapter": str(e)},
            "node_execution_count": new_count
        }


def chapter_planning_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    章节计划生成节点
    
    为 outline 中的所有章节生成详细计划
    注：这是批量生成节点，处理所有章节
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.outline is None:
            raise ValueError("outline 未生成，无法创建章节计划")
        
        chapters_plan = {}
        
        for chapter_summary in state.outline.chapters:
            chapter_number = chapter_summary.chapter_number
            
            # 检查是否已存在计划（避免重复生成）
            chapters_dir = os.path.join(state.project_dir, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)
            plan_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}_plan.json")
            
            if os.path.exists(plan_path):
                # 加载已有计划
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    chapters_plan[chapter_number] = ChapterPlan(**plan_data)
            else:
                # 生成新计划
                plan = generate_chapter_plan(
                    chapter_summary=chapter_summary,
                    world_setting=state.world,
                    characters=state.characters,
                    chapter_memory="",
                    chapter_dependencies="",
                    verbose=state.verbose,
                    show_prompt=state.show_prompt
                )
                
                # 保存计划
                with open(plan_path, 'w', encoding='utf-8') as f:
                    json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)
                
                chapters_plan[chapter_number] = plan
        
        return {
            "chapters_plan": chapters_plan,
            "current_step": "chapter_planning",
            "completed_steps": state.completed_steps + ["chapter_planning"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "chapter_planning",
            "failed_steps": state.failed_steps + ["chapter_planning"],
            "error_messages": {**state.error_messages, "chapter_planning": str(e)},
            "node_execution_count": new_count
        }


def _get_mem0_manager(project_dir: str, project_name: str):
    """
    获取 Mem0Manager 实例

    由于 LangGraph 状态无法序列化 Mem0Manager，需要在节点中动态创建

    Args:
        project_dir: 项目目录
        project_name: 项目名称

    Returns:
        Mem0Manager 实例，如果初始化失败则返回 None
    """
    try:
        from novelgen.config import ProjectConfig
        from novelgen.runtime.mem0_manager import Mem0Manager, Mem0InitializationError

        config = ProjectConfig(project_dir=project_dir)
        if config.mem0_config and config.mem0_config.enabled:
            return Mem0Manager(
                config=config.mem0_config,
                project_id=project_name,
                embedding_config=config.embedding_config
            )
    except Exception as e:
        print(f"⚠️ Mem0Manager 初始化失败: {e}")
    return None


def _initialize_character_states_to_mem0(mem0_manager, characters: CharactersConfig):
    """
    初始化角色状态到 Mem0

    为主角、反派和配角创建初始状态记录

    Args:
        mem0_manager: Mem0Manager 实例
        characters: 角色配置
    """
    if mem0_manager is None:
        return

    print(f"💾 正在为角色初始化 Mem0 Agent Memory...")
    try:
        character_count = 0
        
        # 主角
        mem0_manager.add_entity_state(
            entity_id=characters.protagonist.name,
            entity_type="character",
            state_description=f"角色初始状态：{characters.protagonist.personality}。背景：{characters.protagonist.background}",
            chapter_index=0,
            story_timeline="故事开始",
        )
        character_count += 1
        
        # 反派
        if characters.antagonist:
            mem0_manager.add_entity_state(
                entity_id=characters.antagonist.name,
                entity_type="character",
                state_description=f"角色初始状态：{characters.antagonist.personality}。背景：{characters.antagonist.background}",
                chapter_index=0,
                story_timeline="故事开始",
            )
            character_count += 1
        
        # 配角
        for character in characters.supporting_characters:
            mem0_manager.add_entity_state(
                entity_id=character.name,
                entity_type="character",
                state_description=f"角色初始状态：{character.personality}。背景：{character.background}",
                chapter_index=0,
                story_timeline="故事开始",
            )
            character_count += 1
        
        print(f"✅ 已为 {character_count} 个角色初始化 Mem0 记忆")
    except Exception as e:
        print(f"⚠️ Mem0 角色初始化失败: {e}")


def _retrieve_scene_memory_context(
    mem0_manager,
    scene_plan,
    chapter_number: int,
    project_name: str
) -> Optional[SceneMemoryContext]:
    """
    从 Mem0 检索场景记忆上下文

    Args:
        mem0_manager: Mem0Manager 实例
        scene_plan: 场景计划
        chapter_number: 章节编号
        project_name: 项目名称

    Returns:
        SceneMemoryContext 对象，如果检索失败则返回 None
    """
    if mem0_manager is None:
        return None

    try:
        # 从 Mem0 检索角色状态
        entity_states = []
        if scene_plan.characters:
            entity_states = mem0_manager.get_entity_states_for_characters(
                character_names=scene_plan.characters,
                chapter_index=chapter_number,
                scene_index=scene_plan.scene_number
            )
            if entity_states:
                print(f"    ✅ 已从 Mem0 检索到 {len(entity_states)} 个角色状态")

        # 从 Mem0 检索相关场景内容
        relevant_memories = []
        try:
            # 使用场景目的作为查询
            relevant_memories = mem0_manager.search_scene_content(
                query=scene_plan.purpose,
                chapter_index=None,  # 搜索所有章节
                limit=5
            )
            if relevant_memories:
                print(f"    ✅ 已从 Mem0 检索到 {len(relevant_memories)} 个相关记忆")
        except Exception as search_exc:
            print(f"    ⚠️ Mem0 场景内容搜索失败: {search_exc}")

        # 构建场景记忆上下文
        return SceneMemoryContext(
            project_id=project_name,
            chapter_index=chapter_number,
            scene_index=scene_plan.scene_number,
            entity_states=entity_states,
            relevant_memories=relevant_memories,
            timeline_context=None,
            retrieval_timestamp=datetime.now()
        )
    except Exception as exc:
        print(f"    ⚠️ 场景记忆上下文生成失败: {exc}")
        return None


def _save_scene_to_mem0(mem0_manager, content: str, chapter_number: int, scene_number: int):
    """
    保存场景内容到 Mem0

    Args:
        mem0_manager: Mem0Manager 实例
        content: 场景文本内容
        chapter_number: 章节编号
        scene_number: 场景编号
    """
    if mem0_manager is None:
        return

    try:
        chunks = mem0_manager.add_scene_content(
            content=content,
            chapter_index=chapter_number,
            scene_index=scene_number,
            content_type="scene"
        )
        if chunks:
            print(f"    💾 已将场景{scene_number}内容保存到 Mem0（{len(chunks)}个块）")
    except Exception as e:
        print(f"    ⚠️ 保存场景内容到 Mem0 失败: {e}")


def _generate_and_save_chapter_memory(
    state: NovelGenerationState,
    chapter: GeneratedChapter,
    chapter_number: int,
    mem0_manager
) -> Optional[ChapterMemoryEntry]:
    """
    生成章节记忆条目并保存到文件和 Mem0

    Args:
        state: 当前工作流状态
        chapter: 已生成的章节
        chapter_number: 章节编号
        mem0_manager: Mem0Manager 实例

    Returns:
        ChapterMemoryEntry 对象，如果生成失败则返回 None
    """
    print(f"🧠 正在为第{chapter_number}章生成记忆条目...")
    
    try:
        # 获取章节摘要（从大纲中）
        outline_summary = None
        if state.outline:
            for ch in state.outline.chapters:
                if ch.chapter_number == chapter_number:
                    outline_summary = ch
                    break
        
        # 生成场景摘要
        scene_summaries_text = summarize_scenes(chapter.scenes, verbose=state.verbose, show_prompt=state.show_prompt)
        scene_summaries = scene_summaries_text.split("\n") if scene_summaries_text else []
        
        # 聚合摘要
        aggregated_summary = f"第{chapter_number}章「{chapter.chapter_title}」共{len(chapter.scenes)}个场景，{chapter.total_words}字"
        
        # 调用 LLM 生成章节记忆条目
        memory_entry = generate_chapter_memory_entry(
            chapter=chapter,
            outline_summary=outline_summary,
            scene_summaries=scene_summaries,
            aggregated_summary=aggregated_summary,
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )
        
        # 保存到 chapter_memory.json
        _append_chapter_memory_entry(state.project_dir, memory_entry)
        print(f"✅ 第{chapter_number}章记忆条目已保存")
        
        # 更新角色状态到 Mem0（传递故事时间线）
        if mem0_manager and memory_entry.character_states:
            _update_character_states_to_mem0(
                mem0_manager, 
                memory_entry.character_states, 
                chapter_number,
                story_timeline=memory_entry.timeline_anchor
            )
        
        return memory_entry
        
    except Exception as exc:
        print(f"⚠️ 章节记忆生成失败：{exc}")
        return None


def _append_chapter_memory_entry(project_dir: str, memory_entry: ChapterMemoryEntry):
    """
    将章节记忆条目追加到 chapter_memory.json
    
    Args:
        project_dir: 项目目录
        memory_entry: 章节记忆条目
    """
    memory_file = os.path.join(project_dir, "chapter_memory.json")
    
    # 读取现有记忆
    existing_memories = []
    if os.path.exists(memory_file):
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                existing_memories = json.load(f)
        except (json.JSONDecodeError, Exception):
            existing_memories = []
    
    # 追加新记忆
    existing_memories.append(memory_entry.model_dump())
    
    # 保存
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(existing_memories, f, ensure_ascii=False, indent=2)


def _update_character_states_to_mem0(
    mem0_manager, 
    character_states: Dict[str, str], 
    chapter_number: int,
    story_timeline: Optional[str] = None
):
    """
    更新角色状态到 Mem0
    
    Args:
        mem0_manager: Mem0Manager 实例
        character_states: 角色状态字典 {角色名: 状态描述}
        chapter_number: 章节编号
        story_timeline: 故事时间线（如 "T+0 天"）
    """
    if not character_states:
        return
    
    print(f"💾 正在更新角色状态到 Mem0...")
    updated_count = 0
    
    for character_name, state_description in character_states.items():
        try:
            mem0_manager.add_entity_state(
                entity_id=character_name,
                entity_type="character",
                state_description=state_description,
                chapter_index=chapter_number,
                story_timeline=story_timeline,
            )
            updated_count += 1
        except Exception as char_exc:
            print(f"⚠️ 更新角色 {character_name} 状态失败: {char_exc}")
    
    print(f"✅ 已更新 {updated_count} 个角色状态到 Mem0")


def chapter_generation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    章节文本生成节点（单章生成模式）

    根据 state.current_chapter_number 生成指定章节的场景文本
    支持从 Mem0 检索记忆上下文以提升生成一致性
    """
    new_count = _increment_node_count(state)
    
    try:
        if not state.chapters_plan:
            raise ValueError("chapters_plan 为空，无法生成章节文本")

        # 确定当前章节编号
        chapter_number = state.current_chapter_number
        if chapter_number is None:
            raise ValueError("current_chapter_number 未设置，无法生成章节")

        # 检查章节计划是否存在
        if chapter_number not in state.chapters_plan:
            raise ValueError(f"章节 {chapter_number} 的计划不存在")

        plan = state.chapters_plan[chapter_number]
        chapters = dict(state.chapters)  # 复制现有章节
        chapter_memories = list(state.chapter_memories)  # 复制现有记忆
        
        # 初始化 Mem0Manager（用于记忆检索和存储）
        mem0_manager = _get_mem0_manager(state.project_dir, state.project_name)

        # 检查是否已存在章节（避免重复生成）
        chapters_dir = os.path.join(state.project_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")

        if os.path.exists(chapter_path) and chapter_number not in chapters:
            # 加载已有章节
            with open(chapter_path, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
                chapters[chapter_number] = GeneratedChapter(**chapter_data)
            print(f"✅ 第 {chapter_number} 章已存在，跳过生成")
        elif chapter_number not in chapters:
            # 生成新章节
            print(f"📝 正在生成第 {chapter_number} 章：{plan.chapter_title}")

            if mem0_manager:
                print(f"    🧠 已初始化 Mem0 记忆检索")
            else:
                print(f"    ⚠️ Mem0 未启用，将不使用记忆上下文")

            generated_scenes = []
            previous_summary = ""

            for scene_plan in plan.scenes:
                print(f"    生成场景 {scene_plan.scene_number}...")

                # 从 Mem0 检索记忆上下文
                scene_memory_context = _retrieve_scene_memory_context(
                    mem0_manager=mem0_manager,
                    scene_plan=scene_plan,
                    chapter_number=chapter_number,
                    project_name=state.project_name
                )

                # 生成场景文本
                scene = generate_scene_text(
                    scene_plan=scene_plan,
                    world_setting=state.world,
                    characters=state.characters,
                    previous_summary=previous_summary,
                    chapter_context="",
                    scene_memory_context=scene_memory_context,
                    verbose=state.verbose,
                    show_prompt=state.show_prompt
                )
                generated_scenes.append(scene)

                # 保存场景内容到 Mem0（供后续场景检索）
                _save_scene_to_mem0(
                    mem0_manager=mem0_manager,
                    content=scene.content,
                    chapter_number=chapter_number,
                    scene_number=scene.scene_number
                )

                # 更新前文摘要（简单版本，使用场景概要）
                if hasattr(scene_plan, 'summary') and scene_plan.summary:
                    previous_summary = scene_plan.summary
                elif hasattr(scene, 'content') and scene.content:
                    # 截取内容前200字作为摘要
                    previous_summary = scene.content[:200] + "..."

            chapter = GeneratedChapter(
                chapter_number=chapter_number,
                chapter_title=plan.chapter_title,
                scenes=generated_scenes,
                total_words=sum(s.word_count for s in generated_scenes)
            )

            # 保存章节
            with open(chapter_path, 'w', encoding='utf-8') as f:
                json.dump(chapter.model_dump(), f, ensure_ascii=False, indent=2)

            chapters[chapter_number] = chapter
            print(f"✅ 第 {chapter_number} 章生成完成，共 {chapter.total_words} 字")
            
            # 生成章节记忆并更新角色状态到 Mem0
            memory_entry = _generate_and_save_chapter_memory(
                state=state,
                chapter=chapter,
                chapter_number=chapter_number,
                mem0_manager=mem0_manager
            )
            
            # 将记忆条目添加到状态（用于后续章节的一致性检测）
            if memory_entry:
                chapter_memories.append(memory_entry)

        return {
            "chapters": chapters,
            "chapter_memories": chapter_memories,
            "current_step": "chapter_generation",
            "completed_steps": state.completed_steps + [f"chapter_generation_{chapter_number}"],
            "node_execution_count": new_count
        }

    except Exception as e:
        return {
            "current_step": "chapter_generation",
            "failed_steps": state.failed_steps + ["chapter_generation"],
            "error_messages": {**state.error_messages, "chapter_generation": str(e)},
            "node_execution_count": new_count
        }


def consistency_check_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    一致性检测节点
    
    对当前章节进行完整上下文一致性检测：
    - 章节计划
    - 世界观设定
    - 角色配置
    - 前文章节记忆
    """
    new_count = _increment_node_count(state)
    chapter_number = state.current_chapter_number
    
    try:
        # 获取当前章节编号
        if chapter_number is None:
            raise ValueError("current_chapter_number 未设置，无法进行一致性检测")
        
        # 检查章节是否已生成
        if chapter_number not in state.chapters:
            raise ValueError(f"章节 {chapter_number} 尚未生成，无法进行一致性检测")
        
        chapter = state.chapters[chapter_number]
        
        # 1. 构建上下文 payload
        print(f"🔍 正在对第 {chapter_number} 章进行一致性检测...")
        context_payload = _build_context_payload(state, chapter_number)
        
        # 2. 收集章节文本
        chapter_text = _collect_chapter_text(chapter)
        
        # 3. 调用一致性检测链
        report = run_consistency_check(
            chapter_number=chapter_number,
            context_payload=context_payload,
            chapter_text=chapter_text,
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )
        
        # 4. 保存报告到状态
        consistency_reports = dict(state.consistency_reports)
        consistency_reports[chapter_number] = report
        
        # 5. 保存报告到文件
        reports_file = os.path.join(state.project_dir, "consistency_reports.json")
        all_reports = []
        if os.path.exists(reports_file):
            try:
                with open(reports_file, 'r', encoding='utf-8') as f:
                    all_reports = json.load(f)
            except json.JSONDecodeError:
                all_reports = []
        
        all_reports.append(report.model_dump())
        with open(reports_file, 'w', encoding='utf-8') as f:
            json.dump(all_reports, f, ensure_ascii=False, indent=2)
        
        # 6. 输出检测结果
        issue_count = len(report.issues)
        if issue_count == 0:
            print(f"✅ 第 {chapter_number} 章一致性检测通过，未发现问题")
        else:
            severity_summary = {}
            for issue in report.issues:
                severity = issue.severity
                severity_summary[severity] = severity_summary.get(severity, 0) + 1
            
            severity_info = ", ".join([f"{k}({v})" for k, v in severity_summary.items()])
            print(f"⚠️  第 {chapter_number} 章发现 {issue_count} 个问题: {severity_info}")
        
        return {
            "consistency_reports": consistency_reports,
            "current_step": "consistency_check",
            "completed_steps": state.completed_steps + [f"consistency_check_{chapter_number}"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "consistency_check",
            "failed_steps": state.failed_steps + [f"consistency_check_{chapter_number}"],
            "error_messages": {**state.error_messages, f"consistency_check_{chapter_number}": str(e)},
            "node_execution_count": new_count
        }


def chapter_revision_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    章节修订节点
    
    根据一致性检测结果自动修订章节
    """
    new_count = _increment_node_count(state)
    chapter_number = state.current_chapter_number
    
    try:
        # 获取当前章节编号
        if chapter_number is None:
            raise ValueError("current_chapter_number 未设置，无法进行修订")
        
        # 检查是否有一致性报告
        if chapter_number not in state.consistency_reports:
            raise ValueError(f"章节 {chapter_number} 没有一致性报告，无法进行修订")
        
        report = state.consistency_reports[chapter_number]
        
        # 检查是否有问题需要修订
        if not report.issues:
            print(f"✅ 第 {chapter_number} 章无需修订")
            return {
                "current_step": "chapter_revision",
                "completed_steps": state.completed_steps + [f"chapter_revision_{chapter_number}_skipped"],
                "node_execution_count": new_count
            }
        
        # 构建修订说明
        print(f"🔧 正在修订第 {chapter_number} 章...")
        revision_notes_parts = [f"发现 {len(report.issues)} 个问题需要修订：\n"]
        
        for i, issue in enumerate(report.issues, 1):
            revision_notes_parts.append(
                f"{i}. [{issue.severity}] {issue.issue_type}: {issue.description}"
            )
            if issue.fix_instructions:
                revision_notes_parts.append(f"   修复建议：{issue.fix_instructions}")
            revision_notes_parts.append("")
        
        revision_notes = "\n".join(revision_notes_parts)
        
        # 获取原始章节
        original_chapter = state.chapters[chapter_number]
        
        # 调用修订链
        revised_chapter = revise_chapter(
            original_chapter=original_chapter,
            revision_notes=revision_notes,
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )
        
        # 更新章节
        chapters = dict(state.chapters)
        chapters[chapter_number] = revised_chapter
        
        # 保存修订后的章节
        chapters_dir = os.path.join(state.project_dir, "chapters")
        chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")
        with open(chapter_path, 'w', encoding='utf-8') as f:
            json.dump(revised_chapter.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 第 {chapter_number} 章修订完成")
        
        return {
            "chapters": chapters,
            "current_step": "chapter_revision",
            "completed_steps": state.completed_steps + [f"chapter_revision_{chapter_number}"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        print(f"❌ 修订失败：{str(e)}")
        return {
            "current_step": "chapter_revision",
            "failed_steps": state.failed_steps + [f"chapter_revision_{chapter_number}"],
            "error_messages": {**state.error_messages, f"chapter_revision_{chapter_number}": str(e)},
            "node_execution_count": new_count
        }


# ============================================================================
# 动态章节扩展节点
# ============================================================================

def evaluate_story_progress_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    剧情进度评估节点
    
    评估当前剧情进度，决定是继续发展、开始收尾还是强制结束。
    
    触发条件：当前章节 >= 已规划章节数 且 outline.is_complete = False
    
    重要：代码级强制保障评估规则：
    - 当前章节 >= max_chapters 时，强制返回 force_end（不调用 LLM）
    - 当前章节 >= max_chapters * 0.8 时，LLM 返回 continue 会被覆盖为 wrap_up
    
    开发者: jamesenh, 开发时间: 2025-11-28
    更新: 2025-11-28 - 添加代码级强制保障，防止 LLM 不遵守评估规则
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.outline is None or state.theme_conflict is None or state.settings is None:
            raise ValueError("outline, theme_conflict 或 settings 未加载")
        
        # 使用已完成的章节数（更准确）
        current_chapter = len(state.chapters)
        max_chapters = state.settings.max_chapters
        remaining_chapters = max_chapters - current_chapter
        
        print(f"📊 评估剧情进度：当前第 {current_chapter} 章，最大 {max_chapters} 章，剩余 {remaining_chapters} 章")
        
        # ===== 代码级强制保障 =====
        # 规则1: 当前章节 >= max_chapters 时，强制 force_end（不调用 LLM）
        if current_chapter >= max_chapters:
            print(f"🛑 已达到最大章节数限制，强制结束")
            evaluation = StoryProgressEvaluation(
                evaluation_result="force_end",
                current_chapter=current_chapter,
                remaining_chapters=0,
                main_conflict_progress=1.0,  # 假设已完成
                unresolved_threads=[],
                character_arc_status={},
                recommendation=f"已达到最大章节数 {max_chapters}，必须立即结束故事。"
            )
        else:
            # 调用 LLM 评估
            evaluation = evaluate_story_progress(
                current_chapter=current_chapter,
                max_chapters=max_chapters,
                theme_conflict=state.theme_conflict,
                outline=state.outline,
                chapter_memories=state.chapter_memories,
                verbose=state.verbose,
                show_prompt=state.show_prompt
            )
            
            # 规则2: 剩余章节 <= 20% 时，如果 LLM 返回 continue，强制覆盖为 wrap_up
            threshold = max_chapters * 0.2
            if remaining_chapters <= threshold and evaluation.evaluation_result == "continue":
                print(f"⚠️ 剩余章节({remaining_chapters})不足20%，将 continue 覆盖为 wrap_up")
                evaluation.evaluation_result = "wrap_up"
                evaluation.recommendation = f"[系统覆盖] 剩余章节不足，原建议继续发展，现强制开始收尾。原因：{evaluation.recommendation}"
        
        # 输出评估结果
        result_emoji = {
            "continue": "🔄",
            "wrap_up": "🎬",
            "force_end": "🛑"
        }
        emoji = result_emoji.get(evaluation.evaluation_result, "❓")
        print(f"{emoji} 评估结果：{evaluation.evaluation_result}")
        print(f"   主线进度：{evaluation.main_conflict_progress:.0%}")
        print(f"   剩余章节：{evaluation.remaining_chapters}")
        print(f"   建议：{evaluation.recommendation[:100]}...")
        
        return {
            "story_progress_evaluation": evaluation,
            "current_step": "evaluate_story_progress",
            "completed_steps": state.completed_steps + ["evaluate_story_progress"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "evaluate_story_progress",
            "failed_steps": state.failed_steps + ["evaluate_story_progress"],
            "error_messages": {**state.error_messages, "evaluate_story_progress": str(e)},
            "node_execution_count": new_count
        }


def extend_outline_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    大纲扩展节点
    
    根据剧情进度评估结果，生成后续章节的大纲。
    
    重要：包含无限循环检测，如果扩展后没有新章节，强制标记大纲为完成。
    
    开发者: jamesenh, 开发时间: 2025-11-28
    更新: 2025-11-28 - 添加无限循环检测，修复剩余章节数计算
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.outline is None or state.story_progress_evaluation is None or state.settings is None:
            raise ValueError("outline, story_progress_evaluation 或 settings 未加载")
        
        evaluation = state.story_progress_evaluation
        # 修复问题4：统一使用 len(state.chapters) 计算剩余章节数
        completed_chapters = len(state.chapters)
        remaining_chapters = state.settings.max_chapters - completed_chapters
        
        mode_desc = {
            "continue": "继续发展",
            "wrap_up": "开始收尾",
            "force_end": "强制结束"
        }
        print(f"📝 扩展大纲（{mode_desc.get(evaluation.evaluation_result, '未知')}模式）...")
        print(f"   已完成 {completed_chapters} 章，剩余可用 {remaining_chapters} 章")
        
        # 调用大纲扩展链
        extended_outline = extend_outline(
            existing_outline=state.outline,
            evaluation=evaluation,
            chapter_memories=state.chapter_memories,
            remaining_chapters=remaining_chapters,
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )
        
        # 计算新增章节数
        old_count = len(state.outline.chapters)
        new_chapter_count = len(extended_outline.chapters)
        added_count = new_chapter_count - old_count
        
        # ===== 无限循环检测 =====
        # 如果扩展后没有新增章节，强制标记大纲为完成，防止无限循环
        if added_count <= 0:
            print(f"⚠️ 大纲扩展未生成新章节（新增 {added_count} 章），强制标记为完成")
            extended_outline.is_complete = True
            extended_outline.current_phase = "resolution"
        
        print(f"✅ 大纲扩展完成：新增 {added_count} 章（共 {new_chapter_count} 章）")
        if extended_outline.is_complete:
            print(f"   📕 大纲已完整（包含结局）")
        
        # 保存更新后的大纲
        outline_path = os.path.join(state.project_dir, "outline.json")
        with open(outline_path, 'w', encoding='utf-8') as f:
            json.dump(extended_outline.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {
            "outline": extended_outline,
            "story_progress_evaluation": None,  # 清除评估结果，等待下次评估
            "current_step": "extend_outline",
            "completed_steps": state.completed_steps + ["extend_outline"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "extend_outline",
            "failed_steps": state.failed_steps + ["extend_outline"],
            "error_messages": {**state.error_messages, "extend_outline": str(e)},
            "node_execution_count": new_count
        }


def plan_new_chapters_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    新章节计划生成节点
    
    为大纲中新增的章节生成详细计划。
    只处理尚未有计划的章节。
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    new_count = _increment_node_count(state)
    
    try:
        if state.outline is None:
            raise ValueError("outline 未加载")
        
        chapters_plan = dict(state.chapters_plan)  # 复制现有计划
        chapters_dir = os.path.join(state.project_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        
        new_plans_count = 0
        
        for chapter_summary in state.outline.chapters:
            chapter_number = chapter_summary.chapter_number
            
            # 跳过已有计划的章节
            if chapter_number in chapters_plan:
                continue
            
            plan_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}_plan.json")
            
            if os.path.exists(plan_path):
                # 加载已有计划文件
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    chapters_plan[chapter_number] = ChapterPlan(**plan_data)
            else:
                # 生成新计划
                print(f"   📋 生成第 {chapter_number} 章计划...")
                plan = generate_chapter_plan(
                    chapter_summary=chapter_summary,
                    world_setting=state.world,
                    characters=state.characters,
                    chapter_memory="",
                    chapter_dependencies="",
                    verbose=state.verbose,
                    show_prompt=state.show_prompt
                )
                
                # 保存计划
                with open(plan_path, 'w', encoding='utf-8') as f:
                    json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)
                
                chapters_plan[chapter_number] = plan
                new_plans_count += 1
        
        if new_plans_count > 0:
            print(f"✅ 新增 {new_plans_count} 个章节计划")
        
        return {
            "chapters_plan": chapters_plan,
            "current_step": "plan_new_chapters",
            "completed_steps": state.completed_steps + ["plan_new_chapters"],
            "node_execution_count": new_count
        }
    
    except Exception as e:
        return {
            "current_step": "plan_new_chapters",
            "failed_steps": state.failed_steps + ["plan_new_chapters"],
            "error_messages": {**state.error_messages, "plan_new_chapters": str(e)},
            "node_execution_count": new_count
        }


# ============================================================================
# 场景生成子图节点
# ============================================================================

def init_scene_loop_node(state: SceneGenerationState) -> Dict[str, Any]:
    """
    初始化场景循环节点
    
    设置场景循环的初始状态，根据已存在的场景文件设置起始位置。
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    print(f"📝 开始生成第 {state.chapter_number} 章的场景...")
    print(f"   总场景数: {state.total_scenes}, 已完成: {len(state.generated_scenes)}")
    
    # 设置当前场景编号为已完成数量+1
    current_scene_number = len(state.generated_scenes) + 1
    
    return {
        "current_scene_number": current_scene_number
    }


def should_generate_scene(state: SceneGenerationState) -> str:
    """
    条件函数：判断当前场景是否需要生成
    
    返回:
        "skip" - 场景已存在，跳过
        "execute" - 需要生成场景
    """
    scene_num = state.current_scene_number
    
    # 检查是否超出总场景数
    if scene_num > state.total_scenes:
        return "skip"
    
    # 检查场景是否已完成
    if scene_num in state.scene_status and state.scene_status[scene_num] == "completed":
        print(f"  ⏭️ 场景 {scene_num} 已存在，跳过")
        return "skip"
    
    return "execute"


def retrieve_scene_memory_node(state: SceneGenerationState) -> Dict[str, Any]:
    """
    从 Mem0 检索场景记忆上下文
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    scene_num = state.current_scene_number
    
    # 获取场景计划
    if state.chapter_plan is None or scene_num > len(state.chapter_plan.scenes):
        return {"scene_memory_context": None}
    
    scene_plan = state.chapter_plan.scenes[scene_num - 1]  # 索引从0开始
    
    # 获取 Mem0Manager
    mem0_manager = _get_mem0_manager(state.project_dir, state.project_name)
    
    # 检索记忆上下文
    scene_memory_context = _retrieve_scene_memory_context(
        mem0_manager=mem0_manager,
        scene_plan=scene_plan,
        chapter_number=state.chapter_number,
        project_name=state.project_name
    )
    
    return {"scene_memory_context": scene_memory_context}


def generate_scene_node(state: SceneGenerationState) -> Dict[str, Any]:
    """
    生成单个场景文本
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    scene_num = state.current_scene_number
    
    # 获取场景计划
    if state.chapter_plan is None or scene_num > len(state.chapter_plan.scenes):
        raise ValueError(f"场景 {scene_num} 的计划不存在")
    
    scene_plan = state.chapter_plan.scenes[scene_num - 1]
    
    print(f"  ✍️ 生成场景 {scene_num}...")
    
    # 调用场景生成链
    scene = generate_scene_text(
        scene_plan=scene_plan,
        world_setting=state.world,
        characters=state.characters,
        previous_summary=state.previous_summary,
        chapter_context="",
        scene_memory_context=state.scene_memory_context,
        verbose=state.verbose,
        show_prompt=state.show_prompt
    )
    
    # 更新 previous_summary 用于下一场景
    new_summary = scene.content[:200] + "..." if len(scene.content) > 200 else scene.content
    
    # 将新场景添加到列表
    new_scenes = list(state.generated_scenes) + [scene]
    
    return {
        "generated_scenes": new_scenes,
        "previous_summary": new_summary
    }


def save_scene_node(state: SceneGenerationState) -> Dict[str, Any]:
    """
    保存场景到文件和 Mem0
    
    每个场景完成后立即持久化，支持断点续跑。
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    if not state.generated_scenes:
        return {}
    
    scene = state.generated_scenes[-1]
    chapters_dir = os.path.join(state.project_dir, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)
    
    # 1. 保存场景 JSON 文件
    scene_file = os.path.join(
        chapters_dir,
        f"scene_{state.chapter_number:03d}_{scene.scene_number:03d}.json"
    )
    with open(scene_file, 'w', encoding='utf-8') as f:
        json.dump(scene.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"  💾 场景 {scene.scene_number} 已保存: {scene_file}")
    
    # 2. 保存到 Mem0
    mem0_manager = _get_mem0_manager(state.project_dir, state.project_name)
    _save_scene_to_mem0(
        mem0_manager=mem0_manager,
        content=scene.content,
        chapter_number=state.chapter_number,
        scene_number=scene.scene_number
    )
    
    # 3. 更新场景状态
    scene_status = dict(state.scene_status)
    scene_status[scene.scene_number] = "completed"
    
    return {"scene_status": scene_status}


def next_scene_node(state: SceneGenerationState) -> Dict[str, Any]:
    """
    递增场景编号
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    return {
        "current_scene_number": state.current_scene_number + 1
    }


def has_more_scenes(state: SceneGenerationState) -> str:
    """
    条件函数：判断是否还有更多场景需要生成
    
    返回:
        "continue" - 还有场景需要生成
        "end" - 所有场景已完成
    """
    if state.current_scene_number <= state.total_scenes:
        return "continue"
    return "end"


def skip_scene_node(state: SceneGenerationState) -> Dict[str, Any]:
    """
    跳过场景的空操作节点
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    return {}


def scene_generation_wrapper_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    场景生成包装节点
    
    职责：
    1. 从父图状态提取子图输入
    2. 检查已存在的场景文件（断点续跑）
    3. 调用子图（或直接处理如果子图不可用）
    4. 将子图结果合并回父图状态
    
    注意：由于子图需要在 workflow.py 中定义，这里暂时使用内联逻辑，
    后续可以改为调用子图。
    
    开发者: jamesenh, 开发时间: 2025-11-28
    更新: 2025-11-30 - 添加 node_execution_count 更新
    """
    new_count = _increment_node_count(state)
    
    try:
        if not state.chapters_plan:
            raise ValueError("chapters_plan 为空，无法生成章节文本")

        chapter_number = state.current_chapter_number
        if chapter_number is None:
            raise ValueError("current_chapter_number 未设置，无法生成章节")

        if chapter_number not in state.chapters_plan:
            raise ValueError(f"章节 {chapter_number} 的计划不存在")

        plan = state.chapters_plan[chapter_number]
        chapters_dir = os.path.join(state.project_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")

        # 检查是否已存在完整章节
        if os.path.exists(chapter_path) and chapter_number not in state.chapters:
            with open(chapter_path, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
                chapter = GeneratedChapter(**chapter_data)
            print(f"✅ 第 {chapter_number} 章已存在，跳过生成")
            
            chapters = dict(state.chapters)
            chapters[chapter_number] = chapter
            return {
                "chapters": chapters,
                "current_step": "chapter_generation",
                "completed_steps": state.completed_steps + [f"chapter_generation_{chapter_number}"],
                "node_execution_count": new_count
            }

        # 初始化 Mem0Manager
        mem0_manager = _get_mem0_manager(state.project_dir, state.project_name)
        if mem0_manager:
            print(f"    🧠 已初始化 Mem0 记忆检索")

        # 构建子图输入状态
        subgraph_state = SceneGenerationState(
            chapter_number=chapter_number,
            chapter_plan=plan,
            total_scenes=len(plan.scenes),
            world=state.world,
            characters=state.characters,
            project_dir=state.project_dir,
            project_name=state.project_name,
            verbose=state.verbose,
            show_prompt=state.show_prompt
        )

        # 检查已存在的场景文件（断点续跑支持）
        for scene_plan in plan.scenes:
            scene_file = os.path.join(
                chapters_dir,
                f"scene_{chapter_number:03d}_{scene_plan.scene_number:03d}.json"
            )
            if os.path.exists(scene_file):
                with open(scene_file, 'r', encoding='utf-8') as f:
                    scene = GeneratedScene(**json.load(f))
                subgraph_state.generated_scenes.append(scene)
                subgraph_state.scene_status[scene_plan.scene_number] = "completed"
                print(f"  ⏭️ 场景 {scene_plan.scene_number} 已存在，跳过")

        # 设置起始场景编号
        subgraph_state.current_scene_number = len(subgraph_state.generated_scenes) + 1

        print(f"📝 正在生成第 {chapter_number} 章：{plan.chapter_title}")
        print(f"   总场景数: {subgraph_state.total_scenes}, 已完成: {len(subgraph_state.generated_scenes)}")

        # 尝试调用子图，如果不可用则使用内联逻辑
        try:
            from novelgen.runtime.workflow import scene_generation_subgraph
            if scene_generation_subgraph is not None:
                # 使用子图处理
                result = scene_generation_subgraph.invoke(subgraph_state.model_dump())
                raw_scenes = result.get("generated_scenes", [])
                
                # 安全地转换场景数据（处理对象和字典两种情况）
                generated_scenes = []
                for s in raw_scenes:
                    if isinstance(s, GeneratedScene):
                        generated_scenes.append(s)
                    elif isinstance(s, dict):
                        generated_scenes.append(GeneratedScene(**s))
                    elif hasattr(s, 'model_dump'):
                        # Pydantic 对象但类型不匹配，尝试转换
                        generated_scenes.append(GeneratedScene(**s.model_dump()))
                    else:
                        print(f"  ⚠️ 未知场景类型: {type(s)}, 跳过")
            else:
                raise ImportError("scene_generation_subgraph 未定义")
        except (ImportError, AttributeError) as e:
            # 子图不可用，使用内联逻辑
            print(f"  ℹ️ 使用内联逻辑生成场景 (原因: {e})")
            generated_scenes = list(subgraph_state.generated_scenes)
            previous_summary = subgraph_state.previous_summary
            
            # 导入停止信号检查函数
            from novelgen.runtime.mem0_manager import is_shutdown_requested
            
            for i in range(subgraph_state.current_scene_number, subgraph_state.total_scenes + 1):
                # 检查是否收到停止信号
                if is_shutdown_requested():
                    print(f"  ⏹️ 收到停止信号，停止场景生成（已完成 {len(generated_scenes)} 个场景）")
                    break
                
                scene_plan = plan.scenes[i - 1]
                
                # 检索记忆上下文
                scene_memory_context = _retrieve_scene_memory_context(
                    mem0_manager=mem0_manager,
                    scene_plan=scene_plan,
                    chapter_number=chapter_number,
                    project_name=state.project_name
                )
                
                print(f"  ✍️ 生成场景 {i}...")
                
                # 生成场景
                scene = generate_scene_text(
                    scene_plan=scene_plan,
                    world_setting=state.world,
                    characters=state.characters,
                    previous_summary=previous_summary,
                    chapter_context="",
                    scene_memory_context=scene_memory_context,
                    verbose=state.verbose,
                    show_prompt=state.show_prompt
                )
                
                # 立即保存场景到文件
                scene_file = os.path.join(
                    chapters_dir,
                    f"scene_{chapter_number:03d}_{scene.scene_number:03d}.json"
                )
                with open(scene_file, 'w', encoding='utf-8') as f:
                    json.dump(scene.model_dump(), f, ensure_ascii=False, indent=2)
                print(f"  💾 场景 {scene.scene_number} 已保存: {scene_file}")
                
                # 保存到 Mem0
                _save_scene_to_mem0(
                    mem0_manager=mem0_manager,
                    content=scene.content,
                    chapter_number=chapter_number,
                    scene_number=scene.scene_number
                )
                
                generated_scenes.append(scene)
                previous_summary = scene.content[:200] + "..." if len(scene.content) > 200 else scene.content

        # 如果 generated_scenes 为空但场景文件存在，从文件重新加载（回退机制）
        if not generated_scenes:
            print(f"  ⚠️ 场景列表为空，尝试从文件重新加载...")
            for scene_plan in plan.scenes:
                scene_file = os.path.join(
                    chapters_dir,
                    f"scene_{chapter_number:03d}_{scene_plan.scene_number:03d}.json"
                )
                if os.path.exists(scene_file):
                    with open(scene_file, 'r', encoding='utf-8') as f:
                        scene = GeneratedScene(**json.load(f))
                    generated_scenes.append(scene)
            if generated_scenes:
                print(f"  ✅ 从文件加载了 {len(generated_scenes)} 个场景")
            else:
                print(f"  ❌ 未找到任何场景文件")

        # 合并场景为章节
        chapter = GeneratedChapter(
            chapter_number=chapter_number,
            chapter_title=plan.chapter_title,
            scenes=generated_scenes,
            total_words=sum(s.word_count for s in generated_scenes)
        )

        # 保存完整章节文件
        with open(chapter_path, 'w', encoding='utf-8') as f:
            json.dump(chapter.model_dump(), f, ensure_ascii=False, indent=2)
        print(f"  💾 章节文件已保存: {chapter_path}")

        # 清理单独的场景文件（可选，保留以便调试）
        # for scene in generated_scenes:
        #     scene_file = os.path.join(chapters_dir, f"scene_{chapter_number:03d}_{scene.scene_number:03d}.json")
        #     if os.path.exists(scene_file):
        #         os.remove(scene_file)

        chapters = dict(state.chapters)
        chapters[chapter_number] = chapter
        chapter_memories = list(state.chapter_memories)

        print(f"✅ 第 {chapter_number} 章生成完成，共 {chapter.total_words} 字")

        # 生成章节记忆并更新角色状态到 Mem0
        memory_entry = _generate_and_save_chapter_memory(
            state=state,
            chapter=chapter,
            chapter_number=chapter_number,
            mem0_manager=mem0_manager
        )

        if memory_entry:
            chapter_memories.append(memory_entry)

        return {
            "chapters": chapters,
            "chapter_memories": chapter_memories,
            "current_step": "chapter_generation",
            "completed_steps": state.completed_steps + [f"chapter_generation_{chapter_number}"],
            "node_execution_count": new_count
        }

    except Exception as e:
        return {
            "current_step": "chapter_generation",
            "failed_steps": state.failed_steps + ["chapter_generation"],
            "error_messages": {**state.error_messages, "chapter_generation": str(e)},
            "node_execution_count": new_count
        }


# ============================================================================
# 辅助函数
# ============================================================================

def _build_context_payload(state: NovelGenerationState, chapter_number: int) -> str:
    """
    构建一致性检测上下文
    
    包含：章节计划、世界观、角色配置、前文记忆
    参考 orchestrator._build_consistency_context
    """
    # 获取章节摘要（从大纲中）
    chapter_summary = None
    if state.outline:
        for ch in state.outline.chapters:
            if ch.chapter_number == chapter_number:
                chapter_summary = ch
                break
    
    # 获取最近N章的记忆（取前面的章节）
    recent_memories = []
    for memory in state.chapter_memories:
        if memory.chapter_number < chapter_number:
            recent_memories.append(memory.model_dump())
    
    # 构建 payload
    payload = {
        "chapter_plan": state.chapters_plan[chapter_number].model_dump() if chapter_number in state.chapters_plan else {},
        "outline_summary": chapter_summary.model_dump() if chapter_summary else {},
        "world_setting": state.world.model_dump() if state.world else {},
        "characters": state.characters.model_dump() if state.characters else {},
        "recent_memory": recent_memories[-5:] if recent_memories else []  # 取最近5章
    }
    
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _collect_chapter_text(chapter: GeneratedChapter) -> str:
    """
    将章节场景拼接成纯文本，供一致性检测使用
    参考 orchestrator._collect_chapter_text
    """
    return "\n\n".join(
        [f"场景 {scene.scene_number}:\n{scene.content}" for scene in chapter.scenes]
    )
