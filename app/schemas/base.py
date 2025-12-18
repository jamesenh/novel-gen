"""包含必要元数据字段的基础 schema 定义。

所有结构化 JSON 资产必须包含:
- schema_version: schema 版本
- generated_at: 生成时的 ISO 时间戳
- generator: 模型/版本/运行信息
"""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class ArtifactMetadata(BaseModel):
    """所有持久化资产的必要元数据。"""

    schema_version: str = Field(
        default="1.0",
        description="Schema version for this artifact type",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when this artifact was generated",
    )
    generator: str = Field(
        default="novel-gen-v2",
        description="Generator identifier (model/version/run_id)",
    )


class BaseArtifact(ArtifactMetadata):
    """所有资产 schema 的基类。"""

    model_config = {"extra": "allow"}  # 允许额外字段以提高灵活性


def add_metadata(
    data: Dict[str, Any],
    schema_version: str = "1.0",
    generator: str = "novel-gen-v2",
) -> Dict[str, Any]:
    """向字典添加必要的元数据字段。

    Args:
        data: 资产数据字典。
        schema_version: schema 版本字符串。
        generator: 生成器标识符。

    Returns:
        添加了元数据字段的数据字典。
    """
    return {
        "schema_version": schema_version,
        "generated_at": datetime.now().isoformat(),
        "generator": generator,
        **data,
    }
