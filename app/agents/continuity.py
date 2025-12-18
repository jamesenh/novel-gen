"""连续性插件 stub - 检查一致性问题。

这是一个 stub 实现。在生产环境中，会使用 LLM 检测世界观/角色/时间线/知情链不一致问题。
"""

from typing import Any, Dict, List

from app.agents.base import AuditPlugin
from app.graph.state import State


class ContinuityPlugin(AuditPlugin):
    """连续性检查插件。

    检查项:
    - 世界规则违规
    - 角色一致性
    - 时间线冲突
    - 知情链违规
    - 伏笔线程问题

    这是一个 stub - 实际实现会调用 LLM。
    """

    name = "continuity"
    description = "Checks for narrative consistency issues"

    def analyze(
        self,
        state: State,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """分析章节的一致性问题。

        Args:
            state: 包含 chapter_draft 的当前工作流状态。
            context: world、characters、outline 等上下文。

        Returns:
            问题列表，包含 severity、category、summary、evidence、fix_instructions。
        """
        # Stub implementation - would call LLM in production
        issues: List[Dict[str, Any]] = []

        draft = state.get("chapter_draft", {})
        if not draft:
            return issues

        # Example: Check if chapter has content
        scenes = draft.get("scenes", [])
        if not scenes:
            issues.append(
                {
                    "id": f"I-{state.get('current_chapter', 1):03d}-001",
                    "severity": "blocker",
                    "category": "world_rule",
                    "summary": "章节缺少场景内容",
                    "evidence": {
                        "chapter_id": state.get("current_chapter", 1),
                        "missing": "scenes",
                    },
                    "fix_instructions": "添加至少一个场景到章节中",
                }
            )

        # Example: Check placeholder / zero-word drafts (用于驱动修订循环收敛)
        if scenes:
            any_placeholder = any(
                ("由LLM生成" in (s.get("content", "") or ""))
                or ("[第" in (s.get("content", "") or ""))
                for s in scenes
                if isinstance(s, dict)
            )
            word_count = draft.get("word_count")
            if any_placeholder or word_count == 0:
                issues.append(
                    {
                        "id": f"I-{state.get('current_chapter', 1):03d}-002",
                        "severity": "blocker",
                        "category": "pov_style",
                        "summary": "章节正文仍包含占位内容或字数为 0",
                        "evidence": {
                            "chapter_id": state.get("current_chapter", 1),
                            "word_count": word_count,
                        },
                        "fix_instructions": "生成真实正文，移除占位符，并补齐 word_count",
                    }
                )

        # In production, this would:
        # 1. Extract facts from chapter draft
        # 2. Compare against world/character/timeline state
        # 3. Check knowledge chain (who knows what when)
        # 4. Verify thread/foreshadowing progression
        # 5. Return structured issues with evidence and fix hints

        return issues
