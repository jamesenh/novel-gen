"""LangGraph 工作流的 State 定义。

State 是共享黑板：节点之间只通过 State 通信，不直接传参。
每个节点返回增量更新。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
from uuid import uuid4


class Issue(TypedDict, total=False):
    """单个审计问题。"""

    id: str
    severity: str  # blocker, major, minor
    category: str  # world_rule, character, timeline, knowledge, thread, pov_style
    summary: str
    evidence: Dict[str, Any]
    fix_instructions: str


class AuditResult(TypedDict, total=False):
    """审计结果。"""

    chapter_id: int
    issues: List[Issue]
    blocker_count: int
    major_count: int
    minor_count: int
    updates: Dict[str, Any]  # Suggested updates to bible/memory


class State(TypedDict, total=False):
    """工作流状态 - 所有节点的共享黑板。

    字段分组:
    - requirements: 初始提示词和约束
    - bible: 世界观/角色/时间线/线程（唯一真值来源）
    - outline: 全局故事大纲
    - runtime: 循环控制（chapter_id、revision_round、阈值）
    - artifacts: 当前章节计划、草稿、审计结果
    - status: 最终状态标志
    """

    # Identifiers
    run_id: str
    project_name: str

    # Requirements (from prompt)
    prompt: str
    requirements: Dict[str, Any]

    # Bible (Single Source of Truth)
    world: Dict[str, Any]
    characters: Dict[str, Any]
    theme_conflict: Dict[str, Any]

    # Outline
    outline: Dict[str, Any]

    # Runtime control
    current_chapter: int
    num_chapters: int
    revision_round: int
    revision_id: str  # 当前修订标识符 (run_id + chapter_id + revision_round)
    max_revision_rounds: int
    qa_blocker_max: int  # blocker 阈值（必须 <= 此值才能推进，通常为 0）
    qa_major_max: int  # major 问题最大数（用于警告，未来可扩展）

    # Current chapter artifacts (in-memory, not yet persisted)
    chapter_plan: Dict[str, Any]
    chapter_draft: Dict[str, Any]
    audit_result: AuditResult
    context_pack: Dict[str, Any]

    # Status flags
    needs_human_review: bool
    completed: bool
    error: Optional[str]


def create_initial_state(
    project_name: str,
    num_chapters: int = 1,
    prompt: str = "",
    max_revision_rounds: int = 3,
    qa_blocker_max: int = 0,
    qa_major_max: int = 3,
) -> State:
    """为新的工作流运行创建初始状态。

    Args:
        project_name: 项目名称。
        num_chapters: 要生成的章节数。
        prompt: 用户的初始提示词。
        max_revision_rounds: 每章最大修订次数。
        qa_blocker_max: blocker 问题阈值（必须 <= 此值才能推进）。
        qa_major_max: major 问题最大数（用于警告）。

    Returns:
        准备好用于图调用的初始 State 字典。
    """
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    return State(
        run_id=run_id,
        project_name=project_name,
        prompt=prompt,
        requirements={},
        world={},
        characters={},
        theme_conflict={},
        outline={},
        current_chapter=1,
        num_chapters=num_chapters,
        revision_round=0,
        revision_id=f"{run_id}_ch001_r0",  # 初始修订 ID
        max_revision_rounds=max_revision_rounds,
        qa_blocker_max=qa_blocker_max,
        qa_major_max=qa_major_max,
        chapter_plan={},
        chapter_draft={},
        audit_result={},
        context_pack={},
        needs_human_review=False,
        completed=False,
        error=None,
    )
