"""工作流图的路由逻辑。

实现:
- Blocker 门禁: blocker > 0 强制进入修订循环
- 章节推进: blocker == 0 允许进入下一章
- 修订上限: 达到最大轮次触发人工审核
"""

from typing import Literal

from app.graph.state import State


def should_revise(state: State) -> Literal["revise", "store", "human_review"]:
    """判断章节是否需要修订、可以存储、还是需要人工审核。

    决策逻辑:
    1. 如果 blocker_count <= qa_blocker_max -> store（通常 qa_blocker_max=0）
    2. 如果 blocker_count > qa_blocker_max 且 revision_round >= max_rounds -> human_review
    3. 如果 blocker_count > qa_blocker_max 且 revision_round < max_rounds -> revise

    Args:
        state: 当前工作流状态。

    Returns:
        "revise"、"store" 或 "human_review"。
    """
    audit = state.get("audit_result", {})
    blocker_count = audit.get("blocker_count", 0)
    revision_round = state.get("revision_round", 0)
    max_rounds = state.get("max_revision_rounds", 3)
    qa_blocker_max = state.get("qa_blocker_max", 0)  # 默认必须为 0 才能推进

    if blocker_count <= qa_blocker_max:
        return "store"

    if revision_round >= max_rounds:
        return "human_review"

    return "revise"


def should_continue_chapters(state: State) -> Literal["next_chapter", "complete"]:
    """判断工作流应该继续下一章还是完成。

    Args:
        state: 当前工作流状态。

    Returns:
        "next_chapter" 或 "complete"。
    """
    current = state.get("current_chapter", 1)
    total = state.get("num_chapters", 1)

    if current < total:
        return "next_chapter"
    return "complete"


def advance_chapter(state: State) -> dict:
    """推进到下一章。

    Args:
        state: 当前工作流状态。

    Returns:
        递增 current_chapter 并重置 revision_round 的状态更新。
    """
    run_id = state.get("run_id", "unknown")
    next_chapter = state.get("current_chapter", 1) + 1
    return {
        "current_chapter": next_chapter,
        "revision_round": 0,
        "revision_id": f"{run_id}_ch{next_chapter:03d}_r0",
        "chapter_plan": {},
        "chapter_draft": {},
        "audit_result": {},
        "context_pack": {},
    }


def mark_human_review(state: State) -> dict:
    """标记当前章节需要人工审核。

    Args:
        state: 当前工作流状态。

    Returns:
        设置 needs_human_review 标志的状态更新。
    """
    return {"needs_human_review": True}


def mark_complete(state: State) -> dict:
    """标记工作流已完成。

    Args:
        state: 当前工作流状态。

    Returns:
        设置 completed 标志的状态更新。
    """
    return {"completed": True}
