"""
生成控制 API 路由

开发者: jamesenh
日期: 2025-12-08
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from novelgen.api.schemas.common import MessageResponse
from novelgen.api.schemas.generation import (
    GenerationStatusResponse,
    LogsResponse,
    ProgressSnapshot,
    StartGenerationRequest,
)
from novelgen.services import generation_service

router = APIRouter(prefix="/api/projects/{name}", tags=["generation"])


@router.post("/generate", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_generation(name: str, body: StartGenerationRequest):
    """开始生成"""
    try:
        task_id = generation_service.start_generation(
            project_name=name,
            stop_at=body.stop_at,
            verbose=body.verbose,
            show_prompt=body.show_prompt,
        )
        return MessageResponse(message="任务已提交", task_id=task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/generate/resume", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def resume_generation(name: str):
    """恢复生成"""
    try:
        task_id = generation_service.resume_generation(project_name=name)
        return MessageResponse(message="恢复任务已提交", task_id=task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/generate/stop", response_model=MessageResponse)
async def stop_generation(name: str):
    """停止生成"""
    task_id = generation_service.stop_generation(project_name=name)
    if not task_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="没有运行中的任务")
    return MessageResponse(message="任务已停止", task_id=task_id)


@router.get("/generate/status", response_model=GenerationStatusResponse)
async def generation_status(name: str):
    """任务状态"""
    status_payload = generation_service.get_status(project_name=name)
    return GenerationStatusResponse(**status_payload)


@router.get("/generate/progress", response_model=ProgressSnapshot)
async def generation_progress(name: str):
    """HTTP 进度查询"""
    progress = generation_service.read_progress(project_name=name)
    return ProgressSnapshot(**progress)


@router.get("/generate/logs", response_model=LogsResponse)
async def generation_logs(name: str, limit: int = Query(default=50, ge=1, le=200)):
    """读取日志"""
    items = generation_service.read_logs(project_name=name, limit=limit)
    return LogsResponse(items=items, total=len(items))


