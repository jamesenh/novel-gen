"""章节相关 schemas。

定义的 schemas:
- ChapterPlan: 单章计划
- ChapterContent: 生成的章节内容
"""

from typing import Any, Dict, List

from pydantic import Field

from .base import BaseArtifact


class ChapterPlan(BaseArtifact):
    """chapter_XXX_plan.json 的 schema。"""

    chapter_id: int = Field(description="Chapter number (1-indexed)")
    pov: str = Field(default="", description="Point of view character")
    goal: str = Field(default="", description="Chapter goal")
    conflict: str = Field(default="", description="Main conflict")
    turn: str = Field(default="", description="Key turn/twist")
    reveal: List[str] = Field(default_factory=list, description="Information reveals")
    threads_advance: List[str] = Field(
        default_factory=list,
        description="Thread IDs to advance",
    )
    must_include: List[str] = Field(
        default_factory=list,
        description="Must-include elements",
    )
    must_avoid: List[str] = Field(
        default_factory=list,
        description="Must-avoid elements",
    )
    scenes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Scene breakdowns",
    )


class Scene(BaseArtifact):
    """章节内单个场景的 schema。"""

    scene_id: str = Field(description="Scene identifier (e.g., '1_1')")
    location: str = Field(default="", description="Scene location")
    characters: List[str] = Field(
        default_factory=list, description="Characters present"
    )
    purpose: str = Field(default="", description="Scene purpose")
    content: str = Field(default="", description="Scene content text")


class ChapterContent(BaseArtifact):
    """chapter_XXX.json 的 schema。"""

    chapter_id: int = Field(description="Chapter number (1-indexed)")
    title: str = Field(default="", description="Chapter title")
    scenes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Scene contents",
    )
    word_count: int = Field(default=0, description="Total word count")
