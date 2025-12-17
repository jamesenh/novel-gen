"""
LangGraph 工作流定义
定义小说生成的 StateGraph 工作流

作者: jamesenh, 2025-12-17
开发者: jamesenh, 开发时间: 2025-11-21
更新: 2025-11-25 - 使用 SqliteSaver 替代 MemorySaver 实现检查点持久化
更新: 2025-11-27 - 添加条件边实现状态持久化，自动跳过已完成的节点
更新: 2025-11-28 - 添加动态章节扩展支持（evaluate_story_progress, extend_outline, plan_new_chapters）
更新: 2025-11-28 - 添加场景生成子工作流支持（scene_generation_subgraph）
更新: 2025-11-30 - 添加退出调试日志和 SQLite 连接管理
更新: 2025-11-30 - 添加递归限制预估机制，支持环境变量配置和主动停止
"""
import os
import sqlite3
import time
import threading
from typing import Literal, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# 调试模式
DEBUG_EXIT = os.getenv("NOVELGEN_DEBUG", "0") == "1"

# 递归限制配置
# 从环境变量读取，默认 500（足够 80+ 章）
DEFAULT_RECURSION_LIMIT = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "500"))

# 每章预估节点消耗数（用于预估机制）
# chapter_generation + consistency_check + [chapter_revision] + next_chapter + 条件边
ESTIMATED_NODES_PER_CHAPTER = int(os.getenv("LANGGRAPH_NODES_PER_CHAPTER", "6"))


def _debug_log(msg: str):
    """输出调试日志（仅在 DEBUG_EXIT=True 时）"""
    if DEBUG_EXIT:
        timestamp = time.strftime("%H:%M:%S")
        thread_name = threading.current_thread().name
        print(f"[{timestamp}][{thread_name}] 🔍 [workflow] {msg}")

from novelgen.models import NovelGenerationState, SceneGenerationState
from novelgen.runtime.nodes import (
    load_settings_node,
    world_creation_node,
    theme_conflict_creation_node,
    character_creation_node,
    outline_creation_node,
    chapter_planning_node,
    init_chapter_loop_node,
    # 使用新的包装节点替代原来的 chapter_generation_node
    scene_generation_wrapper_node,
    consistency_check_node,
    chapter_revision_node,
    next_chapter_node,
    # 动态章节扩展节点
    evaluate_story_progress_node,
    extend_outline_node,
    plan_new_chapters_node,
    # 场景生成子图节点
    init_scene_loop_node,
    should_generate_scene,
    retrieve_scene_memory_node,
    generate_scene_node,
    save_scene_node,
    next_scene_node,
    has_more_scenes,
    skip_scene_node,
    # 逻辑审查节点
    chapter_logic_review_node
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
    创建小说生成工作流（逐章生成模式，支持自动跳过已完成节点和动态章节扩展）

    工作流结构：
    1. 前置步骤：设置 → [世界观] → [主题冲突] → [角色] → [大纲] → [章节计划]
       - 方括号表示会检查是否已完成，已完成则跳过
    2. 循环生成：[生成单章 → 一致性检测 → 修订(如需要) → 下一章] × N
       - 章节生成也会检查该章是否已存在
    3. 动态扩展：当已规划章节生成完毕且大纲未完成时
       - 评估剧情进度 → 扩展大纲 → 生成新章节计划 → 继续生成

    Args:
        checkpointer: 检查点保存器（可选）
        project_dir: 项目目录，用于存储 SQLite 检查点数据库

    Returns:
        编译后的 StateGraph 工作流
    
    更新: 2025-11-28 - 添加动态章节扩展支持
    """
    # 创建 StateGraph，使用 NovelGenerationState 作为状态模型
    workflow = StateGraph[NovelGenerationState, None, NovelGenerationState, NovelGenerationState](NovelGenerationState)

    # ==================== 添加节点 ====================
    
    # -------------------- 基础节点 --------------------
    # 这些节点按顺序执行，构成小说生成的主要流程
    
    # 加载项目设置节点：从 settings.json 读取配置，初始化 LangGraph 状态
    # 输入：project_dir（项目目录路径）
    # 输出：更新 state.settings, state.project_dir
    workflow.add_node("load_settings", load_settings_node)
    
    # 世界观生成节点：根据用户描述生成完整的世界观设定
    # 输入：state.settings.world_description
    # 输出：state.world (WorldSetting 对象)，保存到 world.json
    workflow.add_node("world_creation", world_creation_node)
    
    # 主题冲突生成节点：生成故事的核心主题和冲突设定
    # 输入：state.settings.theme_description, state.world
    # 输出：state.theme_conflict (ThemeConflict 对象)，保存到 theme_conflict.json
    workflow.add_node("theme_conflict_creation", theme_conflict_creation_node)
    
    # 角色生成节点：生成主角、配角、反派等角色设定
    # 输入：state.world, state.theme_conflict, state.settings.characters_config
    # 输出：state.characters (CharactersConfig 对象)，保存到 characters.json
    workflow.add_node("character_creation", character_creation_node)
    
    # 大纲生成节点：生成故事的整体结构和章节摘要
    # 输入：state.world, state.theme_conflict, state.characters
    # 输出：state.outline (Outline 对象)，保存到 outline.json
    workflow.add_node("outline_creation", outline_creation_node)
    
    # 章节计划生成节点：为每个章节生成详细的场景计划
    # 输入：state.outline, state.characters, state.world
    # 输出：state.chapters_plan (Dict[int, ChapterPlan])，保存到 chapters/chapter_XXX_plan.json
    workflow.add_node("chapter_planning", chapter_planning_node)
    
    # 初始化章节循环节点：设置 current_chapter_number 开始逐章生成
    # 输入：state.chapters_plan
    # 输出：state.current_chapter_number = 1 (或断点续跑的章节号)
    workflow.add_node("init_chapter_loop", init_chapter_loop_node)
    
    # -------------------- 章节生成循环节点 --------------------
    # 这些节点在循环中执行，逐章生成小说内容
    
    # 章节生成节点（场景级断点续跑版本）：逐场景生成章节内容
    # 使用子工作流实现场景级别的断点续跑支持
    # 输入：state.current_chapter_number, state.chapters_plan[n]
    # 输出：state.chapters[n] (GeneratedChapter 对象)，保存到 chapters/chapter_XXX.json
    workflow.add_node("chapter_generation", scene_generation_wrapper_node)
    
    # 逻辑审查节点：检查新生成章节的逻辑连贯性（可配置）
    # 输入：state.chapters[current], state.chapters_plan[current]
    # 输出：如果启用且触发阻断，写入 pending revision
    # 开发者: jamesenh, 开发时间: 2025-12-16
    workflow.add_node("chapter_logic_review", chapter_logic_review_node)
    
    # 一致性检查节点：检查新生成章节与已有内容的一致性
    # 输入：state.chapters[current], state.characters, state.world
    # 输出：state.consistency_reports[n] (ConsistencyReport 对象)
    workflow.add_node("consistency_check", consistency_check_node)
    
    # 章节修订节点：根据一致性报告修订章节内容
    # 输入：state.chapters[current], state.consistency_reports[current]
    # 输出：更新后的 state.chapters[n]
    workflow.add_node("chapter_revision", chapter_revision_node)
    
    # 下一章节节点：递增章节号，准备进入下一章生成
    # 输入：state.current_chapter_number
    # 输出：state.current_chapter_number += 1
    workflow.add_node("next_chapter", next_chapter_node)
    
    # -------------------- 动态章节扩展节点 --------------------
    # 当已规划章节全部生成完毕但故事尚未结束时触发
    
    # 剧情进度评估节点：评估当前故事进度，决定是否继续扩展
    # 输入：state.chapters, state.outline
    # 输出：state.story_progress_evaluation (continue/wrap_up/force_end)
    workflow.add_node("evaluate_story_progress", evaluate_story_progress_node)
    
    # 大纲扩展节点：根据评估结果扩展大纲，添加新章节摘要
    # 输入：state.story_progress_evaluation, state.outline
    # 输出：更新 state.outline.chapters，添加新的 ChapterSummary
    workflow.add_node("extend_outline", extend_outline_node)
    
    # 新章节计划生成节点：为新扩展的章节生成场景计划
    # 输入：扩展后的 state.outline
    # 输出：更新 state.chapters_plan，添加新章节的 ChapterPlan
    workflow.add_node("plan_new_chapters", plan_new_chapters_node)

    # -------------------- 跳过节点（用于条件边路由）--------------------
    # 当对应数据已存在时，通过这些节点跳过已完成的步骤
    # 所有跳过节点都使用同一个空操作函数 skip_node
    
    # 跳过世界观生成：当 world.json 已存在时触发
    workflow.add_node("skip_world", skip_node)
    
    # 跳过主题冲突生成：当 theme_conflict.json 已存在时触发
    workflow.add_node("skip_theme_conflict", skip_node)
    
    # 跳过角色生成：当 characters.json 已存在时触发
    workflow.add_node("skip_character", skip_node)
    
    # 跳过大纲生成：当 outline.json 已存在时触发
    workflow.add_node("skip_outline", skip_node)
    
    # 跳过章节计划生成：当所有章节计划文件都已存在时触发
    workflow.add_node("skip_chapter_planning", skip_node)
    
    # 跳过章节生成：当当前章节的内容文件已存在时触发
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

    # chapter_generation → chapter_logic_review
    workflow.add_edge("chapter_generation", "chapter_logic_review")
    
    # 条件分支：逻辑审查后决定是继续到一致性检查还是因阻断而结束
    # 开发者: jamesenh, 开发时间: 2025-12-16
    def should_continue_after_logic_review(state: NovelGenerationState) -> Literal["continue", "end"]:
        """
        判断逻辑审查后是否继续
        
        检查是否存在逻辑审查触发的阻断（pending revision）
        """
        chapter_number = state.current_chapter_number
        if chapter_number is None:
            return "continue"
        
        # 检查是否在 error_messages 中有逻辑审查阻断标记
        block_key = f"logic_review_block_{chapter_number}"
        if block_key in state.error_messages:
            return "end"
        
        return "continue"
    
    workflow.add_conditional_edges(
        "chapter_logic_review",
        should_continue_after_logic_review,
        {
            "continue": "consistency_check",
            "end": END
        }
    )

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
    
    # 条件分支 2：判断是否继续生成、需要评估扩展、还是结束
    # 更新: 2025-11-28 - 支持动态章节扩展
    # 更新: 2025-11-30 - 添加递归限制预估检查
    def should_evaluate_or_continue(state: NovelGenerationState) -> Literal["execute", "skip", "evaluate", "end"]:
        """
        判断下一步操作：继续生成、跳过、评估扩展、还是结束
        
        返回值：
        - "execute": 继续生成下一章
        - "skip": 下一章已存在，跳过
        - "evaluate": 需要评估剧情进度（已规划章节已完成但大纲未完整）
        - "end": 所有章节已完成且大纲已完整，或递归限制不足
        
        更新: 2025-11-30 - 添加递归限制预估检查，防止 GraphRecursionError
        """
        # 检查是否因递归限制主动停止
        if state.should_stop_early:
            print(f"  ⏹️ 因递归限制预估不足，已主动停止")
            return "end"
        
        # 预估检查：剩余递归次数是否足够完成下一章
        remaining_steps = state.recursion_limit - state.node_execution_count
        if remaining_steps < ESTIMATED_NODES_PER_CHAPTER:
            print(f"  ⚠️ 剩余递归次数({remaining_steps}) < 每章所需({ESTIMATED_NODES_PER_CHAPTER})，主动停止")
            print(f"     已执行节点数: {state.node_execution_count}, 递归限制: {state.recursion_limit}")
            return "end"
        
        if state.current_chapter_number is None:
            return "end"
        
        # 修复: 2025-11-30 - 检查当前章节号，而不是 +1
        # next_chapter 节点已经将章节号增加了，这里应该检查当前章节是否需要执行
        current_num = state.current_chapter_number
        
        # 检查当前章节是否在计划中
        if current_num in state.chapters_plan:
            # 当前章节已有计划，检查是否已生成
            if current_num in state.chapters:
                chapter = state.chapters[current_num]
                if chapter.scenes and len(chapter.scenes) > 0:
                    print(f"  ⏭️ 第 {current_num} 章已生成，跳过")
                    return "skip"
            print(f"  ▶️ 第 {current_num} 章待生成")
            return "execute"
        
        # 当前章节不在计划中，检查是否需要扩展大纲
        if state.outline and not state.outline.is_complete:
            # 大纲未完成，需要评估是否扩展
            print(f"  📊 已完成所有已规划章节，需要评估剧情进度")
            return "evaluate"
        
        # 大纲已完成且所有章节都已处理，结束生成
        print(f"  ✅ 所有 {current_num - 1} 章已完成，大纲已完整")
        return "end"

    workflow.add_conditional_edges(
        "next_chapter",
        should_evaluate_or_continue,
        {
            "execute": "chapter_generation",
            "skip": "skip_chapter_generation",
            "evaluate": "evaluate_story_progress",
            "end": END
        }
    )
    
    # 条件分支 3：评估后决定是扩展还是结束
    def should_extend_or_end(state: NovelGenerationState) -> Literal["extend", "end"]:
        """
        根据剧情进度评估结果决定是扩展大纲还是结束
        
        返回值：
        - "extend": 扩展大纲（continue/wrap_up/force_end 都需要生成新章节）
        - "end": 无法继续（异常情况）
        """
        if state.story_progress_evaluation is None:
            print("  ⚠️ 评估结果为空，结束生成")
            return "end"
        
        # 所有评估结果都需要扩展大纲（即使是 force_end 也要生成结局章节）
        return "extend"
    
    workflow.add_conditional_edges(
        "evaluate_story_progress",
        should_extend_or_end,
        {
            "extend": "extend_outline",
            "end": END
        }
    )
    
    # extend_outline → plan_new_chapters
    workflow.add_edge("extend_outline", "plan_new_chapters")
    
    # plan_new_chapters → init_chapter_loop（重新初始化章节循环以处理新章节）
    workflow.add_edge("plan_new_chapters", "init_chapter_loop")
    
    # 配置 checkpointer
    # 如果提供了 project_dir，使用 SqliteSaver 持久化检查点
    # 否则降级到 MemorySaver（内存模式，重启后丢失）
    if checkpointer is None:
        if project_dir:
            db_path = os.path.join(project_dir, "workflow_checkpoints.db")
            _debug_log(f"创建 SQLite 连接: {db_path}")
            conn = sqlite3.connect(db_path, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            _debug_log("SqliteSaver 已创建")
        else:
            _debug_log("使用 MemorySaver（内存模式）")
            checkpointer = MemorySaver()
    
    # 编译工作流
    # 更新: 2025-11-30 - 递归限制现在通过 invoke/stream 的 config 传入
    # 这里不再在 compile 时设置，因为 compile 不支持 recursion_limit 参数
    _debug_log(f"编译工作流... (默认递归限制: {DEFAULT_RECURSION_LIMIT})")
    app = workflow.compile(checkpointer=checkpointer)
    _debug_log("工作流编译完成")
    
    return app


def get_default_recursion_limit() -> int:
    """获取默认递归限制值（从环境变量读取）
    
    Returns:
        int: 递归限制值，默认 500
    """
    return DEFAULT_RECURSION_LIMIT


def get_estimated_nodes_per_chapter() -> int:
    """获取每章预估节点消耗数
    
    Returns:
        int: 每章预估节点数，默认 6
    """
    return ESTIMATED_NODES_PER_CHAPTER


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


# ==================== 场景生成子工作流 ====================

def create_scene_generation_subgraph():
    """
    创建场景生成子工作流
    
    子工作流结构:
    - init_scene_loop: 初始化场景循环
    - [条件边] should_generate_scene:
        - "skip" → skip_scene → next_scene
        - "execute" → retrieve_memory → generate_scene → save_scene → next_scene
    - [条件边] has_more_scenes:
        - "continue" → init_scene_loop（回到条件判断）
        - "end" → END
    
    注意：子图不设置 checkpointer，由父图自动传播。
    
    开发者: jamesenh, 开发时间: 2025-11-28
    """
    builder = StateGraph(SceneGenerationState)
    
    # 添加节点
    builder.add_node("init_scene_loop", init_scene_loop_node)
    builder.add_node("retrieve_memory", retrieve_scene_memory_node)
    builder.add_node("generate_scene", generate_scene_node)
    builder.add_node("save_scene", save_scene_node)
    builder.add_node("next_scene", next_scene_node)
    builder.add_node("skip_scene", skip_scene_node)
    
    # 定义边
    builder.add_edge(START, "init_scene_loop")
    
    # init_scene_loop → [条件边] should_generate_scene
    builder.add_conditional_edges(
        "init_scene_loop",
        should_generate_scene,
        {"skip": "skip_scene", "execute": "retrieve_memory"}
    )
    
    # 生成流程
    builder.add_edge("retrieve_memory", "generate_scene")
    builder.add_edge("generate_scene", "save_scene")
    builder.add_edge("save_scene", "next_scene")
    builder.add_edge("skip_scene", "next_scene")
    
    # next_scene → [条件边] has_more_scenes
    builder.add_conditional_edges(
        "next_scene",
        has_more_scenes,
        {"continue": "init_scene_loop", "end": END}  # 回到 init_scene_loop 以触发条件判断
    )
    
    # 注意：不传 checkpointer，由父图传播
    return builder.compile()


# 创建全局子图实例（供 scene_generation_wrapper_node 使用）
scene_generation_subgraph = create_scene_generation_subgraph()


# 注意：不再提供默认工作流实例，因为需要 project_dir 参数来启用持久化
# 请使用 create_novel_generation_workflow(project_dir=...) 创建工作流实例
