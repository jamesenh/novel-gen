"""资产存储测试。

测试原子写入和失败回滚行为。
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.schemas.base import add_metadata
from app.storage.artifact_store import ArtifactStore, AtomicWriteError


class TestAtomicWrite:
    """测试原子写入行为。"""

    def test_atomic_write_success(self):
        """成功的原子写入应创建所有文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "test_project"
            store = ArtifactStore(project_root)
            store.init_project("test_project", "author")

            plan = add_metadata({"chapter_id": 1, "goal": "测试目标"})
            content = add_metadata({"chapter_id": 1, "title": "第一章", "scenes": []})
            audit = {
                "issues": [],
                "blocker_count": 0,
                "major_count": 0,
                "minor_count": 0,
            }

            store.write_chapter_bundle(1, plan, content, audit)

            # 验证所有文件存在
            assert (project_root / "chapters" / "chapter_001_plan.json").exists()
            assert (project_root / "chapters" / "chapter_001.json").exists()
            assert (project_root / "consistency_reports.json").exists()
            assert (project_root / "chapter_memory.json").exists()

    def test_atomic_write_rollback_on_failure(self):
        """写入失败时应回滚，不留下部分文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "test_project"
            store = ArtifactStore(project_root)
            store.init_project("test_project", "author")

            plan = add_metadata({"chapter_id": 1, "goal": "测试目标"})
            content = add_metadata({"chapter_id": 1, "title": "第一章", "scenes": []})
            audit = {
                "issues": [],
                "blocker_count": 0,
                "major_count": 0,
                "minor_count": 0,
            }

            # 记录写入前的文件状态
            chapters_dir = project_root / "chapters"
            plan_path = chapters_dir / "chapter_001_plan.json"
            content_path = chapters_dir / "chapter_001.json"
            reports_path = project_root / "consistency_reports.json"
            memory_path = project_root / "chapter_memory.json"

            # 模拟在某个阶段失败
            call_count = [0]
            original_replace = os.replace

            def failing_replace(src, dst):
                call_count[0] += 1
                # 仅在“临时文件 -> 目标文件”的阶段模拟失败；回滚使用 backup_* 不受影响
                if "file_" in str(src) and call_count[0] > 2:
                    raise OSError("模拟写入失败")
                return original_replace(src, dst)

            with patch("os.replace", side_effect=failing_replace):
                with pytest.raises(AtomicWriteError, match="原子写入失败"):
                    store.write_chapter_bundle(1, plan, content, audit)

            # 验证没有部分文件留下（或已回滚）
            assert not plan_path.exists()
            assert not content_path.exists()
            assert not reports_path.exists()
            assert not memory_path.exists()

    def test_atomic_write_preserves_existing_on_update(self):
        """更新现有章节时，失败应保留原始文件。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "test_project"
            store = ArtifactStore(project_root)
            store.init_project("test_project", "author")

            # 先写入第一版
            plan_v1 = add_metadata({"chapter_id": 1, "goal": "版本1"})
            content_v1 = add_metadata(
                {"chapter_id": 1, "title": "第一章v1", "scenes": []}
            )
            audit = {
                "issues": [],
                "blocker_count": 0,
                "major_count": 0,
                "minor_count": 0,
            }

            store.write_chapter_bundle(1, plan_v1, content_v1, audit)

            # 读取原始内容
            plan_path = project_root / "chapters" / "chapter_001_plan.json"
            with open(plan_path, "r", encoding="utf-8") as f:
                original_plan = json.load(f)
            assert original_plan["goal"] == "版本1"

            # 尝试写入第二版，但模拟失败
            plan_v2 = add_metadata({"chapter_id": 1, "goal": "版本2"})
            content_v2 = add_metadata(
                {"chapter_id": 1, "title": "第一章v2", "scenes": []}
            )

            call_count = [0]
            original_replace = os.replace

            def failing_replace(src, dst):
                call_count[0] += 1
                if "file_" in str(src) and call_count[0] > 2:
                    raise OSError("模拟写入失败")
                return original_replace(src, dst)

            with patch("os.replace", side_effect=failing_replace):
                with pytest.raises(AtomicWriteError):
                    store.write_chapter_bundle(1, plan_v2, content_v2, audit)

            # 验证原始文件被恢复或更新（取决于失败时机）
            assert plan_path.exists()
            with open(plan_path, "r", encoding="utf-8") as f:
                restored_plan = json.load(f)
            assert restored_plan["goal"] == "版本1"


class TestSchemaValidation:
    """测试新增的 schema 校验。"""

    def test_validate_consistency_reports(self):
        """校验 consistency_reports 结构。"""
        from app.schemas.validation import validate_consistency_reports

        valid_data = add_metadata(
            {
                "chapters": {
                    "1": {
                        "chapter_id": 1,
                        "issues": [],
                        "blocker_count": 0,
                        "major_count": 0,
                        "minor_count": 0,
                        "updated_at": "2024-01-01T00:00:00",
                    }
                },
                "updated_at": "2024-01-01T00:00:00",
            }
        )

        result = validate_consistency_reports(valid_data)
        assert result.valid

    def test_validate_chapter_memory(self):
        """校验 chapter_memory 结构。"""
        from app.schemas.validation import validate_chapter_memory

        valid_data = add_metadata(
            {
                "chapters": {
                    "1": {
                        "chapter_id": 1,
                        "title": "第一章",
                        "scene_count": 3,
                        "word_count": 1500,
                        "updated_at": "2024-01-01T00:00:00",
                    }
                },
                "updated_at": "2024-01-01T00:00:00",
            }
        )

        result = validate_chapter_memory(valid_data)
        assert result.valid

    def test_validate_issues_list_valid(self):
        """校验有效的问题列表。"""
        from app.schemas.validation import validate_issues_list

        valid_issues = [
            add_metadata(
                {
                    "id": "I-001",
                    "severity": "blocker",
                    "category": "timeline",
                    "summary": "时间矛盾",
                    "fix_instructions": "修正时间线",
                }
            )
        ]

        result = validate_issues_list(valid_issues)
        assert result.valid

    def test_validate_issues_list_invalid(self):
        """校验无效的问题列表应返回带路径的错误。"""
        from app.schemas.validation import validate_issues_list

        invalid_issues = [
            {"id": "I-001", "severity": "invalid_severity"},  # 无效的 severity
        ]

        result = validate_issues_list(invalid_issues)
        assert not result.valid
        # 验证错误包含字段路径
        assert any("issues[0]" in str(e.get("loc", ())) for e in result.errors)
