"""
质量闸门检查模块

提供 pending revision 检查功能，用于在所有生成入口强制执行阻断逻辑。

设计原则：
- 任何 pending revision 都视为"必须先修复"的闸门信号
- 无绕过模式，所有生成入口都必须检查

作者: jamesenh, 2025-12-17
开发者: jamesenh, 开发时间: 2025-12-16
"""
import os
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class PendingRevisionInfo:
    """Pending revision 信息"""
    chapter_number: int
    status: str
    triggered_by: str
    revision_file: str
    logic_review_file: Optional[str] = None
    revision_notes: str = ""


class PendingRevisionGateError(Exception):
    """Pending revision 闸门错误
    
    当尝试生成 blocked_chapter 之后的内容时抛出此异常
    """
    def __init__(
        self,
        blocked_chapter: int,
        target_chapter: int,
        pending_info: PendingRevisionInfo,
        message: str = None
    ):
        self.blocked_chapter = blocked_chapter
        self.target_chapter = target_chapter
        self.pending_info = pending_info
        
        if message is None:
            message = (
                f"质量闸门阻断：第 {blocked_chapter} 章存在 pending 修订，"
                f"无法生成第 {target_chapter} 章。"
                f"请先处理 {pending_info.revision_file}"
            )
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于工具返回）"""
        result = {
            "blocked_chapter": self.blocked_chapter,
            "target_chapter": self.target_chapter,
            "revision_status_file": self.pending_info.revision_file,
            "revision_notes": self.pending_info.revision_notes,
            "triggered_by": self.pending_info.triggered_by,
            "next_actions": ["review", "generate_candidate", "apply_revision", "regen", "rollback"]
        }
        if self.pending_info.logic_review_file:
            result["logic_review_report_file"] = self.pending_info.logic_review_file
        return result


def find_pending_revisions(project_dir: str) -> List[PendingRevisionInfo]:
    """查找项目中所有 pending 状态的 revision
    
    扫描 chapters 目录下的 chapter_XXX_revision.json 文件
    
    Args:
        project_dir: 项目目录
        
    Returns:
        pending revision 信息列表，按章节号排序
    """
    chapters_dir = os.path.join(project_dir, "chapters")
    reviews_dir = os.path.join(project_dir, "reviews")
    
    if not os.path.exists(chapters_dir):
        return []
    
    pending_list = []
    revision_pattern = re.compile(r"chapter_(\d{3})_revision\.json")
    
    for filename in os.listdir(chapters_dir):
        match = revision_pattern.match(filename)
        if not match:
            continue
        
        chapter_num = int(match.group(1))
        revision_file = os.path.join(chapters_dir, filename)
        
        try:
            with open(revision_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("status") == "pending":
                # 检查是否有对应的逻辑审查报告
                logic_review_file = None
                potential_review = os.path.join(reviews_dir, f"chapter_{chapter_num:03d}_logic_review.json")
                if os.path.exists(potential_review):
                    logic_review_file = potential_review
                
                pending_list.append(PendingRevisionInfo(
                    chapter_number=chapter_num,
                    status="pending",
                    triggered_by=data.get("triggered_by", "unknown"),
                    revision_file=revision_file,
                    logic_review_file=logic_review_file,
                    revision_notes=data.get("revision_notes", "")
                ))
        except (json.JSONDecodeError, KeyError, IOError):
            # 文件格式错误或读取失败，跳过
            continue
    
    # 按章节号排序
    pending_list.sort(key=lambda x: x.chapter_number)
    return pending_list


def get_blocked_chapter(project_dir: str) -> Optional[int]:
    """获取被阻断的最小章节号
    
    Args:
        project_dir: 项目目录
        
    Returns:
        被阻断的最小章节号，如果没有 pending 则返回 None
    """
    pending_list = find_pending_revisions(project_dir)
    if not pending_list:
        return None
    return pending_list[0].chapter_number


def check_pending_revision_gate(
    project_dir: str,
    target_chapter: int
) -> None:
    """检查 pending revision 闸门
    
    如果存在 blocked_chapter 且 target_chapter > blocked_chapter，
    则抛出 PendingRevisionGateError。
    
    Args:
        project_dir: 项目目录
        target_chapter: 目标章节号
        
    Raises:
        PendingRevisionGateError: 如果被闸门阻断
    """
    pending_list = find_pending_revisions(project_dir)
    
    if not pending_list:
        return  # 没有 pending，允许通过
    
    blocked_chapter = pending_list[0].chapter_number
    
    if target_chapter > blocked_chapter:
        raise PendingRevisionGateError(
            blocked_chapter=blocked_chapter,
            target_chapter=target_chapter,
            pending_info=pending_list[0]
        )


def check_pending_revision_gate_for_range(
    project_dir: str,
    start_chapter: int,
    end_chapter: Optional[int] = None
) -> None:
    """检查 pending revision 闸门（针对章节范围）
    
    如果范围内任何章节号 > blocked_chapter，则抛出异常
    
    Args:
        project_dir: 项目目录
        start_chapter: 起始章节号
        end_chapter: 结束章节号（可选，默认与 start_chapter 相同）
        
    Raises:
        PendingRevisionGateError: 如果被闸门阻断
    """
    if end_chapter is None:
        end_chapter = start_chapter
    
    pending_list = find_pending_revisions(project_dir)
    
    if not pending_list:
        return
    
    blocked_chapter = pending_list[0].chapter_number
    
    # 检查范围内是否有章节 > blocked_chapter
    for ch in range(start_chapter, end_chapter + 1):
        if ch > blocked_chapter:
            raise PendingRevisionGateError(
                blocked_chapter=blocked_chapter,
                target_chapter=ch,
                pending_info=pending_list[0]
            )


def format_gate_error_for_user(error: PendingRevisionGateError) -> str:
    """格式化闸门错误信息供用户阅读
    
    Args:
        error: PendingRevisionGateError 异常
        
    Returns:
        格式化的错误消息
    """
    info = error.pending_info
    lines = [
        f"🛑 质量闸门阻断",
        f"",
        f"第 {error.blocked_chapter} 章存在 pending 修订，无法继续生成后续章节。",
        f"",
        f"📄 修订状态文件：{info.revision_file}",
    ]
    
    if info.logic_review_file:
        lines.append(f"📄 逻辑审查报告：{info.logic_review_file}")
    
    if info.revision_notes:
        lines.append(f"📝 修订说明：{info.revision_notes[:100]}...")
    
    lines.extend([
        f"",
        f"💡 可选操作：",
        f"  1. /review {error.blocked_chapter} - 查看审查报告",
        f"  2. /fix {error.blocked_chapter} - 生成修订候选",
        f"  3. /accept {error.blocked_chapter} - 应用修订",
        f"  4. /rollback {error.blocked_chapter} - 回滚到该章之前",
    ])
    
    return "\n".join(lines)
