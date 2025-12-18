"""Schema 校验测试。

测试资产在持久化前必须通过 schema 校验。
"""

import pytest

from app.schemas.base import add_metadata
from app.schemas.validation import (
    validate_audit_report,
    validate_by_type,
    validate_chapter_content,
    validate_chapter_plan,
)


class TestChapterPlanValidation:
    """测试章节计划 schema 校验。"""

    def test_valid_minimal_plan(self):
        """最小有效计划应通过校验。"""
        plan = add_metadata(
            {
                "chapter_id": 1,
            }
        )
        result = validate_chapter_plan(plan)
        assert result.valid

    def test_valid_full_plan(self):
        """包含所有字段的完整计划应通过校验。"""
        plan = add_metadata(
            {
                "chapter_id": 1,
                "pov": "主角",
                "goal": "进入禁区",
                "conflict": "守卫阻拦",
                "turn": "发现内情",
                "reveal": ["禁区并非荒废"],
                "threads_advance": ["T-01"],
                "must_include": ["关键物品A"],
                "must_avoid": ["解释终极谜底"],
                "scenes": [],
            }
        )
        result = validate_chapter_plan(plan)
        assert result.valid

    def test_missing_chapter_id_fails(self):
        """缺少 chapter_id 的计划应失败。"""
        plan = add_metadata(
            {
                "pov": "主角",
            }
        )
        result = validate_chapter_plan(plan)
        assert not result.valid
        assert any("chapter_id" in msg for msg in result.error_messages)

    def test_invalid_chapter_id_type_fails(self):
        """chapter_id 类型错误的计划应失败。"""
        plan = add_metadata(
            {
                "chapter_id": "one",  # Should be int
            }
        )
        result = validate_chapter_plan(plan)
        assert not result.valid


class TestChapterContentValidation:
    """测试章节内容 schema 校验。"""

    def test_valid_minimal_content(self):
        """最小有效内容应通过校验。"""
        content = add_metadata(
            {
                "chapter_id": 1,
            }
        )
        result = validate_chapter_content(content)
        assert result.valid

    def test_valid_full_content(self):
        """包含场景的完整内容应通过校验。"""
        content = add_metadata(
            {
                "chapter_id": 1,
                "title": "第一章",
                "scenes": [
                    {
                        "scene_id": "1_1",
                        "location": "城门",
                        "characters": ["主角"],
                        "purpose": "开场",
                        "content": "正文内容...",
                    }
                ],
                "word_count": 1500,
            }
        )
        result = validate_chapter_content(content)
        assert result.valid


class TestAuditReportValidation:
    """测试审计报告 schema 校验。"""

    def test_valid_empty_report(self):
        """无问题的报告应通过校验。"""
        report = add_metadata(
            {
                "chapter_id": 1,
                "issues": [],
            }
        )
        result = validate_audit_report(report)
        assert result.valid

    def test_valid_report_with_issues(self):
        """包含问题的报告应通过校验。"""
        report = add_metadata(
            {
                "chapter_id": 1,
                "issues": [
                    {
                        "id": "I-001",
                        "severity": "blocker",
                        "category": "timeline",
                        "summary": "时间矛盾",
                        "evidence": {},
                        "fix_instructions": "修正时间线",
                    }
                ],
            }
        )
        result = validate_audit_report(report)
        assert result.valid


class TestValidateByType:
    """测试基于类型的校验。"""

    def test_validate_by_type_chapter_plan(self):
        """应校验 chapter_plan 类型。"""
        plan = add_metadata({"chapter_id": 1})
        result = validate_by_type(plan, "chapter_plan")
        assert result.valid

    def test_validate_by_type_unknown_raises(self):
        """未知类型应抛出 ValueError。"""
        with pytest.raises(ValueError, match="Unknown artifact type"):
            validate_by_type({}, "unknown_type")


class TestMetadataFields:
    """测试必要元数据字段。"""

    def test_add_metadata_includes_all_fields(self):
        """add_metadata 应添加所有必要字段。"""
        data = add_metadata({"chapter_id": 1})

        assert "schema_version" in data
        assert "generated_at" in data
        assert "generator" in data
        assert data["schema_version"] == "1.0"

    def test_add_metadata_preserves_existing(self):
        """add_metadata 应保留现有数据。"""
        data = add_metadata(
            {
                "chapter_id": 1,
                "custom_field": "value",
            }
        )

        assert data["chapter_id"] == 1
        assert data["custom_field"] == "value"
