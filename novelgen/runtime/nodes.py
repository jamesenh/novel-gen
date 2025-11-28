"""
LangGraph 节点包装器
为现有 LangChain chains 提供 LangGraph 节点接口

开发者: jamesenh, 开发时间: 2025-11-21
更新: 2025-11-27 - 修复 Mem0 集成问题，添加记忆上下文检索功能
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from novelgen.models import (
    NovelGenerationState, Settings, WorldSetting, ThemeConflict,
    CharactersConfig, Outline, ChapterPlan, GeneratedChapter,
    ChapterMemoryEntry, ConsistencyReport, SceneMemoryContext
)
from novelgen.chains.world_chain import generate_world
from novelgen.chains.theme_conflict_chain import generate_theme_conflict
from novelgen.chains.characters_chain import generate_characters
from novelgen.chains.outline_chain import generate_outline
from novelgen.chains.chapters_plan_chain import generate_chapter_plan
from novelgen.chains.scene_text_chain import generate_scene_text
from novelgen.runtime.consistency import run_consistency_check
from novelgen.chains.chapter_revision_chain import revise_chapter
from novelgen.runtime.memory import generate_chapter_memory_entry
from novelgen.runtime.summary import summarize_scenes
from typing import List


def load_settings_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    加载项目配置节点
    
    从项目目录加载 settings.json 文件到状态中
    """
    try:
        settings_path = os.path.join(state.project_dir, "settings.json")
        
        if not os.path.exists(settings_path):
            return {
                "current_step": "load_settings",
                "failed_steps": state.failed_steps + ["load_settings"],
                "error_messages": {**state.error_messages, "load_settings": f"settings.json 不存在: {settings_path}"}
            }
        
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        
        settings = Settings(**settings_data)
        
        return {
            "settings": settings,
            "current_step": "load_settings",
            "completed_steps": state.completed_steps + ["load_settings"]
        }
    
    except Exception as e:
        return {
            "current_step": "load_settings",
            "failed_steps": state.failed_steps + ["load_settings"],
            "error_messages": {**state.error_messages, "load_settings": str(e)}
        }


def world_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    世界观生成节点
    
    调用 generate_world chain 生成世界观设定
    """
    try:
        if state.settings is None:
            raise ValueError("settings 未加载，无法生成世界观")
        
        # 调用现有 chain
        world = generate_world(
            user_input=state.settings.world_description,
            verbose=False
        )
        
        # 保存到 JSON
        world_path = os.path.join(state.project_dir, "world.json")
        with open(world_path, 'w', encoding='utf-8') as f:
            json.dump(world.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {
            "world": world,
            "current_step": "world_creation",
            "completed_steps": state.completed_steps + ["world_creation"]
        }
    
    except Exception as e:
        return {
            "current_step": "world_creation",
            "failed_steps": state.failed_steps + ["world_creation"],
            "error_messages": {**state.error_messages, "world_creation": str(e)}
        }


def theme_conflict_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    主题冲突生成节点
    
    调用 generate_theme_conflict chain 生成主题与冲突
    """
    try:
        if state.settings is None or state.world is None:
            raise ValueError("settings 或 world 未加载")
        
        theme_conflict = generate_theme_conflict(
            world_setting=state.world,
            user_input=state.settings.theme_description or "",
            verbose=False
        )
        
        # 保存到 JSON
        theme_path = os.path.join(state.project_dir, "theme_conflict.json")
        with open(theme_path, 'w', encoding='utf-8') as f:
            json.dump(theme_conflict.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {
            "theme_conflict": theme_conflict,
            "current_step": "theme_conflict_creation",
            "completed_steps": state.completed_steps + ["theme_conflict_creation"]
        }
    
    except Exception as e:
        return {
            "current_step": "theme_conflict_creation",
            "failed_steps": state.failed_steps + ["theme_conflict_creation"],
            "error_messages": {**state.error_messages, "theme_conflict_creation": str(e)}
        }


def character_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    角色生成节点
    
    调用 generate_characters chain 生成角色配置
    并初始化角色状态到 Mem0
    """
    try:
        if state.settings is None or state.world is None or state.theme_conflict is None:
            raise ValueError("settings, world 或 theme_conflict 未加载")
        
        characters = generate_characters(
            world_setting=state.world,
            theme_conflict=state.theme_conflict,
            verbose=False
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
            "completed_steps": state.completed_steps + ["character_creation"]
        }
    
    except Exception as e:
        return {
            "current_step": "character_creation",
            "failed_steps": state.failed_steps + ["character_creation"],
            "error_messages": {**state.error_messages, "character_creation": str(e)}
        }


def outline_creation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    大纲生成节点
    
    调用 generate_outline chain 生成小说大纲
    """
    try:
        if not all([state.settings, state.world, state.theme_conflict, state.characters]):
            raise ValueError("前置步骤未完成，无法生成大纲")
        
        outline = generate_outline(
            world_setting=state.world,
            theme_conflict=state.theme_conflict,
            characters=state.characters,
            num_chapters=state.settings.num_chapters,
            verbose=False
        )
        
        # 保存到 JSON
        outline_path = os.path.join(state.project_dir, "outline.json")
        with open(outline_path, 'w', encoding='utf-8') as f:
            json.dump(outline.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {
            "outline": outline,
            "current_step": "outline_creation",
            "completed_steps": state.completed_steps + ["outline_creation"]
        }
    
    except Exception as e:
        return {
            "current_step": "outline_creation",
            "failed_steps": state.failed_steps + ["outline_creation"],
            "error_messages": {**state.error_messages, "outline_creation": str(e)}
        }


def init_chapter_loop_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    初始化章节循环节点

    设置 current_chapter_number 为第一个未完成的章节，支持断点续跑。
    如果所有章节都已完成，则设置为最后一章+1（将触发结束条件）。

    更新: 2025-11-27 - 修改为找到第一个未完成的章节，而不是总是从第1章开始
    """
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

        if first_incomplete_chapter is not None:
            # 有未完成的章节，从该章节开始
            if completed_count > 0:
                print(f"🔄 检测到已完成 {completed_count} 章，从第 {first_incomplete_chapter} 章继续")
            else:
                print(f"🔄 初始化章节循环，从第 {first_incomplete_chapter} 章开始")

            return {
                "current_chapter_number": first_incomplete_chapter,
                "current_step": "init_chapter_loop",
                "completed_steps": state.completed_steps + ["init_chapter_loop"]
            }
        else:
            # 所有章节都已完成
            last_chapter = max(planned_chapters)
            print(f"✅ 所有 {len(planned_chapters)} 章都已完成，无需生成")

            # 设置为最后一章，让后续的条件边能正确处理
            return {
                "current_chapter_number": last_chapter,
                "current_step": "init_chapter_loop",
                "completed_steps": state.completed_steps + ["init_chapter_loop"]
            }

    except Exception as e:
        return {
            "current_step": "init_chapter_loop",
            "failed_steps": state.failed_steps + ["init_chapter_loop"],
            "error_messages": {**state.error_messages, "init_chapter_loop": str(e)}
        }


def next_chapter_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    递增章节编号节点
    
    将 current_chapter_number 增加 1，准备处理下一章
    """
    try:
        if state.current_chapter_number is None:
            raise ValueError("current_chapter_number 未设置")
        
        next_chapter_number = state.current_chapter_number + 1
        
        print(f"➡️  准备处理第 {next_chapter_number} 章")
        
        return {
            "current_chapter_number": next_chapter_number,
            "current_step": "next_chapter"
        }
    
    except Exception as e:
        return {
            "current_step": "next_chapter",
            "failed_steps": state.failed_steps + ["next_chapter"],
            "error_messages": {**state.error_messages, "next_chapter": str(e)}
        }


def chapter_planning_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    章节计划生成节点
    
    为 outline 中的所有章节生成详细计划
    注：这是批量生成节点，处理所有章节
    """
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
                    verbose=False
                )
                
                # 保存计划
                with open(plan_path, 'w', encoding='utf-8') as f:
                    json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)
                
                chapters_plan[chapter_number] = plan
        
        return {
            "chapters_plan": chapters_plan,
            "current_step": "chapter_planning",
            "completed_steps": state.completed_steps + ["chapter_planning"]
        }
    
    except Exception as e:
        return {
            "current_step": "chapter_planning",
            "failed_steps": state.failed_steps + ["chapter_planning"],
            "error_messages": {**state.error_messages, "chapter_planning": str(e)}
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
        scene_summaries_text = summarize_scenes(chapter.scenes)
        scene_summaries = scene_summaries_text.split("\n") if scene_summaries_text else []
        
        # 聚合摘要
        aggregated_summary = f"第{chapter_number}章「{chapter.chapter_title}」共{len(chapter.scenes)}个场景，{chapter.total_words}字"
        
        # 调用 LLM 生成章节记忆条目
        memory_entry = generate_chapter_memory_entry(
            chapter=chapter,
            outline_summary=outline_summary,
            scene_summaries=scene_summaries,
            aggregated_summary=aggregated_summary,
            verbose=False
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
                    verbose=False
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
            "completed_steps": state.completed_steps + [f"chapter_generation_{chapter_number}"]
        }

    except Exception as e:
        return {
            "current_step": "chapter_generation",
            "failed_steps": state.failed_steps + ["chapter_generation"],
            "error_messages": {**state.error_messages, "chapter_generation": str(e)}
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
    try:
        # 获取当前章节编号
        chapter_number = state.current_chapter_number
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
            verbose=False
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
            "completed_steps": state.completed_steps + [f"consistency_check_{chapter_number}"]
        }
    
    except Exception as e:
        return {
            "current_step": "consistency_check",
            "failed_steps": state.failed_steps + [f"consistency_check_{chapter_number}"],
            "error_messages": {**state.error_messages, f"consistency_check_{chapter_number}": str(e)}
        }


def chapter_revision_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    章节修订节点
    
    根据一致性检测结果自动修订章节
    """
    try:
        # 获取当前章节编号
        chapter_number = state.current_chapter_number
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
                "completed_steps": state.completed_steps + [f"chapter_revision_{chapter_number}_skipped"]
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
            verbose=False
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
            "completed_steps": state.completed_steps + [f"chapter_revision_{chapter_number}"]
        }
    
    except Exception as e:
        print(f"❌ 修订失败：{str(e)}")
        return {
            "current_step": "chapter_revision",
            "failed_steps": state.failed_steps + [f"chapter_revision_{chapter_number}"],
            "error_messages": {**state.error_messages, f"chapter_revision_{chapter_number}": str(e)}
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
