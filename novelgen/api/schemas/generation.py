"""
生成控制相关数据模型

开发者: jamesenh
日期: 2025-12-08
"""
from typing import Optional, Dict, Any, List, Literal

from pydantic import BaseModel, Field


class StartGenerationRequest(BaseModel):
    """启动生成的请求体"""

    stop_at: Optional[
        Literal[
            "world_creation",
            "theme_conflict_creation",
            "character_creation",
            "outline_creation",
            "chapter_planning",
        ]
    ] = Field(default=None, description="可选的停止步骤")
    verbose: bool = Field(default=False, description="是否启用详细日志")
    show_prompt: bool = Field(default=False, description="verbose 模式下是否显示提示词")


class GenerationStatusResponse(BaseModel):
    """生成任务状态"""

    status: str = Field(description="任务状态：idle/running/completed/failed/stopped")
    task_id: Optional[str] = Field(default=None, description="当前或最近任务 ID")
    detail: Optional[str] = Field(default=None, description="状态描述信息")


class ProgressSnapshot(BaseModel):
    """进度快照"""

    status: str = Field(description="状态：idle/running/completed/failed/stopped")
    current_step: Optional[str] = Field(default=None, description="当前步骤")
    current_chapter: Optional[int] = Field(default=None, description="当前章节号")
    current_scene: Optional[int] = Field(default=None, description="当前场景号")
    progress_percent: float = Field(default=0.0, description="整体进度百分比")
    message: Optional[str] = Field(default=None, description="提示信息")


class LogEntry(BaseModel):
    """生成日志条目"""

    timestamp: str = Field(description="时间戳（ISO 字符串）")
    level: Literal["INFO", "ERROR", "WARN", "DEBUG"] = Field(description="日志级别")
    message: str = Field(description="日志内容")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文元数据")


class LogsResponse(BaseModel):
    """日志列表响应"""

    items: List[LogEntry] = Field(description="日志条目列表")
    total: int = Field(description="总条目数")


