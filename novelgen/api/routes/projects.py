"""
项目管理 API 路由

开发者: jamesenh
日期: 2025-12-08
"""
import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status

from novelgen.api.schemas.project import (
    CreateProjectRequest,
    ProjectDetailResponse,
    ProjectState,
    ProjectSummary,
)
from novelgen.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectSummary])
async def list_projects_api():
    """项目列表"""
    projects = project_service.list_projects()
    return [ProjectSummary(**p) for p in projects]


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_project_api(body: CreateProjectRequest):
    """创建项目"""
    project_dir = os.path.join(project_service.PROJECTS_ROOT, body.project_name)
    if os.path.exists(project_dir):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="项目已存在")

    settings = project_service.create_project(body.model_dump())
    summary = ProjectSummary(
        name=body.project_name,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        status="idle",
    )
    state = project_service.load_project_state(body.project_name)
    return ProjectDetailResponse(summary=summary, settings=settings, state=state)


@router.get("/{name}", response_model=ProjectDetailResponse)
async def get_project_detail(name: str):
    """项目详情"""
    project_dir = os.path.join(project_service.PROJECTS_ROOT, name)
    settings_path = os.path.join(project_dir, "settings.json")
    if not os.path.exists(settings_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    settings = project_service.load_settings(name)
    stat = os.stat(settings_path)
    updated_at = project_service.get_project_last_modified(name).isoformat()
    state = project_service.load_project_state(name)
    summary = ProjectSummary(
        name=name,
        created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        updated_at=updated_at,
        status="completed" if state.steps.chapters else "idle",
    )
    return ProjectDetailResponse(summary=summary, settings=settings, state=state)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_api(name: str):
    """删除项目"""
    project_dir = os.path.join(project_service.PROJECTS_ROOT, name)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    project_service.delete_project(name)
    return


@router.get("/{name}/state", response_model=ProjectState)
async def project_state_api(name: str):
    """获取项目状态"""
    project_dir = os.path.join(project_service.PROJECTS_ROOT, name)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project_service.load_project_state(name)


