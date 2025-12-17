"""
修订工具模块
提供逻辑审查报告查看、修订候选生成、修订应用等工具

核心工具：
- review.report       查看审查报告（无需确认）
- review.generate_fix 生成修订候选（普通确认）
- review.apply        应用修订/接受（破坏性确认）
- review.reject       拒绝修订/清除阻断状态（普通确认）
- review.list         列出所有 pending revisions（无需确认）

设计原则：
- review.report 和 review.list 为只读操作，无需确认
- review.generate_fix 需要 LLM 调用，普通确认
- review.apply 修改章节文件，属于破坏性操作
- review.reject 只修改 revision 状态，属于普通确认

作者: jamesenh, 2025-12-17
开发者: jamesenh, 开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult
from novelgen.models import (
    LogicReviewReport, LogicReviewIssue, RevisionStatus,
    GeneratedChapter, GeneratedScene, ChapterPlan,
    WorldSetting, CharactersConfig
)
from novelgen.runtime.gate import (
    find_pending_revisions,
    PendingRevisionInfo,
)


def create_revision_tools(project_dir: str, project_id: str) -> List[Tool]:
    """创建修订工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    chapters_dir = os.path.join(project_dir, "chapters")
    reviews_dir = os.path.join(project_dir, "reviews")
    
    def _get_review_report_path(chapter_num: int) -> str:
        """获取逻辑审查报告路径"""
        return os.path.join(reviews_dir, f"chapter_{chapter_num:03d}_logic_review.json")
    
    def _get_revision_status_path(chapter_num: int) -> str:
        """获取修订状态文件路径"""
        return os.path.join(chapters_dir, f"chapter_{chapter_num:03d}_revision.json")
    
    def _get_chapter_path(chapter_num: int) -> str:
        """获取章节文件路径"""
        return os.path.join(chapters_dir, f"chapter_{chapter_num:03d}.json")
    
    def _get_chapter_plan_path(chapter_num: int) -> str:
        """获取章节计划文件路径"""
        return os.path.join(chapters_dir, f"chapter_{chapter_num:03d}_plan.json")
    
    def _load_world() -> Optional[WorldSetting]:
        """加载世界观"""
        world_file = os.path.join(project_dir, "world.json")
        if not os.path.exists(world_file):
            return None
        with open(world_file, 'r', encoding='utf-8') as f:
            return WorldSetting(**json.load(f))
    
    def _load_characters() -> Optional[CharactersConfig]:
        """加载角色"""
        char_file = os.path.join(project_dir, "characters.json")
        if not os.path.exists(char_file):
            return None
        with open(char_file, 'r', encoding='utf-8') as f:
            return CharactersConfig(**json.load(f))
    
    def view_review_report(chapter_number: int) -> ToolResult:
        """查看章节的逻辑审查报告
        
        只读操作，无需确认
        
        Args:
            chapter_number: 章节编号
            
        Returns:
            包含审查报告的 ToolResult
        """
        try:
            report_path = _get_review_report_path(chapter_number)
            
            if not os.path.exists(report_path):
                return ToolResult(
                    tool_name="review.report",
                    success=False,
                    error=f"第 {chapter_number} 章的逻辑审查报告不存在",
                    data={"chapter_number": chapter_number, "report_file": report_path}
                )
            
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            report = LogicReviewReport(**report_data)
            
            # 格式化报告用于显示
            formatted_report = {
                "chapter_number": report.chapter_number,
                "overall_score": report.overall_score,
                "summary": report.summary,
                "issues_count": len(report.issues),
                "high_severity_count": sum(1 for i in report.issues if i.severity == "high"),
                "issues": [
                    {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "description": issue.description,
                        "evidence": issue.evidence,
                        "fix_instructions": issue.fix_instructions
                    }
                    for issue in report.issues
                ],
                "report_file": report_path
            }
            
            return ToolResult(
                tool_name="review.report",
                success=True,
                message=f"第 {chapter_number} 章逻辑审查报告：评分 {report.overall_score}/100，问题 {len(report.issues)} 个",
                data=formatted_report
            )
        except Exception as e:
            return ToolResult(
                tool_name="review.report",
                success=False,
                error=str(e)
            )
    
    def list_pending_revisions() -> ToolResult:
        """列出所有 pending 状态的修订
        
        只读操作，无需确认
        
        Returns:
            包含 pending 修订列表的 ToolResult
        """
        try:
            pending_list = find_pending_revisions(project_dir)
            
            if not pending_list:
                return ToolResult(
                    tool_name="review.list",
                    success=True,
                    message="没有 pending 状态的修订",
                    data={"pending_count": 0, "revisions": []}
                )
            
            revisions_data = []
            for info in pending_list:
                revision_entry = {
                    "chapter_number": info.chapter_number,
                    "triggered_by": info.triggered_by,
                    "revision_file": info.revision_file,
                    "revision_notes": info.revision_notes[:100] + "..." if len(info.revision_notes) > 100 else info.revision_notes
                }
                
                # 尝试加载逻辑审查报告获取评分
                if info.logic_review_file and os.path.exists(info.logic_review_file):
                    try:
                        with open(info.logic_review_file, 'r', encoding='utf-8') as f:
                            report = LogicReviewReport(**json.load(f))
                        revision_entry["score"] = report.overall_score
                        revision_entry["issues_count"] = len(report.issues)
                        revision_entry["logic_review_file"] = info.logic_review_file
                    except Exception:
                        pass
                
                revisions_data.append(revision_entry)
            
            blocked_chapter = pending_list[0].chapter_number
            
            return ToolResult(
                tool_name="review.list",
                success=True,
                message=f"发现 {len(pending_list)} 个 pending 修订，阻断章节：{blocked_chapter}",
                data={
                    "pending_count": len(pending_list),
                    "blocked_chapter": blocked_chapter,
                    "revisions": revisions_data
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="review.list",
                success=False,
                error=str(e)
            )
    
    def generate_revision_candidate(chapter_number: int) -> ToolResult:
        """为指定章节生成修订候选
        
        基于审查报告中的问题，使用 LLM 生成修订后的章节内容
        需要普通确认（可被 /auto on 跳过）
        
        Args:
            chapter_number: 章节编号
            
        Returns:
            包含修订候选的 ToolResult
        """
        try:
            # 检查修订状态文件是否存在
            revision_path = _get_revision_status_path(chapter_number)
            if not os.path.exists(revision_path):
                return ToolResult(
                    tool_name="review.generate_fix",
                    success=False,
                    error=f"第 {chapter_number} 章没有 pending 修订状态",
                    data={"chapter_number": chapter_number}
                )
            
            with open(revision_path, 'r', encoding='utf-8') as f:
                revision_status = RevisionStatus(**json.load(f))
            
            if revision_status.status != "pending":
                return ToolResult(
                    tool_name="review.generate_fix",
                    success=False,
                    error=f"第 {chapter_number} 章的修订状态不是 pending，当前状态：{revision_status.status}",
                    data={"chapter_number": chapter_number, "status": revision_status.status}
                )
            
            # 加载原章节
            chapter_path = _get_chapter_path(chapter_number)
            if not os.path.exists(chapter_path):
                return ToolResult(
                    tool_name="review.generate_fix",
                    success=False,
                    error=f"第 {chapter_number} 章的原文不存在",
                    data={"chapter_number": chapter_number}
                )
            
            with open(chapter_path, 'r', encoding='utf-8') as f:
                original_chapter = GeneratedChapter(**json.load(f))
            
            # 加载审查报告
            report_path = _get_review_report_path(chapter_number)
            report: Optional[LogicReviewReport] = None
            if os.path.exists(report_path):
                with open(report_path, 'r', encoding='utf-8') as f:
                    report = LogicReviewReport(**json.load(f))
            
            # 加载章节计划
            plan_path = _get_chapter_plan_path(chapter_number)
            chapter_plan: Optional[ChapterPlan] = None
            if os.path.exists(plan_path):
                with open(plan_path, 'r', encoding='utf-8') as f:
                    chapter_plan = ChapterPlan(**json.load(f))
            
            # 加载世界观和角色
            world = _load_world()
            characters = _load_characters()
            
            # 构建修订 prompt 并调用 LLM
            from novelgen.chains.chapter_revision_chain import generate_revised_chapter
            
            print(f"🔧 正在为第 {chapter_number} 章生成修订候选...")
            
            revised_chapter = generate_revised_chapter(
                original_chapter=original_chapter,
                review_report=report,
                chapter_plan=chapter_plan,
                world_setting=world,
                characters=characters,
                verbose=False
            )
            
            # 更新修订状态文件，添加候选
            revision_status.revised_chapter = revised_chapter
            
            with open(revision_path, 'w', encoding='utf-8') as f:
                json.dump(revision_status.model_dump(), f, ensure_ascii=False, indent=2)
            
            print(f"✅ 第 {chapter_number} 章修订候选已生成")
            
            return ToolResult(
                tool_name="review.generate_fix",
                success=True,
                message=f"第 {chapter_number} 章修订候选已生成，共 {revised_chapter.total_words} 字",
                data={
                    "chapter_number": chapter_number,
                    "original_words": original_chapter.total_words,
                    "revised_words": revised_chapter.total_words,
                    "revision_file": revision_path,
                    "next_action": "review.apply 应用修订，或 review.reject 拒绝"
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="review.generate_fix",
                success=False,
                error=str(e)
            )
    
    def apply_revision(chapter_number: int) -> ToolResult:
        """应用修订候选，替换原章节
        
        破坏性操作，始终需要确认
        
        Args:
            chapter_number: 章节编号
            
        Returns:
            应用结果的 ToolResult
        """
        try:
            revision_path = _get_revision_status_path(chapter_number)
            
            if not os.path.exists(revision_path):
                return ToolResult(
                    tool_name="review.apply",
                    success=False,
                    error=f"第 {chapter_number} 章没有修订状态文件",
                    data={"chapter_number": chapter_number}
                )
            
            with open(revision_path, 'r', encoding='utf-8') as f:
                revision_status = RevisionStatus(**json.load(f))
            
            if revision_status.status != "pending":
                return ToolResult(
                    tool_name="review.apply",
                    success=False,
                    error=f"第 {chapter_number} 章的修订状态不是 pending",
                    data={"chapter_number": chapter_number, "status": revision_status.status}
                )
            
            if revision_status.revised_chapter is None:
                return ToolResult(
                    tool_name="review.apply",
                    success=False,
                    error=f"第 {chapter_number} 章没有修订候选，请先使用 review.generate_fix 生成",
                    data={"chapter_number": chapter_number}
                )
            
            # 备份原章节（可选）
            chapter_path = _get_chapter_path(chapter_number)
            backup_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}_backup.json")
            
            if os.path.exists(chapter_path):
                with open(chapter_path, 'r', encoding='utf-8') as f:
                    original_data = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_data)
                print(f"📦 已备份原章节到 {backup_path}")
            
            # 应用修订
            revised = revision_status.revised_chapter
            with open(chapter_path, 'w', encoding='utf-8') as f:
                json.dump(revised.model_dump(), f, ensure_ascii=False, indent=2)
            
            # 更新修订状态为 accepted
            revision_status.status = "accepted"
            revision_status.decision_at = datetime.now().isoformat()
            
            with open(revision_path, 'w', encoding='utf-8') as f:
                json.dump(revision_status.model_dump(), f, ensure_ascii=False, indent=2)
            
            print(f"✅ 第 {chapter_number} 章修订已应用")
            
            return ToolResult(
                tool_name="review.apply",
                success=True,
                message=f"第 {chapter_number} 章修订已应用，共 {revised.total_words} 字",
                data={
                    "chapter_number": chapter_number,
                    "status": "accepted",
                    "total_words": revised.total_words,
                    "chapter_file": chapter_path,
                    "backup_file": backup_path
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="review.apply",
                success=False,
                error=str(e)
            )
    
    def reject_revision(chapter_number: int, reason: str = "") -> ToolResult:
        """拒绝修订，清除阻断状态
        
        将修订状态设为 rejected，允许继续生成后续章节
        普通确认（可被 /auto on 跳过）
        
        Args:
            chapter_number: 章节编号
            reason: 拒绝原因（可选）
            
        Returns:
            拒绝结果的 ToolResult
        """
        try:
            revision_path = _get_revision_status_path(chapter_number)
            
            if not os.path.exists(revision_path):
                return ToolResult(
                    tool_name="review.reject",
                    success=False,
                    error=f"第 {chapter_number} 章没有修订状态文件",
                    data={"chapter_number": chapter_number}
                )
            
            with open(revision_path, 'r', encoding='utf-8') as f:
                revision_status = RevisionStatus(**json.load(f))
            
            if revision_status.status != "pending":
                return ToolResult(
                    tool_name="review.reject",
                    success=False,
                    error=f"第 {chapter_number} 章的修订状态不是 pending",
                    data={"chapter_number": chapter_number, "status": revision_status.status}
                )
            
            # 更新修订状态为 rejected
            revision_status.status = "rejected"
            revision_status.decision_at = datetime.now().isoformat()
            if reason:
                revision_status.revision_notes += f"\n[拒绝原因] {reason}"
            
            with open(revision_path, 'w', encoding='utf-8') as f:
                json.dump(revision_status.model_dump(), f, ensure_ascii=False, indent=2)
            
            print(f"⏭️ 第 {chapter_number} 章修订已拒绝，阻断已解除")
            
            return ToolResult(
                tool_name="review.reject",
                success=True,
                message=f"第 {chapter_number} 章修订已拒绝，可继续生成后续章节",
                data={
                    "chapter_number": chapter_number,
                    "status": "rejected",
                    "revision_file": revision_path
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="review.reject",
                success=False,
                error=str(e)
            )
    
    def view_revision_status(chapter_number: int) -> ToolResult:
        """查看章节的修订状态
        
        只读操作，无需确认
        
        Args:
            chapter_number: 章节编号
            
        Returns:
            包含修订状态的 ToolResult
        """
        try:
            revision_path = _get_revision_status_path(chapter_number)
            
            if not os.path.exists(revision_path):
                return ToolResult(
                    tool_name="review.status",
                    success=True,
                    message=f"第 {chapter_number} 章没有修订状态",
                    data={"chapter_number": chapter_number, "has_revision": False}
                )
            
            with open(revision_path, 'r', encoding='utf-8') as f:
                revision_status = RevisionStatus(**json.load(f))
            
            status_data = {
                "chapter_number": revision_status.chapter_number,
                "status": revision_status.status,
                "triggered_by": revision_status.triggered_by,
                "revision_notes": revision_status.revision_notes,
                "created_at": revision_status.created_at,
                "decision_at": revision_status.decision_at,
                "has_candidate": revision_status.revised_chapter is not None,
                "issues_count": len(revision_status.issues),
                "revision_file": revision_path
            }
            
            if revision_status.revised_chapter:
                status_data["candidate_words"] = revision_status.revised_chapter.total_words
            
            return ToolResult(
                tool_name="review.status",
                success=True,
                message=f"第 {chapter_number} 章修订状态：{revision_status.status}",
                data=status_data
            )
        except Exception as e:
            return ToolResult(
                tool_name="review.status",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="review.report",
            category=ToolCategory.FINE_GRAINED,
            description="查看章节的逻辑审查报告",
            confirm_level=ConfirmLevel.NONE,  # 只读，无需确认
            slash_command="/review",
            handler=view_review_report
        ),
        Tool(
            name="review.list",
            category=ToolCategory.FINE_GRAINED,
            description="列出所有 pending 状态的修订",
            confirm_level=ConfirmLevel.NONE,  # 只读，无需确认
            slash_command="/pending",
            handler=list_pending_revisions
        ),
        Tool(
            name="review.status",
            category=ToolCategory.FINE_GRAINED,
            description="查看章节的修订状态",
            confirm_level=ConfirmLevel.NONE,  # 只读，无需确认
            handler=view_revision_status
        ),
        Tool(
            name="review.generate_fix",
            category=ToolCategory.FINE_GRAINED,
            description="为章节生成修订候选（需要 LLM 调用）",
            confirm_level=ConfirmLevel.NORMAL,  # 普通确认
            slash_command="/fix",
            handler=generate_revision_candidate
        ),
        Tool(
            name="review.apply",
            category=ToolCategory.FINE_GRAINED,
            description="应用修订候选，替换原章节（破坏性）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,  # 破坏性确认
            slash_command="/accept",
            handler=apply_revision
        ),
        Tool(
            name="review.reject",
            category=ToolCategory.FINE_GRAINED,
            description="拒绝修订，清除阻断状态",
            confirm_level=ConfirmLevel.NORMAL,  # 普通确认
            slash_command="/reject",
            handler=reject_revision
        ),
    ]
    
    return tools
