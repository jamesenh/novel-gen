"""
逻辑审查质量闸门回归测试

测试目标：
1. 触发阻断时，后续章节/场景生成入口都会返回一致的阻断错误
2. 应用修订后阻断解除，可继续生成

作者: jamesenh, 2025-12-17
开发者: jamesenh, 开发时间: 2025-12-16
"""
import os
import json
import tempfile
import shutil
import pytest
from datetime import datetime

from novelgen.models import (
    RevisionStatus, LogicReviewReport, LogicReviewIssue,
    ConsistencyIssue, GeneratedChapter, GeneratedScene
)
from novelgen.runtime.gate import (
    find_pending_revisions,
    get_blocked_chapter,
    check_pending_revision_gate,
    check_pending_revision_gate_for_range,
    PendingRevisionGateError,
    PendingRevisionInfo
)


class TestGateModule:
    """测试 gate.py 模块的核心功能"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        temp_dir = tempfile.mkdtemp()
        chapters_dir = os.path.join(temp_dir, "chapters")
        reviews_dir = os.path.join(temp_dir, "reviews")
        os.makedirs(chapters_dir)
        os.makedirs(reviews_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def _create_pending_revision(self, project_dir: str, chapter_number: int, triggered_by: str = "logic_review"):
        """创建 pending 状态的修订文件"""
        chapters_dir = os.path.join(project_dir, "chapters")
        revision_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}_revision.json")
        
        revision = RevisionStatus(
            chapter_number=chapter_number,
            status="pending",
            revision_notes=f"第 {chapter_number} 章逻辑审查未通过",
            issues=[],
            revised_chapter=None,
            created_at=datetime.now().isoformat(),
            triggered_by=triggered_by
        )
        
        with open(revision_file, 'w', encoding='utf-8') as f:
            json.dump(revision.model_dump(), f, ensure_ascii=False, indent=2)
        
        return revision_file
    
    def _create_logic_review_report(self, project_dir: str, chapter_number: int, score: int = 60):
        """创建逻辑审查报告"""
        reviews_dir = os.path.join(project_dir, "reviews")
        report_file = os.path.join(reviews_dir, f"chapter_{chapter_number:03d}_logic_review.json")
        
        report = LogicReviewReport(
            chapter_number=chapter_number,
            overall_score=score,
            issues=[
                LogicReviewIssue(
                    issue_type="因果断裂",
                    description="主角突然获得力量缺乏铺垫",
                    severity="high",
                    evidence="第三段...",
                    fix_instructions="在前文添加伏笔"
                )
            ],
            summary=f"第 {chapter_number} 章评分 {score}，存在高严重性问题"
        )
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
        
        return report_file
    
    def test_no_pending_revisions(self, temp_project_dir):
        """测试无 pending revision 时的行为"""
        pending_list = find_pending_revisions(temp_project_dir)
        assert len(pending_list) == 0
        
        blocked = get_blocked_chapter(temp_project_dir)
        assert blocked is None
        
        # 不应抛出异常
        check_pending_revision_gate(temp_project_dir, target_chapter=5)
    
    def test_find_pending_revisions(self, temp_project_dir):
        """测试查找 pending revisions"""
        # 创建多个修订文件
        self._create_pending_revision(temp_project_dir, 3)
        self._create_pending_revision(temp_project_dir, 5)
        
        pending_list = find_pending_revisions(temp_project_dir)
        assert len(pending_list) == 2
        assert pending_list[0].chapter_number == 3  # 按章节号排序
        assert pending_list[1].chapter_number == 5
    
    def test_get_blocked_chapter(self, temp_project_dir):
        """测试获取被阻断的最小章节号"""
        self._create_pending_revision(temp_project_dir, 5)
        self._create_pending_revision(temp_project_dir, 3)
        
        blocked = get_blocked_chapter(temp_project_dir)
        assert blocked == 3  # 返回最小章节号
    
    def test_gate_blocks_subsequent_chapters(self, temp_project_dir):
        """测试闸门阻止后续章节生成"""
        self._create_pending_revision(temp_project_dir, 3)
        
        # 目标章节 > blocked_chapter 应抛出异常
        with pytest.raises(PendingRevisionGateError) as exc_info:
            check_pending_revision_gate(temp_project_dir, target_chapter=4)
        
        assert exc_info.value.blocked_chapter == 3
        assert exc_info.value.target_chapter == 4
    
    def test_gate_allows_blocked_chapter_itself(self, temp_project_dir):
        """测试闸门允许被阻断章节本身的操作"""
        self._create_pending_revision(temp_project_dir, 3)
        
        # 目标章节 == blocked_chapter 不应抛出异常
        check_pending_revision_gate(temp_project_dir, target_chapter=3)
    
    def test_gate_allows_prior_chapters(self, temp_project_dir):
        """测试闸门允许阻断章节之前的操作"""
        self._create_pending_revision(temp_project_dir, 3)
        
        # 目标章节 < blocked_chapter 不应抛出异常
        check_pending_revision_gate(temp_project_dir, target_chapter=2)
        check_pending_revision_gate(temp_project_dir, target_chapter=1)
    
    def test_gate_for_range(self, temp_project_dir):
        """测试范围检查"""
        self._create_pending_revision(temp_project_dir, 3)
        
        # 范围完全在阻断章节之前：允许
        check_pending_revision_gate_for_range(temp_project_dir, start_chapter=1, end_chapter=2)
        
        # 范围包含阻断章节：允许（因为 3 == blocked_chapter）
        check_pending_revision_gate_for_range(temp_project_dir, start_chapter=1, end_chapter=3)
        
        # 范围超过阻断章节：阻止
        with pytest.raises(PendingRevisionGateError):
            check_pending_revision_gate_for_range(temp_project_dir, start_chapter=1, end_chapter=4)
        
        with pytest.raises(PendingRevisionGateError):
            check_pending_revision_gate_for_range(temp_project_dir, start_chapter=4, end_chapter=5)
    
    def test_error_dict_format(self, temp_project_dir):
        """测试错误信息的字典格式"""
        revision_file = self._create_pending_revision(temp_project_dir, 3)
        report_file = self._create_logic_review_report(temp_project_dir, 3)
        
        try:
            check_pending_revision_gate(temp_project_dir, target_chapter=5)
        except PendingRevisionGateError as e:
            error_dict = e.to_dict()
            
            assert "blocked_chapter" in error_dict
            assert error_dict["blocked_chapter"] == 3
            assert "target_chapter" in error_dict
            assert error_dict["target_chapter"] == 5
            assert "revision_status_file" in error_dict
            assert "next_actions" in error_dict
            assert isinstance(error_dict["next_actions"], list)


class TestRevisionStatusLifecycle:
    """测试修订状态的生命周期"""
    
    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录"""
        temp_dir = tempfile.mkdtemp()
        chapters_dir = os.path.join(temp_dir, "chapters")
        reviews_dir = os.path.join(temp_dir, "reviews")
        os.makedirs(chapters_dir)
        os.makedirs(reviews_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def _set_revision_status(self, project_dir: str, chapter_number: int, status: str):
        """设置修订状态"""
        chapters_dir = os.path.join(project_dir, "chapters")
        revision_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}_revision.json")
        
        if os.path.exists(revision_file):
            with open(revision_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["status"] = status
            data["decision_at"] = datetime.now().isoformat()
        else:
            data = RevisionStatus(
                chapter_number=chapter_number,
                status=status,
                revision_notes="测试修订",
                issues=[],
                revised_chapter=None,
                created_at=datetime.now().isoformat(),
                decision_at=datetime.now().isoformat(),
                triggered_by="logic_review"
            ).model_dump()
        
        with open(revision_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def test_accepted_revision_releases_gate(self, temp_project_dir):
        """测试接受修订后闸门解除"""
        # 创建 pending 修订
        chapters_dir = os.path.join(temp_project_dir, "chapters")
        revision_file = os.path.join(chapters_dir, "chapter_003_revision.json")
        
        revision = RevisionStatus(
            chapter_number=3,
            status="pending",
            revision_notes="测试",
            issues=[],
            revised_chapter=None,
            created_at=datetime.now().isoformat(),
            triggered_by="logic_review"
        )
        with open(revision_file, 'w', encoding='utf-8') as f:
            json.dump(revision.model_dump(), f, ensure_ascii=False, indent=2)
        
        # 验证阻断存在
        with pytest.raises(PendingRevisionGateError):
            check_pending_revision_gate(temp_project_dir, target_chapter=5)
        
        # 将状态改为 accepted
        self._set_revision_status(temp_project_dir, 3, "accepted")
        
        # 验证阻断解除
        check_pending_revision_gate(temp_project_dir, target_chapter=5)  # 不应抛出异常
    
    def test_rejected_revision_releases_gate(self, temp_project_dir):
        """测试拒绝修订后闸门解除"""
        # 创建 pending 修订
        chapters_dir = os.path.join(temp_project_dir, "chapters")
        revision_file = os.path.join(chapters_dir, "chapter_003_revision.json")
        
        revision = RevisionStatus(
            chapter_number=3,
            status="pending",
            revision_notes="测试",
            issues=[],
            revised_chapter=None,
            created_at=datetime.now().isoformat(),
            triggered_by="logic_review"
        )
        with open(revision_file, 'w', encoding='utf-8') as f:
            json.dump(revision.model_dump(), f, ensure_ascii=False, indent=2)
        
        # 验证阻断存在
        with pytest.raises(PendingRevisionGateError):
            check_pending_revision_gate(temp_project_dir, target_chapter=5)
        
        # 将状态改为 rejected
        self._set_revision_status(temp_project_dir, 3, "rejected")
        
        # 验证阻断解除
        check_pending_revision_gate(temp_project_dir, target_chapter=5)  # 不应抛出异常


class TestLogicReviewReport:
    """测试 LogicReviewReport 模型的阻断判断逻辑"""
    
    def test_should_block_low_score(self):
        """测试低分触发阻断"""
        report = LogicReviewReport(
            chapter_number=1,
            overall_score=60,
            issues=[],
            summary="评分较低"
        )
        
        assert report.should_block(min_score=75) is True
        assert report.should_block(min_score=60) is False
        assert report.should_block(min_score=50) is False
    
    def test_should_block_high_severity_issue(self):
        """测试高严重性问题触发阻断"""
        report = LogicReviewReport(
            chapter_number=1,
            overall_score=80,  # 分数高于阈值
            issues=[
                LogicReviewIssue(
                    issue_type="因果断裂",
                    description="问题描述",
                    severity="high"
                )
            ],
            summary="存在高严重性问题"
        )
        
        assert report.should_block(min_score=75) is True
    
    def test_no_block_when_passing(self):
        """测试通过时不阻断"""
        report = LogicReviewReport(
            chapter_number=1,
            overall_score=85,
            issues=[
                LogicReviewIssue(
                    issue_type="节奏失衡",
                    description="轻微问题",
                    severity="medium"
                ),
                LogicReviewIssue(
                    issue_type="用词重复",
                    description="小问题",
                    severity="low"
                )
            ],
            summary="整体良好"
        )
        
        assert report.should_block(min_score=75) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
