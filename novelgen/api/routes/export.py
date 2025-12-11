"""
导出 API 路由

开发者: jamesenh
日期: 2025-12-08
"""
import os

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from novelgen.services import export_service, project_service

router = APIRouter(prefix="/api/projects/{name}", tags=["export"])


def _ensure_project(name: str):
    project_dir = os.path.join(project_service.PROJECTS_ROOT, name)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")


@router.get("/export/txt")
async def export_full_txt(name: str):
    """导出全书 TXT"""
    _ensure_project(name)
    try:
        path = export_service.export_full_txt(name)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    filename = os.path.basename(path)
    return FileResponse(path, media_type="text/plain; charset=utf-8", filename=filename)


@router.get("/export/txt/{chapter_num}")
async def export_chapter_txt(name: str, chapter_num: int):
    """导出单章 TXT"""
    _ensure_project(name)
    try:
        path = export_service.export_chapter_txt(name, chapter_num)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    filename = os.path.basename(path)
    return FileResponse(path, media_type="text/plain; charset=utf-8", filename=filename)


@router.get("/export/md")
async def export_full_md(name: str):
    """导出全书 Markdown"""
    _ensure_project(name)
    try:
        path = export_service.export_markdown(name)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    filename = os.path.basename(path)
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename=filename)


@router.get("/export/md/{chapter_num}")
async def export_chapter_md(name: str, chapter_num: int):
    """导出单章 Markdown"""
    _ensure_project(name)
    try:
        path = export_service.export_markdown(name, chapter_num=chapter_num)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    filename = os.path.basename(path)
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename=filename)


@router.get("/export/json")
async def export_full_json(name: str):
    """导出全书 JSON"""
    _ensure_project(name)
    try:
        path = export_service.export_json(name)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    filename = os.path.basename(path)
    return FileResponse(path, media_type="application/json", filename=filename)


@router.get("/export/json/{chapter_num}")
async def export_chapter_json(name: str, chapter_num: int):
    """导出单章 JSON"""
    _ensure_project(name)
    try:
        path = export_service.export_json(name, chapter_num=chapter_num)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    filename = os.path.basename(path)
    return FileResponse(path, media_type="application/json", filename=filename)


