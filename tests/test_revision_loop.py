"""修订循环收敛测试（B2 验收用）。"""

import tempfile
from pathlib import Path

from app.config import Config
from app.generation.fakes import FakePatcher, FakePlanner, FakeWriter
from app.generation.providers import GenerationProviders
from app.graph.builder import build_graph
from app.graph.run_config import build_thread_config
from app.graph.state import create_initial_state
from app.storage.artifact_store import ArtifactStore


def test_revision_loop_converges_under_fake_providers():
    """在 FakeWriter 输出占位稿的情况下，应触发修订并最终收敛到 blocker=0。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "p"
        config = Config(
            project_name="p", project_root=project_root, max_revision_rounds=3
        )

        store = ArtifactStore(project_root)
        store.init_project(project_name="p", author="author")

        providers = GenerationProviders(
            planner=FakePlanner(),
            writer=FakeWriter(placeholder=True),
            patcher=FakePatcher(),
        )
        graph = build_graph(config, providers=providers)

        state = create_initial_state(
            project_name="p", num_chapters=1, prompt="测试", max_revision_rounds=3
        )
        final_state = graph.invoke(state, build_thread_config("p"))

        assert final_state.get("needs_human_review") is not True
        assert (project_root / "chapters" / "chapter_001.json").exists()
        assert final_state.get("revision_round", 0) >= 1
