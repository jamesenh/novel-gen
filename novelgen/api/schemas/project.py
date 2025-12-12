"""
项目管理相关数据模型

开发者: jamesenh
日期: 2025-12-08
"""
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    """项目基础信息"""

    name: str = Field(description="项目名称")
    created_at: str = Field(description="创建时间（ISO 格式）")
    updated_at: str = Field(description="最近修改时间（ISO 格式）")
    status: str = Field(description="当前状态：idle/running/completed/failed/unknown")


class ProjectStepState(BaseModel):
    """六步流程完成情况"""

    world: bool = Field(description="世界观是否已生成")
    theme: bool = Field(description="主题与冲突是否已生成")
    characters: bool = Field(description="角色是否已生成")
    outline: bool = Field(description="大纲是否已生成")
    chapters_plan: bool = Field(description="章节计划是否已生成")
    chapters: bool = Field(description="章节文本是否已生成")


class ProjectState(BaseModel):
    """项目状态详情"""

    steps: ProjectStepState = Field(description="基础步骤完成情况")
    checkpoint_exists: bool = Field(description="是否存在可恢复的检查点")
    chapters: List[Dict[str, Any]] = Field(default_factory=list, description="章节元数据列表")


class CreateProjectRequest(BaseModel):
    """创建项目的请求体
    
    更新: 2025-12-11 - 移除 world_description/theme_description，由独立内容生成接口管理
    """

    project_name: str = Field(description="项目名称")
    initial_chapters: int = Field(default=3, description="初始章节数")


class ProjectDetailResponse(BaseModel):
    """项目详情响应"""

    summary: ProjectSummary = Field(description="项目概要")
    settings: Dict[str, Any] = Field(description="settings.json 内容")
    state: Optional[ProjectState] = Field(default=None, description="项目当前状态")


