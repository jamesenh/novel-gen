"""应用补丁节点 - 基于审计问题执行最小修订。"""

from datetime import datetime
from typing import Any, Dict

from app.generation.providers import Patcher
from app.graph.state import State


def apply_patch(state: State, patcher: Patcher) -> Dict[str, Any]:
    """应用最小补丁修复 blocker 问题。

    从 state 读取:
        - chapter_draft
        - audit_result

    写入 state:
        - chapter_draft (已更新)
        - revision_round (已递增)
        - revision_id (已更新)

    Args:
        state: 当前工作流状态。

    Returns:
        包含已修补 chapter_draft 的状态更新。
    """
    audit_result = state.get("audit_result", {})
    draft = state.get("chapter_draft", {})
    revision_round = state.get("revision_round", 0)
    run_id = state.get("run_id", "unknown")
    chapter_id = state.get("current_chapter", 1)

    blockers = [
        i for i in audit_result.get("issues", []) if i.get("severity") == "blocker"
    ]

    if not blockers:
        return {}

    new_revision_round = revision_round + 1
    new_revision_id = f"{run_id}_ch{chapter_id:03d}_r{new_revision_round}"

    # 先更新 revision 标识，再让 patcher 基于新 revision_id 写入 draft 元数据
    next_state = {
        **state,
        "revision_round": new_revision_round,
        "revision_id": new_revision_id,
    }
    patched_draft = patcher.apply(
        next_state,
        draft,
        blockers,
        context_pack=state.get("context_pack"),
    )
    patched_draft["run_id"] = run_id
    patched_draft["revision_id"] = new_revision_id
    patched_draft["generated_at"] = datetime.now().isoformat()
    patched_draft["generator"] = f"novel-gen-v2/{run_id}/{new_revision_id}"

    return {
        "chapter_draft": patched_draft,
        "revision_round": new_revision_round,
        "revision_id": new_revision_id,
    }
