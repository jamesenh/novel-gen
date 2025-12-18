"""断点续跑（continue）相关测试。"""

import json
import tempfile
from pathlib import Path

from app.config import Config
from app.graph.builder import build_graph
from app.graph.run_config import build_thread_config
from app.graph.state import create_initial_state
from app.schemas.base import add_metadata
from app.storage.artifact_store import ArtifactStore


def test_interrupt_then_continue_completes_and_writes_artifacts():
    """中断后继续应能完成工作流，并写出完整的资产 bundle。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "test_project"
        config = Config(project_name="test_project", project_root=project_root)

        store = ArtifactStore(project_root)
        store.init_project(project_name=config.project_name, author=config.author)

        graph = build_graph(config)
        thread_cfg = build_thread_config(config.project_name)

        state = create_initial_state(
            project_name=config.project_name,
            num_chapters=1,
            prompt="测试提示词",
            max_revision_rounds=config.max_revision_rounds,
        )

        # 在写完草稿后中断（此时尚未写盘章节资产）
        _partial = graph.invoke(state, thread_cfg, interrupt_after=["write_chapter"])

        chapters_dir = project_root / "chapters"
        assert not (chapters_dir / "chapter_001.json").exists()
        assert not (chapters_dir / "chapter_001_plan.json").exists()

        final_state = graph.invoke(None, thread_cfg)

        assert final_state.get("completed") is True or final_state.get(
            "needs_human_review"
        )
        assert (chapters_dir / "chapter_001_plan.json").exists()
        assert (chapters_dir / "chapter_001.json").exists()
        assert (project_root / "consistency_reports.json").exists()
        assert (project_root / "chapter_memory.json").exists()


def test_store_bundle_idempotent_by_revision_id():
    """同一 revision_id 的 bundle 写入应是幂等的（不会覆写既有文件）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "test_project"
        store = ArtifactStore(project_root)
        store.init_project("test_project", "author")

        plan_v1 = add_metadata(
            {"chapter_id": 1, "goal": "版本1", "run_id": "run", "revision_id": "rev1"}
        )
        content_v1 = add_metadata(
            {
                "chapter_id": 1,
                "title": "第一章v1",
                "scenes": [{"scene_id": "1_1", "content": "正文"}],
                "word_count": 2,
                "run_id": "run",
                "revision_id": "rev1",
            }
        )
        audit = {"issues": [], "blocker_count": 0, "major_count": 0, "minor_count": 0}

        store.write_chapter_bundle(1, plan_v1, content_v1, audit)

        # 第二次写入同一 revision_id，但内容不同；应被忽略
        plan_v2 = add_metadata(
            {"chapter_id": 1, "goal": "版本2", "run_id": "run", "revision_id": "rev1"}
        )
        content_v2 = add_metadata(
            {
                "chapter_id": 1,
                "title": "第一章v2",
                "scenes": [{"scene_id": "1_1", "content": "不同正文"}],
                "word_count": 4,
                "run_id": "run",
                "revision_id": "rev1",
            }
        )
        store.write_chapter_bundle(1, plan_v2, content_v2, audit)

        plan_path = project_root / "chapters" / "chapter_001_plan.json"
        content_path = project_root / "chapters" / "chapter_001.json"
        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)
        with open(content_path, "r", encoding="utf-8") as f:
            content = json.load(f)

        assert plan["goal"] == "版本1"
        assert content["title"] == "第一章v1"
