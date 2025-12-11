"""
通用 API 数据模型

开发者: jamesenh
日期: 2025-12-08
"""
from typing import Optional

from pydantic import BaseModel, Field


class APIError(BaseModel):
    """统一错误响应格式"""

    detail: str = Field(description="错误描述")
    error_code: str = Field(default="ERROR", description="错误编码，便于前端分类处理")


class MessageResponse(BaseModel):
    """通用消息响应"""

    message: str = Field(description="提示信息")
    task_id: Optional[str] = Field(default=None, description="相关任务 ID（如有）")


