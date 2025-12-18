"""检索与 context pack（B3）测试。"""

import tempfile
from pathlib import Path

from app.bootstrap.bootstrap import ensure_background_assets
from app.config import Config
from app.graph.nodes.build_context_pack import build_context_pack
from app.retrieval.documents import iter_project_chunks
from app.retrieval.index import rebuild_index, search
from app.storage.artifact_store import ArtifactStore


def test_retrieval_hits_project_assets_without_vectors():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "p"
        config = Config(project_name="p", project_root=project_root)
        store = ArtifactStore(project_root)
        store.init_project("p", "author")

        ensure_background_assets(
            store=store,
            prompt="完全架空的修仙世界,整个世界分为3界(人界,灵界,魔界)",
            num_chapters=1,
            generator="test",
        )

        rebuild_index(
            config.retrieval_db, chunks=list(iter_project_chunks(project_root))
        )
        # rebuild_index 可能在某些 SQLite 环境下因为缺少 FTS5 而返回 False；不强制要求 True

        hits = search(project_root, config.retrieval_db, query="林澈", top_k=5)
        assert hits  # 至少命中一条（FTS 或 fallback scan）

        # 回归：带逗号/括号的 query 不应触发 FTS5 语法错误
        hits2 = search(
            project_root,
            config.retrieval_db,
            query="完全架空的修仙世界,整个世界分为3界(人界,灵界,魔界)",
            top_k=5,
        )
        assert hits2 is not None


def test_build_context_pack_is_valid_schema():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "p"
        config = Config(project_name="p", project_root=project_root)
        store = ArtifactStore(project_root)
        store.init_project("p", "author")

        ensure_background_assets(
            store=store,
            prompt="修仙世界",
            num_chapters=1,
            generator="test",
        )

        state = {
            "project_name": "p",
            "current_chapter": 1,
            "run_id": "run_x",
            "revision_id": "run_x_ch001_r0",
            "prompt": "修仙世界",
            "outline": store.read_outline(),
            "world": store.read_world(),
            "characters": store.read_characters(),
            "theme_conflict": store.read_theme_conflict(),
            "qa_blocker_max": 0,
        }

        updates = build_context_pack(state, config)
        pack = updates["context_pack"]
        assert pack["project_name"] == "p"
        assert pack["chapter_id"] == 1
        assert "required" in pack
        assert "retrieved" in pack
