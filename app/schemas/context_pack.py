"""Context Pack schema（用于生成链路与插件复用的上下文包）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import BaseArtifact


class ContextSource(BaseModel):
    """可追溯的上下文来源条目。"""

    model_config = {"extra": "allow"}

    source_id: str = Field(description="稳定来源 ID（如 file:world.json）")
    source_path: str = Field(description="来源路径（相对 projects/<project>/）")
    doc_type: str = Field(
        description="文档类型（world/characters/outline/chapter/...）"
    )
    chapter_id: Optional[int] = Field(
        default=None, description="若来源与章节相关则给出章节号"
    )
    score: Optional[float] = Field(default=None, description="检索得分（越大越相关）")
    excerpt: str = Field(default="", description="用于可视化/调试的摘录")


class ContextPack(BaseArtifact):
    """context_pack 的稳定结构（放入 state['context_pack'] 并传入插件）。"""

    project_name: str = Field(description="项目名")
    chapter_id: int = Field(description="当前章节号")
    query: str = Field(
        default="", description="检索 query（通常来自 prompt 或 question）"
    )

    required: Dict[str, Any] = Field(
        default_factory=dict,
        description="必带上下文（deterministic）：bible/outline/memory/open_issues 等",
    )
    retrieved: List[ContextSource] = Field(
        default_factory=list,
        description="检索结果片段（可追溯 sources）",
    )
