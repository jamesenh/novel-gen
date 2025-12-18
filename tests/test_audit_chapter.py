"""审计节点测试。

验证:
1) 无效插件输出会被拒绝（带可定位错误）
2) qa_major_max 会产出 major_over_threshold 提示信息
"""

import pytest

from app.graph.nodes.audit_chapter import audit_chapter
from app.graph.state import State


class _MajorIssuesPlugin:
    name = "major_issues_plugin"

    def __init__(self, major_count: int):
        self._major_count = major_count

    def analyze(self, state: State, context: dict):
        return [
            {
                "id": f"M-{i:03d}",
                "severity": "major",
                "category": "timeline",
                "summary": f"Major issue {i}",
            }
            for i in range(self._major_count)
        ]


class _InvalidIssuePlugin:
    name = "invalid_issue_plugin"

    def analyze(self, state: State, context: dict):
        return [{"id": "X-001", "severity": "not-a-valid-severity"}]


def test_audit_rejects_invalid_plugin_issues(monkeypatch):
    monkeypatch.setattr(
        "app.graph.nodes.audit_chapter.get_audit_plugins",
        lambda: [_InvalidIssuePlugin()],
    )

    state: State = {
        "current_chapter": 1,
        "chapter_draft": {"scenes": [{"content": ""}]},
    }

    with pytest.raises(ValueError) as exc:
        audit_chapter(state)

    assert "invalid issues" in str(exc.value)
    assert "issues[0]" in str(exc.value)


def test_audit_sets_major_over_threshold(monkeypatch):
    monkeypatch.setattr(
        "app.graph.nodes.audit_chapter.get_audit_plugins",
        lambda: [_MajorIssuesPlugin(major_count=4)],
    )

    state: State = {
        "current_chapter": 1,
        "chapter_draft": {"scenes": [{"content": ""}]},
        "qa_major_max": 3,
    }

    result = audit_chapter(state)["audit_result"]

    assert result["major_count"] == 4
    assert result["qa_major_max"] == 3
    assert result["major_over_threshold"] is True
