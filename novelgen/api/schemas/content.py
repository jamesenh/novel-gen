"""
内容展示相关数据模型

开发者: jamesenh
日期: 2025-12-08
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChapterMeta(BaseModel):
    """章节元数据"""

    chapter_number: int = Field(description="章节编号")
    chapter_title: str = Field(description="章节标题")
    scenes_count: int = Field(description="场景数量")
    total_words: int = Field(description="总字数")
    status: str = Field(description="状态：planned/partial/completed")


class ChapterContentResponse(BaseModel):
    """章节内容响应"""

    chapter_number: int = Field(description="章节编号")
    chapter_title: str = Field(description="章节标题")
    scenes: List[Dict[str, Any]] = Field(description="场景列表，按顺序排列")


class GenericContentPayload(BaseModel):
    """通用内容更新载荷，接受任意键值"""

    model_config = {"extra": "allow"}


class SceneUpdate(BaseModel):
    """场景更新模型"""

    scene_number: int = Field(description="场景编号")
    content: str = Field(description="场景内容")
    word_count: Optional[int] = Field(default=None, description="字数，可省略自动计算")


class ChapterUpdateRequest(BaseModel):
    """章节更新请求"""

    chapter_title: Optional[str] = Field(default=None, description="章节标题（可选，不传则沿用原值）")
    scenes: List[SceneUpdate] = Field(default_factory=list, description="场景列表")


