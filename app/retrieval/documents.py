"""将项目资产规范化为可检索 documents/chunks。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class DocumentChunk:
    """一个可检索的文本片段（最小单位）。"""

    source_id: str
    source_path: str
    doc_type: str
    chapter_id: Optional[int]
    text: str


def _read_json_safe(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _pretty_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def iter_project_chunks(project_root: Path) -> Iterable[DocumentChunk]:
    """遍历项目资产并产出 chunks（稳定 source_id）。"""
    project_root = Path(project_root)
    chapters_dir = project_root / "chapters"

    def emit(
        path: Path, doc_type: str, chapter_id: Optional[int] = None
    ) -> List[DocumentChunk]:
        rel = str(path.relative_to(project_root))
        data = _read_json_safe(path)
        if data is None:
            return []
        text = _pretty_json(data)
        source_id = f"file:{rel}"
        return [
            DocumentChunk(
                source_id=source_id,
                source_path=rel,
                doc_type=doc_type,
                chapter_id=chapter_id,
                text=text,
            )
        ]

    # bible / outline
    for path, doc_type in [
        (project_root / "world.json", "world"),
        (project_root / "characters.json", "characters"),
        (project_root / "theme_conflict.json", "theme_conflict"),
        (project_root / "outline.json", "outline"),
        (project_root / "chapter_memory.json", "chapter_memory"),
        (project_root / "consistency_reports.json", "consistency_reports"),
        (project_root / "settings.json", "settings"),
    ]:
        yield from emit(path, doc_type)

    # chapters
    if chapters_dir.exists():
        for p in sorted(chapters_dir.glob("chapter_*.json")):
            # chapter_001.json or chapter_001_plan.json
            name = p.name
            ch = None
            if name.startswith("chapter_") and len(name) >= len("chapter_001"):
                maybe = name.split("_", 1)[1].split(".", 1)[0]
                maybe_num = maybe.replace("plan", "").replace("_plan", "")
                try:
                    ch = int(maybe_num[:3])
                except Exception:
                    ch = None

            if name.endswith("_plan.json"):
                yield from emit(p, "chapter_plan", chapter_id=ch)
            else:
                yield from emit(p, "chapter_content", chapter_id=ch)
