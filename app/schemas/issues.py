"""问题和审计报告 schemas。

定义的 schemas:
- Issue: 单个审计问题
- AuditReport: 章节的问题集合
"""

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field, model_validator


class Severity(str, Enum):
    """问题严重程度级别。"""

    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"


class Category(str, Enum):
    """问题类别。"""

    WORLD_RULE = "world_rule"
    CHARACTER = "character"
    TIMELINE = "timeline"
    KNOWLEDGE = "knowledge"
    THREAD = "thread"
    POV_STYLE = "pov_style"


class Issue(BaseModel):
    """单个一致性问题的 schema（插件输出 / 报告写入使用）。

    注意：Issue 本身不强制携带 `schema_version/generated_at/generator` 元数据，
    元数据由顶层持久化文件（如 consistency_reports.json）提供。
    """

    model_config = {"extra": "ignore"}

    id: str = Field(description="Issue identifier (e.g., 'I-001')")
    severity: Severity = Field(description="Issue severity")
    category: Category = Field(description="Issue category")
    summary: str = Field(description="Human-readable summary")
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Evidence including chapter quotes and bible references",
    )
    fix_instructions: str = Field(
        default="",
        description="Actionable fix guidance",
    )
    fix_options: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Alternative fix strategies",
    )

    @model_validator(mode="after")
    def _blocker_requires_fix_instructions(self) -> "Issue":
        if self.severity == Severity.BLOCKER and not self.fix_instructions:
            raise ValueError("Blocker issues MUST include non-empty fix_instructions")
        return self


class AuditReport(BaseModel):
    """consistency_reports.json 的 schema（每章节部分）。"""

    model_config = {"extra": "ignore"}

    chapter_id: int = Field(description="Chapter number")
    issues: List[Issue] = Field(default_factory=list, description="List of issues")
    updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Suggested updates to timeline/threads/facts",
    )

    @property
    def blocker_count(self) -> int:
        """统计 blocker 级别问题数。"""
        return sum(1 for i in self.issues if i.severity == Severity.BLOCKER)

    @property
    def major_count(self) -> int:
        """统计 major 级别问题数。"""
        return sum(1 for i in self.issues if i.severity == Severity.MAJOR)

    @property
    def minor_count(self) -> int:
        """统计 minor 级别问题数。"""
        return sum(1 for i in self.issues if i.severity == Severity.MINOR)
