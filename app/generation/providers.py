"""生成链路的 Provider 接口（便于测试与替换实现）。

本项目的工作流节点（plan/write/patch）不直接依赖外部 LLM，
而是通过 Provider 接口注入依赖：
- 真实环境：可接入 OpenAI/其它模型（后续扩展）
- 测试环境：使用确定性的 Fake* 组件，保证可复现
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from app.graph.state import Issue, State


class Planner(Protocol):
    """章节规划器：把 outline + 上下文生成 chapter_plan。"""

    def plan(
        self, state: State, *, context_pack: Dict[str, Any] | None = None
    ) -> Dict[str, Any]: ...


class Writer(Protocol):
    """章节写作者：把 chapter_plan + 上下文生成 chapter_draft。"""

    def write(
        self,
        state: State,
        plan: Dict[str, Any],
        *,
        context_pack: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]: ...


class Patcher(Protocol):
    """最小补丁器：根据 issues.fix_instructions 对 draft 做最小改动。"""

    def apply(
        self,
        state: State,
        draft: Dict[str, Any],
        issues: List[Issue],
        *,
        context_pack: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class GenerationProviders:
    planner: Planner
    writer: Writer
    patcher: Patcher
