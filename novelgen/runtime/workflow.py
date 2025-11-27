"""
LangGraph 工作流定义
定义小说生成的 StateGraph 工作流

开发者: jamesenh, 开发时间: 2025-11-21
更新: 2025-11-25 - 使用 SqliteSaver 替代 MemorySaver 实现检查点持久化
"""
import os
import sqlite3
from typing import Literal, Optional
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


def create_novel_generation_workflow(checkpointer=None, project_dir: Optional[str] = None):
    """
    创建小说生成工作流（逐章生成模式）
    
    工作流结构：
    1. 前置步骤：设置 → 世界观 → 主题冲突 → 角色 → 大纲 → 章节计划
    2. 循环生成：[生成单章 → 一致性检测 → 修订(如需要) → 下一章] × N
    
    Args:
        checkpointer: 检查点保存器（可选）
        project_dir: 项目目录，用于存储 SQLite 检查点数据库
    
    Returns:
        编译后的 StateGraph 工作流
    """
    # 创建 StateGraph，使用 NovelGenerationState 作为状态模型
    workflow = StateGraph[NovelGenerationState, None, NovelGenerationState, NovelGenerationState](NovelGenerationState)
    
    # 添加节点
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
    
    # 定义前置步骤的线性流程边
    workflow.add_edge(START, "load_settings")
    workflow.add_edge("load_settings", "world_creation")
    workflow.add_edge("world_creation", "theme_conflict_creation")
    workflow.add_edge("theme_conflict_creation", "character_creation")
    workflow.add_edge("character_creation", "outline_creation")
    workflow.add_edge("outline_creation", "chapter_planning")
    workflow.add_edge("chapter_planning", "init_chapter_loop")
    
    # 初始化循环后进入章节生成
    workflow.add_edge("init_chapter_loop", "chapter_generation")
    
    # 章节生成后进入一致性检测
    workflow.add_edge("chapter_generation", "consistency_check")
    
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
    
    # 条件分支 2：判断是否还有更多章节需要生成
    def should_continue_generation(state: NovelGenerationState) -> Literal["continue", "end"]:
        """
        判断是否继续生成下一章
        
        检查 current_chapter_number 是否在 chapters_plan 范围内
        """
        if state.current_chapter_number is None:
            return "end"
        
        # 检查下一章是否在计划中
        next_num = state.current_chapter_number + 1
        if next_num in state.chapters_plan:
            return "continue"
        else:
            return "end"
    
    workflow.add_conditional_edges(
        "next_chapter",
        should_continue_generation,
        {
            "continue": "chapter_generation",
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
