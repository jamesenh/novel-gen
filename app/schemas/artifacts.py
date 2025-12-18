"""持久化资产文件的 schemas。

定义的 schemas:
- ChapterReportEntry: consistency_reports.json 中每章的条目
- ConsistencyReportsFile: consistency_reports.json 完整文件
- ChapterMemoryEntry: chapter_memory.json 中每章的条目
- ChapterMemoryFile: chapter_memory.json 完整文件
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseArtifact
from .issues import Issue


class ChapterReportEntry(BaseModel):
    """consistency_reports.json 中每章节的条目。"""

    model_config = {"extra": "allow"}

    chapter_id: int = Field(description="章节编号")
    issues: List[Issue] = Field(
        default_factory=list,
        description="该章节的问题列表",
    )
    blocker_count: int = Field(default=0, description="blocker 级别问题数")
    major_count: int = Field(default=0, description="major 级别问题数")
    minor_count: int = Field(default=0, description="minor 级别问题数")
    updated_at: str = Field(description="最后更新时间 (ISO 格式)")
    major_over_threshold: bool = Field(
        default=False, description="major_count 是否超过 qa_major_max（用于提示）"
    )
    qa_major_max: Optional[int] = Field(
        default=None, description="major 阈值（用于提示）"
    )


class ConsistencyReportsFile(BaseArtifact):
    """consistency_reports.json 完整文件的 schema。"""

    chapters: Dict[str, ChapterReportEntry] = Field(
        default_factory=dict,
        description="按章节 ID 索引的报告条目",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="文件最后更新时间 (ISO 格式)",
    )


class ChapterMemoryEntry(BaseModel):
    """chapter_memory.json 中每章节的条目。"""

    model_config = {"extra": "allow"}

    chapter_id: int = Field(description="章节编号")
    title: str = Field(default="", description="章节标题")
    scene_count: int = Field(default=0, description="场景数量")
    word_count: int = Field(default=0, description="字数")
    updated_at: str = Field(description="最后更新时间 (ISO 格式)")


class ChapterMemoryFile(BaseArtifact):
    """chapter_memory.json 完整文件的 schema。"""

    chapters: Dict[str, ChapterMemoryEntry] = Field(
        default_factory=dict,
        description="按章节 ID 索引的记忆条目",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="文件最后更新时间 (ISO 格式)",
    )
