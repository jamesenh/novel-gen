"""章节计划节点 - 生成 chapter_XXX_plan.json 结构。"""

from typing import Any, Dict

from app.generation.providers import Planner
from app.graph.state import State


def plan_chapter(state: State, planner: Planner) -> Dict[str, Any]:
    """为当前章节生成计划（通过 planner 注入实现）。"""
    plan = planner.plan(state, context_pack=state.get("context_pack"))
    return {"chapter_plan": plan}
