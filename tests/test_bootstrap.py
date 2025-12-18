"""run bootstrap（背景资产生成/加载）测试。"""

import json
import tempfile
from pathlib import Path

import pytest

from app.bootstrap.bootstrap import ensure_background_assets
from app.storage.artifact_store import ArtifactStore


def test_bootstrap_generates_missing_assets_from_prompt():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "p"
        store = ArtifactStore(project_root)
        store.init_project("p", "author")

        result = ensure_background_assets(
            store=store,
            prompt="完全架空的修仙世界,整个世界分为3界(人界,灵界,魔界)",
            num_chapters=2,
            generator="test-gen",
            allow_overwrite=False,
        )

        assert result.world
        assert result.characters
        assert result.theme_conflict
        assert result.outline
        assert (project_root / "world.json").exists()
        assert (project_root / "characters.json").exists()
        assert (project_root / "theme_conflict.json").exists()
        assert (project_root / "outline.json").exists()

        with open(project_root / "outline.json", "r", encoding="utf-8") as f:
            outline = json.load(f)
        assert outline["num_chapters"] == 2
        assert len(outline["chapters"]) == 2


def test_bootstrap_does_not_overwrite_existing_assets_by_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "p"
        store = ArtifactStore(project_root)
        store.init_project("p", "author")

        ensure_background_assets(
            store=store,
            prompt="修仙世界",
            num_chapters=1,
            generator="gen-1",
            allow_overwrite=False,
        )

        with open(project_root / "world.json", "r", encoding="utf-8") as f:
            world_before = json.load(f)

        ensure_background_assets(
            store=store,
            prompt="完全不同的提示词（不应覆写）",
            num_chapters=3,
            generator="gen-2",
            allow_overwrite=False,
        )

        with open(project_root / "world.json", "r", encoding="utf-8") as f:
            world_after = json.load(f)

        assert world_after["generated_at"] == world_before["generated_at"]
        assert world_after["generator"] == world_before["generator"]


def test_bootstrap_requires_prompt_when_assets_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "p"
        store = ArtifactStore(project_root)
        store.init_project("p", "author")

        # world 等文件都缺失，但未提供 prompt
        with pytest.raises(ValueError, match="未提供 --prompt"):
            ensure_background_assets(
                store=store,
                prompt="",
                num_chapters=1,
                generator="gen",
                allow_overwrite=False,
            )
