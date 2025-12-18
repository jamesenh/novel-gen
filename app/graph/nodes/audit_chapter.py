"""章节审计节点 - 通过插件运行一致性检查。

此节点调用已注册的审计插件，并将它们的结果聚合为单个章节审计结果。
"""

from typing import Any, Dict, List

from app.agents.registry import get_audit_plugins
from app.graph.state import AuditResult, State
from app.schemas.validation import validate_issues_list


def audit_chapter(state: State) -> Dict[str, Any]:
    """对当前章节草稿运行审计插件。

    从 state 读取:
        - current_chapter
        - chapter_draft
        - world, characters, outline

    写入 state:
        - audit_result

    Args:
        state: 当前工作流状态。

    Returns:
        包含 audit_result 的状态更新。
    """
    chapter_id = state.get("current_chapter", 1)
    # chapter_draft is passed to plugins via context

    # Build context pack for plugins
    context = {
        "world": state.get("world", {}),
        "characters": state.get("characters", {}),
        "outline": state.get("outline", {}),
        "theme_conflict": state.get("theme_conflict", {}),
        "chapter_plan": state.get("chapter_plan", {}),
        "context_pack": state.get("context_pack", {}),
    }

    # Collect issues from all audit plugins
    all_issues: List[Dict[str, Any]] = []
    plugins = get_audit_plugins()

    for plugin in plugins:
        issues = plugin.analyze(state, context)
        issues_result = validate_issues_list(issues)
        if not issues_result:
            raise ValueError(
                f"Plugin '{plugin.name}' returned invalid issues: "
                f"{issues_result.error_messages}"
            )
        all_issues.extend(issues)

    # Count issues by severity
    blocker_count = sum(1 for i in all_issues if i.get("severity") == "blocker")
    major_count = sum(1 for i in all_issues if i.get("severity") == "major")
    minor_count = sum(1 for i in all_issues if i.get("severity") == "minor")
    qa_major_max = state.get("qa_major_max", 3)
    major_over_threshold = major_count > qa_major_max

    result: AuditResult = {
        "chapter_id": chapter_id,
        "issues": all_issues,
        "blocker_count": blocker_count,
        "major_count": major_count,
        "minor_count": minor_count,
        "updates": {},  # Plugins may suggest updates
        "major_over_threshold": major_over_threshold,
        "qa_major_max": qa_major_max,
    }

    return {"audit_result": result}
