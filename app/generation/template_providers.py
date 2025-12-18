"""无外部依赖的模板型 Provider 实现（默认实现）。

目的：
- 让 v2 在没有 LLM 的情况下也能“真实产出”非占位文本，便于端到端测试与日常演示
- 产出结构稳定、可被审计插件与检索模块消费的内容
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.graph.state import Issue, State
from app.schemas.base import add_metadata

_WS_RE = re.compile(r"\s+")


def _generator(state: State) -> str:
    run_id = state.get("run_id", "unknown")
    revision_id = state.get("revision_id", "unknown")
    return f"novel-gen-v2/{run_id}/{revision_id}"


def _word_count(text: str) -> int:
    """粗略字数统计：去空白后长度（兼容中文/英文）。"""
    return len(_WS_RE.sub("", text or ""))


def _pick_protagonist_name(characters: Dict[str, Any]) -> str:
    p = characters.get("protagonist", {})
    return p.get("name") or "主角"


class TemplatePlanner:
    """基于 outline 的模板规划器。"""

    def plan(
        self, state: State, *, context_pack: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        chapter_id = state.get("current_chapter", 1)
        outline = state.get("outline", {}) or {}
        chapters_outline = outline.get("chapters", []) or []
        chapter_outline = (
            chapters_outline[chapter_id - 1]
            if len(chapters_outline) >= chapter_id
            else {}
        )

        characters = state.get("characters", {}) or {}
        protagonist = _pick_protagonist_name(characters)
        world = state.get("world", {}) or {}
        realm_name = ""
        realms = world.get("realms") or []
        if realms and isinstance(realms, list):
            realm_name = (
                realms[0].get("name") if isinstance(realms[0], dict) else str(realms[0])
            )

        scenes: List[Dict[str, Any]] = [
            {
                "scene_id": f"{chapter_id}_1",
                "location": realm_name or "城外古道",
                "characters": [protagonist],
                "purpose": "建立当章目标与阻力",
                "key_actions": ["获得线索", "遭遇阻拦", "做出选择"],
            }
        ]

        plan = add_metadata(
            {
                "chapter_id": chapter_id,
                "run_id": state.get("run_id", "unknown"),
                "revision_id": state.get("revision_id", "unknown"),
                "pov": chapter_outline.get("pov", protagonist),
                "goal": chapter_outline.get("goal", f"第{chapter_id}章目标"),
                "conflict": chapter_outline.get("conflict", "阻力与代价"),
                "turn": chapter_outline.get("turn", "关键转折"),
                "reveal": chapter_outline.get("reveal", []),
                "threads_advance": chapter_outline.get("threads", []),
                "must_include": chapter_outline.get("must_include", []),
                "must_avoid": chapter_outline.get("must_avoid", []),
                "scenes": scenes,
            },
            generator=_generator(state),
        )
        return plan


class TemplateWriter:
    """基于 plan 的模板写作者（产出非占位正文）。"""

    def write(
        self,
        state: State,
        plan: Dict[str, Any],
        *,
        context_pack: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        chapter_id = state.get("current_chapter", 1)
        protagonist = plan.get("pov") or _pick_protagonist_name(
            state.get("characters", {}) or {}
        )
        goal = plan.get("goal", "")
        conflict = plan.get("conflict", "")
        turn = plan.get("turn", "")

        scenes_out: List[Dict[str, Any]] = []
        for idx, s in enumerate(plan.get("scenes", []) or [], start=1):
            location = s.get("location", "某处")
            content = (
                f"{location}，{protagonist}压下心绪，回想起此行的目标：{goal}。"
                f"然而阻力很快显形——{conflict}。"
                f"他在犹豫与决断之间前行，直到{turn}，局势骤然翻转。"
            )
            scenes_out.append(
                {
                    "scene_id": s.get("scene_id", f"{chapter_id}_{idx}"),
                    "location": location,
                    "characters": s.get("characters", [protagonist]),
                    "purpose": s.get("purpose", ""),
                    "content": content,
                }
            )

        full_text = "\n".join([sc.get("content", "") for sc in scenes_out])
        draft = add_metadata(
            {
                "chapter_id": chapter_id,
                "run_id": state.get("run_id", "unknown"),
                "revision_id": state.get("revision_id", "unknown"),
                "title": f"第{chapter_id}章",
                "scenes": scenes_out,
                "word_count": _word_count(full_text),
            },
            generator=_generator(state),
        )
        return draft


class TemplatePatcher:
    """模板型最小补丁器：优先修复 blocker，并尽量只改动必要片段。"""

    def apply(
        self,
        state: State,
        draft: Dict[str, Any],
        issues: List[Issue],
        *,
        context_pack: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        patched = {**draft}
        scenes = [dict(s) for s in (patched.get("scenes") or [])]

        blocker_issues = [i for i in issues if i.get("severity") == "blocker"]
        if not blocker_issues:
            return patched

        # 最小策略：在第一场景末尾追加“修订说明”并移除常见占位符标记
        note_lines = ["修订说明："]
        for i in blocker_issues:
            summary = i.get("summary", "").strip()
            fix = i.get("fix_instructions", "").strip()
            if summary or fix:
                note_lines.append(f"- {summary}（修复：{fix}）")
        note = "\n".join(note_lines).strip()

        if scenes:
            content = scenes[0].get("content", "")
            content = (
                content.replace("由LLM生成", "已补全")
                .replace("[", "（")
                .replace("]", "）")
            )
            if note:
                content = content.rstrip() + "\n\n" + note
            scenes[0]["content"] = content

        patched["scenes"] = scenes
        patched["word_count"] = _word_count(
            "\n".join([s.get("content", "") for s in scenes])
        )
        return patched
