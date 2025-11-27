"""
LangGraph 工作流定义
定义小说生成的 StateGraph 工作流

开发者: jamesenh, 开发时间: 2025-11-21
更新: 2025-11-25 - 使用 SqliteSaver 替代 MemorySaver 实现检查点持久化
更新: 2025-11-27 - 添加条件边实现状态持久化，自动跳过已完成的节点
"""
import os
import sqlite3
from typing import Literal, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from novelgen.models import NovelGenerationState
from novelgen.runtime.nodes import (
    load_settings_node,
    world_creation_node,
    theme_conflict_creation_node,
    character_creation_node,
    outline_creation_node,
    chapter_planning_node,
    init_chapter_loop_node,
    chapter_generation_node,
    consistency_check_node,
    chapter_revision_node,
    next_chapter_node
)


# ==================== 条件函数：判断是否跳过已完成的节点 ====================
# 更新: 2025-11-27 - 简化跳过逻辑，只检查数据是否存在，不依赖 completed_steps
# 这样更可靠，因为数据的存在性是判断是否完成的最直接证据

def should_skip_world_creation(state: NovelGenerationState) -> Literal["skip", "execute"]:
    """判断是否跳过世界观生成节点

    只检查 world 数据是否已存在，无需依赖 completed_steps
    """
    if state.world is not None:
        print("  ⏭️ world_creation 已完成（world.json 已存在），跳过")
        return "skip"
    return "execute"


def should_skip_theme_conflict(state: NovelGenerationState) -> Literal["skip", "execute"]:
    """判断是否跳过主题冲突生成节点

    只检查 theme_conflict 数据是否已存在
    """
    if state.theme_conflict is not None:
        print("  ⏭️ theme_conflict_creation 已完成（theme_conflict.json 已存在），跳过")
        return "skip"
    return "execute"


def should_skip_character_creation(state: NovelGenerationState) -> Literal["skip", "execute"]:
    """判断是否跳过角色生成节点

    只检查 characters 数据是否已存在
    """
    if state.characters is not None:
        print("  ⏭️ character_creation 已完成（characters.json 已存在），跳过")
        return "skip"
    return "execute"


def should_skip_outline_creation(state: NovelGenerationState) -> Literal["skip", "execute"]:
    """判断是否跳过大纲生成节点

    只检查 outline 数据是否已存在
    """
    if state.outline is not None:
        print("  ⏭️ outline_creation 已完成（outline.json 已存在），跳过")
        return "skip"
    return "execute"


def should_skip_chapter_planning(state: NovelGenerationState) -> Literal["skip", "execute"]:
    """判断是否跳过章节计划生成节点

    检查所有章节的计划是否都已生成
    """
    if not state.outline or not state.outline.chapters:
        return "execute"

    if not state.chapters_plan:
        return "execute"

    # 检查是否所有章节都有计划
    expected_chapters = {ch.chapter_number for ch in state.outline.chapters}
    existing_plans = set(state.chapters_plan.keys())

    if expected_chapters <= existing_plans:
        print(f"  ⏭️ chapter_planning 已完成（{len(existing_plans)} 个章节计划已存在），跳过")
        return "skip"

    # 有部分章节计划缺失，需要执行
    missing = expected_chapters - existing_plans
    print(f"  ⚠️ 缺少章节计划: {sorted(missing)}")
    return "execute"


def should_skip_chapter_generation(state: NovelGenerationState) -> Literal["skip", "execute"]:
    """
    判断当前章节是否需要生成

    检查 current_chapter_number 对应的章节是否已经生成
    """
    chapter_num = state.current_chapter_number
    if chapter_num is None:
        return "execute"

    # 检查该章节是否已生成
    if chapter_num in state.chapters:
        chapter = state.chapters[chapter_num]
        # 检查章节是否有实际内容（至少有一个场景）
        if chapter.scenes and len(chapter.scenes) > 0:
            print(f"  ⏭️ 第 {chapter_num} 章已生成（chapter_{chapter_num:03d}.json 已存在），跳过")
            return "skip"

    return "execute"


# ==================== 跳过节点：空操作，仅用于路由 ====================

def skip_node(state: NovelGenerationState) -> Dict[str, Any]:
    """
    跳过节点 - 不执行任何操作，直接返回空更新

    用于条件边路由时跳过已完成的步骤
    """
    return {}


def create_novel_generation_workflow(checkpointer=None, project_dir: Optional[str] = None):
    """
    创建小说生成工作流（逐章生成模式，支持自动跳过已完成节点）

    工作流结构：
    1. 前置步骤：设置 → [世界观] → [主题冲突] → [角色] → [大纲] → [章节计划]
       - 方括号表示会检查是否已完成，已完成则跳过
    2. 循环生成：[生成单章 → 一致性检测 → 修订(如需要) → 下一章] × N
       - 章节生成也会检查该章是否已存在

    Args:
        checkpointer: 检查点保存器（可选）
        project_dir: 项目目录，用于存储 SQLite 检查点数据库

    Returns:
        编译后的 StateGraph 工作流
    """
    # 创建 StateGraph，使用 NovelGenerationState 作为状态模型
    workflow = StateGraph[NovelGenerationState, None, NovelGenerationState, NovelGenerationState](NovelGenerationState)

    # ==================== 添加节点 ====================
    # 基础节点
    workflow.add_node("load_settings", load_settings_node)
    workflow.add_node("world_creation", world_creation_node)
    workflow.add_node("theme_conflict_creation", theme_conflict_creation_node)
    workflow.add_node("character_creation", character_creation_node)
    workflow.add_node("outline_creation", outline_creation_node)
    workflow.add_node("chapter_planning", chapter_planning_node)
    workflow.add_node("init_chapter_loop", init_chapter_loop_node)
    workflow.add_node("chapter_generation", chapter_generation_node)
    workflow.add_node("consistency_check", consistency_check_node)
    workflow.add_node("chapter_revision", chapter_revision_node)
    workflow.add_node("next_chapter", next_chapter_node)

    # 跳过节点（用于条件边路由）
    workflow.add_node("skip_world", skip_node)
    workflow.add_node("skip_theme_conflict", skip_node)
    workflow.add_node("skip_character", skip_node)
    workflow.add_node("skip_outline", skip_node)
    workflow.add_node("skip_chapter_planning", skip_node)
    workflow.add_node("skip_chapter_generation", skip_node)

    # ==================== 定义边和条件边 ====================

    # START → load_settings（设置总是需要加载）
    workflow.add_edge(START, "load_settings")

    # load_settings → [world_creation 或 skip_world]
    workflow.add_conditional_edges(
        "load_settings",
        should_skip_world_creation,
        {
            "execute": "world_creation",
            "skip": "skip_world"
        }
    )

    # world_creation / skip_world → [theme_conflict_creation 或 skip_theme_conflict]
    workflow.add_conditional_edges(
        "world_creation",
        should_skip_theme_conflict,
        {
            "execute": "theme_conflict_creation",
            "skip": "skip_theme_conflict"
        }
    )
    workflow.add_conditional_edges(
        "skip_world",
        should_skip_theme_conflict,
        {
            "execute": "theme_conflict_creation",
            "skip": "skip_theme_conflict"
        }
    )

    # theme_conflict_creation / skip_theme_conflict → [character_creation 或 skip_character]
    workflow.add_conditional_edges(
        "theme_conflict_creation",
        should_skip_character_creation,
        {
            "execute": "character_creation",
            "skip": "skip_character"
        }
    )
    workflow.add_conditional_edges(
        "skip_theme_conflict",
        should_skip_character_creation,
        {
            "execute": "character_creation",
            "skip": "skip_character"
        }
    )

    # character_creation / skip_character → [outline_creation 或 skip_outline]
    workflow.add_conditional_edges(
        "character_creation",
        should_skip_outline_creation,
        {
            "execute": "outline_creation",
            "skip": "skip_outline"
        }
    )
    workflow.add_conditional_edges(
        "skip_character",
        should_skip_outline_creation,
        {
            "execute": "outline_creation",
            "skip": "skip_outline"
        }
    )

    # outline_creation / skip_outline → [chapter_planning 或 skip_chapter_planning]
    workflow.add_conditional_edges(
        "outline_creation",
        should_skip_chapter_planning,
        {
            "execute": "chapter_planning",
            "skip": "skip_chapter_planning"
        }
    )
    workflow.add_conditional_edges(
        "skip_outline",
        should_skip_chapter_planning,
        {
            "execute": "chapter_planning",
            "skip": "skip_chapter_planning"
        }
    )

    # chapter_planning / skip_chapter_planning → init_chapter_loop
    workflow.add_edge("chapter_planning", "init_chapter_loop")
    workflow.add_edge("skip_chapter_planning", "init_chapter_loop")

    # init_chapter_loop → [chapter_generation 或 skip_chapter_generation]
    workflow.add_conditional_edges(
        "init_chapter_loop",
        should_skip_chapter_generation,
        {
            "execute": "chapter_generation",
            "skip": "skip_chapter_generation"
        }
    )

    # chapter_generation → consistency_check
    workflow.add_edge("chapter_generation", "consistency_check")

    # skip_chapter_generation → next_chapter（跳过的章节直接进入下一章判断）
    workflow.add_edge("skip_chapter_generation", "next_chapter")
    
    # 条件分支 1：一致性检测后决定是否修订
    def should_revise_chapter(state: NovelGenerationState) -> Literal["revise", "continue"]:
        """
        判断是否需要修订章节
        
        检查当前章节的一致性报告，如果有问题则修订
        """
        chapter_number = state.current_chapter_number
        if chapter_number is None:
            return "continue"
        
        # 检查是否有一致性报告
        if chapter_number not in state.consistency_reports:
            return "continue"
        
        report = state.consistency_reports[chapter_number]
        
        # 如果有问题，则需要修订
        if report.issues:
            return "revise"
        else:
            return "continue"
    
    workflow.add_conditional_edges(
        "consistency_check",
        should_revise_chapter,
        {
            "revise": "chapter_revision",
            "continue": "next_chapter"
        }
    )
    
    # 修订后进入下一章判断
    workflow.add_edge("chapter_revision", "next_chapter")
    
    # 条件分支 2：判断是否还有更多章节需要生成，并检查是否需要跳过
    def should_continue_or_skip_generation(state: NovelGenerationState) -> Literal["execute", "skip", "end"]:
        """
        判断是否继续生成下一章，以及是否需要跳过已完成的章节

        返回值：
        - "execute": 继续生成下一章
        - "skip": 下一章已存在，跳过
        - "end": 所有章节已完成
        """
        if state.current_chapter_number is None:
            return "end"

        # 检查下一章是否在计划中
        next_num = state.current_chapter_number + 1
        if next_num not in state.chapters_plan:
            return "end"

        # 检查下一章是否已生成
        if next_num in state.chapters:
            chapter = state.chapters[next_num]
            if chapter.scenes and len(chapter.scenes) > 0:
                print(f"  ⏭️ 第 {next_num} 章已生成，跳过")
                return "skip"

        return "execute"

    workflow.add_conditional_edges(
        "next_chapter",
        should_continue_or_skip_generation,
        {
            "execute": "chapter_generation",
            "skip": "skip_chapter_generation",
            "end": END
        }
    )
    
    # 配置 checkpointer
    # 如果提供了 project_dir，使用 SqliteSaver 持久化检查点
    # 否则降级到 MemorySaver（内存模式，重启后丢失）
    if checkpointer is None:
        if project_dir:
            db_path = os.path.join(project_dir, "workflow_checkpoints.db")
            conn = sqlite3.connect(db_path, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
        else:
            checkpointer = MemorySaver()
    
    # 编译工作流
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


def visualize_workflow(workflow_app, output_format: str = "mermaid") -> str:
    """
    可视化工作流图
    
    Args:
        workflow_app: 编译后的工作流应用
        output_format: 输出格式，支持 "mermaid"
    
    Returns:
        工作流图的可视化表示（字符串）
    """
    if output_format == "mermaid":
        # LangGraph 支持生成 Mermaid 格式
        try:
            # 使用 draw_mermaid 方法
            mermaid_code = workflow_app.get_graph().draw_mermaid()
            return mermaid_code
        except Exception as e:
            return f"# 无法生成 Mermaid 图\n错误: {str(e)}"
    else:
        return f"不支持的格式: {output_format}"


# 注意：不再提供默认工作流实例，因为需要 project_dir 参数来启用持久化
# 请使用 create_novel_generation_workflow(project_dir=...) 创建工作流实例
