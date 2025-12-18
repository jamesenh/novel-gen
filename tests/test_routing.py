"""路由逻辑测试。

测试 blocker 门禁和章节推进逻辑。
"""

from app.graph.routing import (
    advance_chapter,
    mark_complete,
    mark_human_review,
    should_continue_chapters,
    should_revise,
)
from app.graph.state import State, create_initial_state


class TestShouldRevise:
    """测试 should_revise 路由函数。"""

    def test_no_blockers_returns_store(self):
        """当 blocker_count == 0 时，应路由到 store。"""
        state: State = {
            "audit_result": {"blocker_count": 0},
            "revision_round": 0,
            "max_revision_rounds": 3,
        }
        assert should_revise(state) == "store"

    def test_blockers_under_max_returns_revise(self):
        """当存在 blockers 且未达最大轮次时，应路由到 revise。"""
        state: State = {
            "audit_result": {"blocker_count": 2},
            "revision_round": 1,
            "max_revision_rounds": 3,
        }
        assert should_revise(state) == "revise"

    def test_blockers_at_max_returns_human_review(self):
        """当存在 blockers 且达到最大轮次时，应路由到 human_review。"""
        state: State = {
            "audit_result": {"blocker_count": 1},
            "revision_round": 3,
            "max_revision_rounds": 3,
        }
        assert should_revise(state) == "human_review"

    def test_blockers_over_max_returns_human_review(self):
        """当存在 blockers 且超过最大轮次时，应路由到 human_review。"""
        state: State = {
            "audit_result": {"blocker_count": 1},
            "revision_round": 5,
            "max_revision_rounds": 3,
        }
        assert should_revise(state) == "human_review"

    def test_empty_state_defaults_to_store(self):
        """空状态应默认路由到 store（0 个 blockers）。"""
        state: State = {}
        assert should_revise(state) == "store"


class TestShouldContinueChapters:
    """测试 should_continue_chapters 路由函数。"""

    def test_more_chapters_returns_next(self):
        """当 current < total 时，应路由到 next_chapter。"""
        state: State = {
            "current_chapter": 1,
            "num_chapters": 3,
        }
        assert should_continue_chapters(state) == "next_chapter"

    def test_last_chapter_returns_complete(self):
        """当 current == total 时，应路由到 complete。"""
        state: State = {
            "current_chapter": 3,
            "num_chapters": 3,
        }
        assert should_continue_chapters(state) == "complete"

    def test_single_chapter_returns_complete(self):
        """单章工作流应在第一章后完成。"""
        state: State = {
            "current_chapter": 1,
            "num_chapters": 1,
        }
        assert should_continue_chapters(state) == "complete"


class TestStateUpdates:
    """测试状态更新函数。"""

    def test_advance_chapter_increments_and_resets(self):
        """advance_chapter 应递增章节并重置修订状态。"""
        state: State = {
            "current_chapter": 1,
            "revision_round": 2,
            "chapter_plan": {"some": "data"},
            "chapter_draft": {"some": "draft"},
            "audit_result": {"issues": []},
        }
        updates = advance_chapter(state)

        assert updates["current_chapter"] == 2
        assert updates["revision_round"] == 0
        assert updates["chapter_plan"] == {}
        assert updates["chapter_draft"] == {}
        assert updates["audit_result"] == {}

    def test_mark_human_review_sets_flag(self):
        """mark_human_review 应设置 needs_human_review 标志。"""
        state: State = {"needs_human_review": False}
        updates = mark_human_review(state)

        assert updates["needs_human_review"] is True

    def test_mark_complete_sets_flag(self):
        """mark_complete 应设置 completed 标志。"""
        state: State = {"completed": False}
        updates = mark_complete(state)

        assert updates["completed"] is True


class TestInitialState:
    """测试初始状态创建。"""

    def test_create_initial_state_defaults(self):
        """初始状态应有正确的默认值。"""
        state = create_initial_state(project_name="test_project")

        assert state["project_name"] == "test_project"
        assert state["current_chapter"] == 1
        assert state["num_chapters"] == 1
        assert state["revision_round"] == 0
        assert state["max_revision_rounds"] == 3
        assert state["needs_human_review"] is False
        assert state["completed"] is False
        assert "run_id" in state

    def test_create_initial_state_custom_values(self):
        """初始状态应接受自定义值。"""
        state = create_initial_state(
            project_name="custom",
            num_chapters=5,
            prompt="Write a story",
            max_revision_rounds=5,
        )

        assert state["project_name"] == "custom"
        assert state["num_chapters"] == 5
        assert state["prompt"] == "Write a story"
        assert state["max_revision_rounds"] == 5
