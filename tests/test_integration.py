"""端到端集成测试。

测试完整工作流运行后的资产契约。
"""

import json
import tempfile
from pathlib import Path

from app.config import Config
from app.graph.builder import build_graph
from app.graph.run_config import build_thread_config
from app.graph.state import create_initial_state
from app.storage.artifact_store import ArtifactStore


class TestArtifactContract:
    """测试资产契约：运行工作流后应生成正确的文件。"""

    def test_single_chapter_creates_all_artifacts(self):
        """运行单章工作流后应创建所有必要的资产文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "test_project"

            # 创建配置
            config = Config(
                project_name="test_project",
                project_root=project_root,
                author="Test Author",
                num_chapters=1,
                max_revision_rounds=3,
            )

            # 初始化项目
            store = ArtifactStore(project_root)
            store.init_project(
                project_name=config.project_name,
                author=config.author,
            )

            # 创建初始状态并运行图
            state = create_initial_state(
                project_name=config.project_name,
                num_chapters=1,
                prompt="测试提示词",
                max_revision_rounds=config.max_revision_rounds,
            )

            graph = build_graph(config)
            final_state = graph.invoke(state, build_thread_config(config.project_name))

            # 验证最终状态
            assert final_state.get("completed") is True or final_state.get(
                "needs_human_review"
            )

            # 验证所有必要文件存在
            chapters_dir = project_root / "chapters"
            assert (chapters_dir / "chapter_001_plan.json").exists()
            assert (chapters_dir / "chapter_001.json").exists()
            assert (project_root / "consistency_reports.json").exists()
            assert (project_root / "chapter_memory.json").exists()
            assert (project_root / "settings.json").exists()

    def test_artifacts_contain_required_metadata(self):
        """持久化的 JSON 应包含必要的元数据字段。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "test_project"

            config = Config(
                project_name="test_project",
                project_root=project_root,
                author="Test Author",
                num_chapters=1,
                max_revision_rounds=3,
            )

            store = ArtifactStore(project_root)
            store.init_project(
                project_name=config.project_name,
                author=config.author,
            )

            state = create_initial_state(
                project_name=config.project_name,
                num_chapters=1,
                prompt="测试提示词",
                max_revision_rounds=config.max_revision_rounds,
            )

            graph = build_graph(config)
            graph.invoke(state, build_thread_config(config.project_name))

            # 检查章节计划的元数据
            plan_path = project_root / "chapters" / "chapter_001_plan.json"
            with open(plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)

            assert "schema_version" in plan
            assert "generated_at" in plan
            assert "generator" in plan
            assert "run_id" in plan
            assert "revision_id" in plan

            # 检查章节内容的元数据
            content_path = project_root / "chapters" / "chapter_001.json"
            with open(content_path, "r", encoding="utf-8") as f:
                content = json.load(f)

            assert "schema_version" in content
            assert "generated_at" in content
            assert "generator" in content
            assert "run_id" in content
            assert "revision_id" in content

            # 检查一致性报告的元数据
            reports_path = project_root / "consistency_reports.json"
            with open(reports_path, "r", encoding="utf-8") as f:
                reports = json.load(f)

            assert "schema_version" in reports
            assert "generated_at" in reports
            assert "chapters" in reports

            # 检查章节记忆的元数据
            memory_path = project_root / "chapter_memory.json"
            with open(memory_path, "r", encoding="utf-8") as f:
                memory = json.load(f)

            assert "schema_version" in memory
            assert "generated_at" in memory
            assert "chapters" in memory

    def test_multi_chapter_workflow(self):
        """多章工作流应正确推进并创建所有章节文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "test_project"

            config = Config(
                project_name="test_project",
                project_root=project_root,
                author="Test Author",
                num_chapters=2,
                max_revision_rounds=3,
            )

            store = ArtifactStore(project_root)
            store.init_project(
                project_name=config.project_name,
                author=config.author,
            )

            state = create_initial_state(
                project_name=config.project_name,
                num_chapters=2,
                prompt="测试多章",
                max_revision_rounds=config.max_revision_rounds,
            )

            graph = build_graph(config)
            final_state = graph.invoke(state, build_thread_config(config.project_name))

            # 验证完成状态
            assert final_state.get("completed") is True or final_state.get(
                "needs_human_review"
            )

            # 验证两章的文件都存在
            chapters_dir = project_root / "chapters"
            assert (chapters_dir / "chapter_001_plan.json").exists()
            assert (chapters_dir / "chapter_001.json").exists()
            assert (chapters_dir / "chapter_002_plan.json").exists()
            assert (chapters_dir / "chapter_002.json").exists()

            # 验证 memory 和 reports 包含两章的数据
            with open(project_root / "chapter_memory.json", "r", encoding="utf-8") as f:
                memory = json.load(f)
            assert "1" in memory["chapters"]
            assert "2" in memory["chapters"]

            with open(
                project_root / "consistency_reports.json", "r", encoding="utf-8"
            ) as f:
                reports = json.load(f)
            assert "1" in reports["chapters"]
            assert "2" in reports["chapters"]
