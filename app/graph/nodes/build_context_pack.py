"""构建 context_pack 节点（B3）。"""

from __future__ import annotations

from typing import Any, Dict, List

from app.config import Config
from app.retrieval.index import RetrievalHit, search
from app.schemas.base import add_metadata
from app.schemas.validation import validate_context_pack
from app.storage.artifact_store import ArtifactStore


def _generator(run_id: str, revision_id: str) -> str:
    return f"novel-gen-v2/{run_id}/{revision_id}"


def _outline_snippet(outline: Dict[str, Any], chapter_id: int) -> Dict[str, Any]:
    chapters = outline.get("chapters", []) or []
    if len(chapters) >= chapter_id:
        return chapters[chapter_id - 1]
    return {}


def _recent_memory(
    memory: Dict[str, Any], chapter_id: int, n: int = 3
) -> List[Dict[str, Any]]:
    chapters = memory.get("chapters", {}) or {}
    items: List[Dict[str, Any]] = []
    for cid in range(max(1, chapter_id - n), chapter_id):
        entry = chapters.get(str(cid))
        if entry:
            items.append(entry)
    return items


def _open_blockers(
    reports: Dict[str, Any], *, qa_blocker_max: int
) -> List[Dict[str, Any]]:
    chapters = reports.get("chapters", {}) or {}
    blockers: List[Dict[str, Any]] = []
    for _cid, entry in chapters.items():
        try:
            if int(entry.get("blocker_count", 0)) > int(qa_blocker_max):
                blockers.append(entry)
        except Exception:
            continue
    return blockers


def _hit_to_source(hit: RetrievalHit) -> Dict[str, Any]:
    return {
        "source_id": hit.source_id,
        "source_path": hit.source_path,
        "doc_type": hit.doc_type,
        "chapter_id": hit.chapter_id,
        "score": hit.score,
        "excerpt": hit.excerpt,
    }


def build_context_pack(state: Dict[str, Any], app_config: Config) -> Dict[str, Any]:
    """组装 context_pack，并写入 state['context_pack']。"""
    chapter_id = int(state.get("current_chapter", 1))
    run_id = str(state.get("run_id", "unknown"))
    revision_id = str(state.get("revision_id", "unknown"))
    prompt = str(
        state.get("prompt") or state.get("requirements", {}).get("prompt") or ""
    ).strip()

    store = ArtifactStore(app_config.project_root)
    memory = store.read_chapter_memory()
    reports = store.read_consistency_reports()

    outline = state.get("outline", {}) or {}
    world = state.get("world", {}) or {}
    characters = state.get("characters", {}) or {}
    theme_conflict = state.get("theme_conflict", {}) or {}

    required = {
        "outline_current": _outline_snippet(outline, chapter_id),
        "bible_summary": {
            "world_name": world.get("name", ""),
            "protagonist": (characters.get("protagonist") or {}).get("name", ""),
            "theme": theme_conflict.get("theme", ""),
        },
        "recent_memory": _recent_memory(memory, chapter_id, n=3),
        "open_blocker_reports": _open_blockers(
            reports, qa_blocker_max=int(state.get("qa_blocker_max", 0))
        ),
    }

    hits = search(
        app_config.project_root,
        app_config.retrieval_db,
        query=prompt,
        top_k=8,
    )
    retrieved = [_hit_to_source(h) for h in hits]

    pack = add_metadata(
        {
            "project_name": str(state.get("project_name", app_config.project_name)),
            "chapter_id": chapter_id,
            "query": prompt,
            "required": required,
            "retrieved": retrieved,
        },
        generator=_generator(run_id, revision_id),
    )

    result = validate_context_pack(pack)
    if not result:
        raise ValueError(f"context_pack validation failed: {result.error_messages}")

    return {"context_pack": result.data or pack}
