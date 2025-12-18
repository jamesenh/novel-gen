"""插件边界执行测试。

测试插件:
1. 只返回结构化问题
2. 不直接写入文件系统/数据库
"""

from pathlib import Path
from unittest.mock import patch

from app.agents.continuity import ContinuityPlugin
from app.agents.noop import NoopPlugin
from app.agents.registry import (
    get_audit_plugins,
    get_plugin,
)
from app.graph.state import State


class TestPluginReadOnlyBoundary:
    """测试插件不执行直接写入。"""

    def test_noop_plugin_returns_empty_list(self):
        """NoopPlugin 应返回空问题列表。"""
        plugin = NoopPlugin()
        state: State = {"chapter_draft": {"content": "test"}}
        context = {}

        issues = plugin.analyze(state, context)

        assert isinstance(issues, list)
        assert len(issues) == 0

    def test_continuity_plugin_returns_structured_issues(self):
        """ContinuityPlugin 应返回正确结构化的问题。"""
        plugin = ContinuityPlugin()
        state: State = {
            "current_chapter": 1,
            "chapter_draft": {"scenes": []},  # Empty scenes triggers issue
        }
        context = {"world": {}, "characters": {}}

        issues = plugin.analyze(state, context)

        assert isinstance(issues, list)
        # Should have at least one issue for empty scenes
        assert len(issues) >= 1

        # Check issue structure
        issue = issues[0]
        assert "id" in issue
        assert "severity" in issue
        assert "category" in issue
        assert "summary" in issue

    def test_plugin_does_not_call_open(self):
        """插件 analyze 不应调用 open() 进行文件写入。"""
        plugin = ContinuityPlugin()
        state: State = {
            "current_chapter": 1,
            "chapter_draft": {"scenes": [{"content": "test"}]},
        }
        context = {}

        with patch("builtins.open") as mock_open:
            plugin.analyze(state, context)
            # Plugin should not have called open()
            mock_open.assert_not_called()

    def test_plugin_does_not_call_pathlib_write(self):
        """插件 analyze 不应调用 Path.write_*() 方法。"""
        plugin = ContinuityPlugin()
        state: State = {
            "current_chapter": 1,
            "chapter_draft": {"scenes": [{"content": "test"}]},
        }
        context = {}

        with patch.object(Path, "write_text") as mock_write:
            with patch.object(Path, "write_bytes") as mock_bytes:
                plugin.analyze(state, context)
                mock_write.assert_not_called()
                mock_bytes.assert_not_called()


class TestPluginOutputContract:
    """测试插件输出契约。"""

    def test_issue_has_severity(self):
        """所有问题必须有 severity 字段。"""
        plugin = ContinuityPlugin()
        state: State = {
            "current_chapter": 1,
            "chapter_draft": {"scenes": []},
        }
        context = {}

        issues = plugin.analyze(state, context)

        for issue in issues:
            assert "severity" in issue
            assert issue["severity"] in ["blocker", "major", "minor"]

    def test_issue_has_category(self):
        """所有问题必须有 category 字段。"""
        plugin = ContinuityPlugin()
        state: State = {
            "current_chapter": 1,
            "chapter_draft": {"scenes": []},
        }
        context = {}

        issues = plugin.analyze(state, context)

        valid_categories = [
            "world_rule",
            "character",
            "timeline",
            "knowledge",
            "thread",
            "pov_style",
        ]
        for issue in issues:
            assert "category" in issue
            assert issue["category"] in valid_categories

    def test_blocker_issue_has_fix_instructions(self):
        """Blocker 问题必须有 fix_instructions。"""
        plugin = ContinuityPlugin()
        state: State = {
            "current_chapter": 1,
            "chapter_draft": {"scenes": []},
        }
        context = {}

        issues = plugin.analyze(state, context)

        blockers = [i for i in issues if i.get("severity") == "blocker"]
        for blocker in blockers:
            assert "fix_instructions" in blocker
            assert blocker["fix_instructions"]  # Non-empty


class TestPluginRegistry:
    """测试插件注册和检索。"""

    def test_default_plugins_registered(self):
        """默认插件应在 import 时注册。"""
        plugins = get_audit_plugins()
        names = [p.name for p in plugins]

        assert "noop" in names
        assert "continuity" in names

    def test_get_plugin_by_name(self):
        """应能按名称检索插件。"""
        plugin = get_plugin("noop")
        assert plugin is not None
        assert plugin.name == "noop"

    def test_get_nonexistent_plugin_returns_none(self):
        """获取不存在的插件应返回 None。"""
        plugin = get_plugin("nonexistent")
        assert plugin is None


class TestPluginInputContract:
    """测试插件输入契约。"""

    def test_plugin_receives_state_and_context(self):
        """插件 analyze 应接收 state 和 context 字典。"""
        plugin = NoopPlugin()

        state: State = {
            "current_chapter": 1,
            "chapter_draft": {"scenes": []},
        }
        context = {
            "world": {"name": "TestWorld"},
            "characters": {"hero": {}},
            "outline": {"chapters": []},
        }

        # Should not raise
        issues = plugin.analyze(state, context)
        assert isinstance(issues, list)
