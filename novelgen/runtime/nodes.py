"""
LangGraph 节点包装器
为现有 LangChain chains 提供 LangGraph 节点接口

开发者: jamesenh, 开发时间: 2025-11-21
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from novelgen.models import (
    NovelGenerationState, Settings, WorldSetting, ThemeConflict,
    CharactersConfig, Outline, ChapterPlan, GeneratedChapter,
    ChapterMemoryEntry, ConsistencyReport
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
    
    设置 current_chapter_number 为第一章，准备开始逐章生成
    """
    try:
        if not state.chapters_plan:
            raise ValueError("chapters_plan 为空，无法初始化章节循环")
        
        # 找到第一个章节编号（通常是1，但为了健壮性，使用最小值）
        first_chapter_number = min(state.chapters_plan.keys())
        
        print(f"🔄 初始化章节循环，从第 {first_chapter_number} 章开始")
        
        return {
            "current_chapter_number": first_chapter_number,
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


def chapter_generation_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    章节文本生成节点（单章生成模式）
    
    根据 state.current_chapter_number 生成指定章节的场景文本
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
            generated_scenes = []
            for scene_plan in plan.scenes:
                scene = generate_scene_text(
                    scene_plan=scene_plan,
                    world_setting=state.world,
                    characters=state.characters,
                    previous_summary="",
                    chapter_context="",
                    scene_memory_context=None,
                    verbose=False
                )
                generated_scenes.append(scene)
            
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
        
        return {
            "chapters": chapters,
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
