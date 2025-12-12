"""
内容展示相关数据模型

开发者: jamesenh
日期: 2025-12-08
更新: 2025-12-11 - 增加内容生成请求/响应模型
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ==================== 内容生成相关 ====================


class ContentGenerateRequest(BaseModel):
    """内容生成请求"""
    
    target: Literal["world", "theme", "characters", "outline"] = Field(
        description="目标类型：world/theme/characters/outline"
    )
    user_prompt: str = Field(default="", description="用户输入的提示/描述")
    num_variants: int = Field(default=3, ge=1, le=5, description="候选数量（1-5，仅 world/theme 使用）")
    num_characters: Optional[int] = Field(
        default=None,
        ge=3,
        le=12,
        description="角色生成数量（仅 target=characters 时使用，未提供则使用默认值，范围 3-12）",
    )
    num_chapters: Optional[int] = Field(
        default=None,
        ge=2,
        le=30,
        description="大纲章节数量（仅 target=outline 时使用，未提供则使用 settings.initial_chapters，范围 2-30）",
    )
    expand: bool = Field(default=False, description="是否先扩写提示（仅 world 有效）")


class ContentVariant(BaseModel):
    """单个内容候选"""
    
    variant_id: str = Field(description="候选ID，如 variant_1")
    style_tag: str = Field(description="风格标签")
    brief_description: str = Field(description="简要描述")
    payload: Dict[str, Any] = Field(description="完整内容 JSON")


class ContentGenerateResponse(BaseModel):
    """内容生成响应"""
    
    target: str = Field(description="目标类型")
    variants: List[ContentVariant] = Field(description="候选列表")
    generated_at: str = Field(description="生成时间")


# ==================== 章节元数据 ====================


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


