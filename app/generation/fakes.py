"""测试用的确定性 Fake Providers。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.generation.template_providers import (
    TemplatePatcher,
    TemplatePlanner,
    TemplateWriter,
)
from app.graph.state import Issue, State
from app.schemas.base import add_metadata


class FakePlanner(TemplatePlanner):
    """测试用 planner：直接复用模板 planner（确定性）。"""

    pass


class FakeWriter(TemplateWriter):
    """测试用 writer：可选择输出占位正文以触发修订循环。"""

    def __init__(self, *, placeholder: bool = False) -> None:
        self._placeholder = placeholder

    def write(
        self,
        state: State,
        plan: Dict[str, Any],
        *,
        context_pack: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if not self._placeholder:
            return super().write(state, plan, context_pack=context_pack)

        chapter_id = state.get("current_chapter", 1)
        run_id = state.get("run_id", "unknown")
        revision_id = state.get("revision_id", "unknown")
        draft = add_metadata(
            {
                "chapter_id": chapter_id,
                "run_id": run_id,
                "revision_id": revision_id,
                "title": f"第{chapter_id}章",
                "scenes": [
                    {
                        "scene_id": f"{chapter_id}_1",
                        "location": "待定",
                        "characters": [],
                        "purpose": plan.get("goal", ""),
                        "content": f"[第{chapter_id}章正文内容 - 由LLM生成]",
                    }
                ],
                "word_count": 0,
            },
            generator=f"fake-writer/{run_id}/{revision_id}",
        )
        return draft


class FakePatcher(TemplatePatcher):
    """测试用 patcher：复用模板 patcher（确定性）。"""

    def apply(
        self,
        state: State,
        draft: Dict[str, Any],
        issues: List[Issue],
        *,
        context_pack: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return super().apply(state, draft, issues, context_pack=context_pack)
