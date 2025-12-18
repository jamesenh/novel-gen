"""章节写作节点 - 根据计划生成章节内容。"""

from typing import Any, Dict

from app.generation.providers import Writer
from app.graph.state import State


def write_chapter(state: State, writer: Writer) -> Dict[str, Any]:
    """根据计划生成章节内容（通过 writer 注入实现）。"""
    plan = state.get("chapter_plan", {})
    draft = writer.write(state, plan, context_pack=state.get("context_pack"))
    return {"chapter_draft": draft}
