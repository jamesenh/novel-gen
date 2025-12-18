"""存储资产节点 - 将章节资产持久化到磁盘。

此节点在写入前对资产进行 schema 校验，并确保内容、记忆和报告的同步写入。
"""

from typing import Any, Dict

from app.config import Config
from app.graph.state import State
from app.schemas.validation import validate_chapter_content, validate_chapter_plan
from app.storage.artifact_store import ArtifactStore


def store_artifacts(state: State, app_config: Config) -> Dict[str, Any]:
    """将章节资产持久化到项目目录。

    从 state 读取:
        - project_name
        - current_chapter
        - chapter_plan
        - chapter_draft
        - audit_result

    写入磁盘:
        - chapters/chapter_XXX_plan.json
        - chapters/chapter_XXX.json
        - consistency_reports.json (已更新)
        - chapter_memory.json (已更新)

    Args:
        state: 当前工作流状态。
        config: 应用配置。

    Returns:
        空的状态更新（资产已持久化到磁盘）。

    Raises:
        ValueError: 如果校验失败。
    """
    chapter_id = state.get("current_chapter", 1)
    plan = state.get("chapter_plan", {})
    draft = state.get("chapter_draft", {})
    audit = state.get("audit_result", {})

    store = ArtifactStore(app_config.project_root)

    # Validate artifacts before writing
    plan_result = validate_chapter_plan(plan)
    if not plan_result:
        raise ValueError(
            f"Chapter plan validation failed: {plan_result.error_messages}"
        )

    draft_result = validate_chapter_content(draft)
    if not draft_result:
        raise ValueError(
            f"Chapter content validation failed: {draft_result.error_messages}"
        )

    # Write artifacts atomically (as a bundle)
    store.write_chapter_bundle(
        chapter_id=chapter_id,
        plan=plan,
        content=draft,
        audit=audit,
    )

    return {}
