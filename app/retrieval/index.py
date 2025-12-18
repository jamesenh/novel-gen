"""SQLite FTS5 检索索引（无向量库）。"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from re import sub
from typing import Iterable, List, Optional

from app.retrieval.documents import DocumentChunk, iter_project_chunks


@dataclass(frozen=True)
class RetrievalHit:
    source_id: str
    source_path: str
    doc_type: str
    chapter_id: Optional[int]
    score: float
    excerpt: str


def _sanitize_fts_query(query: str) -> str:
    """把用户输入清洗为更安全的 FTS5 MATCH 查询。

    目的：
    - 避免 prompt/question 中出现逗号、括号等导致 FTS5 query parser 报错
    - 保持一个“尽量不惊讶”的最小策略：把非字母数字/中文的符号替换为空格
    """
    q = (query or "").strip()
    if not q:
        return ""
    # 允许：英文/数字/下划线/中文；其余全部替换为空格
    q = sub(r"[^\w\u4e00-\u9fff]+", " ", q)
    q = sub(r"\s+", " ", q).strip()
    return q


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_fts(conn: sqlite3.Connection) -> bool:
    """确保 FTS 表存在；若 SQLite 不支持 FTS5 则返回 False。"""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(
              text,
              source_id UNINDEXED,
              source_path UNINDEXED,
              doc_type UNINDEXED,
              chapter_id UNINDEXED,
              tokenize = 'unicode61'
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.OperationalError:
        return False


def rebuild_index(db_path: Path, *, chunks: Iterable[DocumentChunk]) -> bool:
    """重建检索索引（小规模项目可接受全量重建）。"""
    with closing(_connect(db_path)) as conn:
        if not _ensure_fts(conn):
            return False
        cur = conn.cursor()
        cur.execute("DELETE FROM chunks_fts")
        cur.executemany(
            """
            INSERT INTO chunks_fts(text, source_id, source_path, doc_type, chapter_id)
            VALUES (?,?,?,?,?)
            """,
            [
                (c.text, c.source_id, c.source_path, c.doc_type, c.chapter_id)
                for c in chunks
            ],
        )
        conn.commit()
        return True


def ensure_index(project_root: Path, db_path: Path) -> bool:
    """确保索引可用：若 DB 不存在则重建。"""
    if not db_path.exists():
        return rebuild_index(db_path, chunks=iter_project_chunks(project_root))
    # MVP：先不做增量更新；后续可依据文件 mtime/hash 做增量
    return True


def search(
    project_root: Path,
    db_path: Path,
    *,
    query: str,
    top_k: int = 8,
    doc_types: Optional[List[str]] = None,
    chapter_min: Optional[int] = None,
    chapter_max: Optional[int] = None,
) -> List[RetrievalHit]:
    """关键词检索（优先 FTS5；不可用则回退到简易扫描）。"""
    query = (query or "").strip()
    if not query:
        return []

    fts_query = _sanitize_fts_query(query)

    if ensure_index(project_root, db_path):
        with closing(_connect(db_path)) as conn:
            if not _ensure_fts(conn):
                return _fallback_scan(
                    project_root,
                    query=query,
                    top_k=top_k,
                    doc_types=doc_types,
                    chapter_min=chapter_min,
                    chapter_max=chapter_max,
                )

            where = "chunks_fts MATCH ?"
            params: list = [fts_query or query]
            if doc_types:
                placeholders = ",".join(["?"] * len(doc_types))
                where += f" AND doc_type IN ({placeholders})"
                params.extend(doc_types)
            if chapter_min is not None:
                where += " AND (chapter_id IS NULL OR chapter_id >= ?)"
                params.append(int(chapter_min))
            if chapter_max is not None:
                where += " AND (chapter_id IS NULL OR chapter_id <= ?)"
                params.append(int(chapter_max))

            try:
                rows = conn.execute(
                    f"""
                    SELECT
                      source_id,
                      source_path,
                      doc_type,
                      chapter_id,
                      -bm25(chunks_fts) AS score,
                      snippet(chunks_fts, 0, '', '', '...', 20) AS excerpt
                    FROM chunks_fts
                    WHERE {where}
                    ORDER BY score DESC
                    LIMIT ?
                    """,
                    (*params, int(top_k)),
                ).fetchall()
            except sqlite3.OperationalError:
                # 若 FTS5 query 解析失败（例如包含特殊符号），回退到无索引扫描
                return _fallback_scan(
                    project_root,
                    query=query,
                    top_k=top_k,
                    doc_types=doc_types,
                    chapter_min=chapter_min,
                    chapter_max=chapter_max,
                )

            return [
                RetrievalHit(
                    source_id=r["source_id"],
                    source_path=r["source_path"],
                    doc_type=r["doc_type"],
                    chapter_id=r["chapter_id"],
                    score=float(r["score"]),
                    excerpt=r["excerpt"] or "",
                )
                for r in rows
            ]

    return _fallback_scan(
        project_root,
        query=query,
        top_k=top_k,
        doc_types=doc_types,
        chapter_min=chapter_min,
        chapter_max=chapter_max,
    )


def _fallback_scan(
    project_root: Path,
    *,
    query: str,
    top_k: int,
    doc_types: Optional[List[str]],
    chapter_min: Optional[int],
    chapter_max: Optional[int],
) -> List[RetrievalHit]:
    """无索引回退：简单子串扫描（小规模项目可用）。"""
    hits: List[RetrievalHit] = []
    q = query.strip()
    for c in iter_project_chunks(project_root):
        if doc_types and c.doc_type not in doc_types:
            continue
        if c.chapter_id is not None:
            if chapter_min is not None and c.chapter_id < chapter_min:
                continue
            if chapter_max is not None and c.chapter_id > chapter_max:
                continue

        idx = c.text.find(q)
        if idx < 0:
            continue
        start = max(0, idx - 40)
        end = min(len(c.text), idx + 40)
        excerpt = c.text[start:end].replace("\n", " ")
        hits.append(
            RetrievalHit(
                source_id=c.source_id,
                source_path=c.source_path,
                doc_type=c.doc_type,
                chapter_id=c.chapter_id,
                score=1.0,
                excerpt=excerpt,
            )
        )
        if len(hits) >= top_k:
            break
    return hits
