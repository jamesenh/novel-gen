"""
内容展示与编辑 API 路由

开发者: jamesenh
日期: 2025-12-08
"""
import glob
import json
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from novelgen.api.schemas.content import (
    ChapterContentResponse,
    ChapterMeta,
    ChapterUpdateRequest,
    GenericContentPayload,
)
from novelgen.models import GeneratedChapter, GeneratedScene
from novelgen.services import project_service

router = APIRouter(prefix="/api/projects/{name}", tags=["content"])


def _ensure_project(name: str) -> str:
    project_dir = os.path.join(project_service.PROJECTS_ROOT, name)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project_dir


def _write_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@router.get("/world")
async def get_world(name: str):
    """世界观内容"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "world.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="world.json 不存在")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.put("/world")
async def update_world(name: str, body: GenericContentPayload):
    """更新世界观"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "world.json")
    _write_json(path, body.model_dump())
    return {"updated": True}


@router.get("/characters")
async def get_characters(name: str):
    """角色内容"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "characters.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="characters.json 不存在")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.put("/characters")
async def update_characters(name: str, body: GenericContentPayload):
    """更新角色"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "characters.json")
    _write_json(path, body.model_dump())
    return {"updated": True}


@router.get("/outline")
async def get_outline(name: str):
    """大纲内容"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "outline.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outline.json 不存在")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.put("/outline")
async def update_outline(name: str, body: GenericContentPayload):
    """更新大纲"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "outline.json")
    _write_json(path, body.model_dump())
    return {"updated": True}


@router.get("/chapters", response_model=List[ChapterMeta])
async def list_chapters(name: str):
    """章节列表"""
    project_dir = _ensure_project(name)
    chapter_files = sorted(glob.glob(os.path.join(project_dir, "chapters", "chapter_*.json")))
    chapters: List[ChapterMeta] = []
    for path in chapter_files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        try:
            chapter = GeneratedChapter(**data)
            chapters.append(
                ChapterMeta(
                    chapter_number=chapter.chapter_number,
                    chapter_title=chapter.chapter_title,
                    scenes_count=len(chapter.scenes),
                    total_words=chapter.total_words,
                    status="completed",
                )
            )
        except Exception:
            continue
    return chapters


@router.get("/chapters/{num}", response_model=ChapterContentResponse)
async def get_chapter(name: str, num: int):
    """章节内容"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "chapters", f"chapter_{num:03d}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    chapter = GeneratedChapter(**data)
    scenes = [scene.model_dump() for scene in chapter.scenes]
    return ChapterContentResponse(
        chapter_number=chapter.chapter_number,
        chapter_title=chapter.chapter_title,
        scenes=scenes,
    )


@router.put("/chapters/{num}")
async def update_chapter(name: str, num: int, body: ChapterUpdateRequest):
    """更新章节或场景内容"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "chapters", f"chapter_{num:03d}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")

    with open(path, "r", encoding="utf-8") as f:
        origin = json.load(f)

    chapter_title = body.chapter_title or origin.get("chapter_title")
    scenes_payload = body.scenes or origin.get("scenes", [])

    scenes: List[GeneratedScene] = []
    for scene in scenes_payload:
        content = scene.get("content", "")
        word_count = scene.get("word_count") or len(content)
        scenes.append(
            GeneratedScene(
                scene_number=int(scene.get("scene_number")),
                content=content,
                word_count=int(word_count),
            )
        )
    total_words = sum(s.word_count for s in scenes)
    chapter = GeneratedChapter(
        chapter_number=num,
        chapter_title=chapter_title,
        scenes=scenes,
        total_words=total_words,
    )
    _write_json(path, chapter.model_dump())
    return {"updated": True, "total_words": total_words}


@router.delete("/chapters/{num}")
async def delete_chapter_or_scene(name: str, num: int, scene: Optional[int] = None):
    """删除章节或场景"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "chapters", f"chapter_{num:03d}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")

    deleted_files: List[str] = []
    if scene is None:
        # 删除整章
        os.remove(path)
        deleted_files.append(path)
        for file in glob.glob(os.path.join(project_dir, "chapters", f"scene_{num:03d}_*.json")):
            os.remove(file)
            deleted_files.append(file)
        return {"deleted": deleted_files}

    # 删除指定场景
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    chapter = GeneratedChapter(**data)
    new_scenes = [s for s in chapter.scenes if s.scene_number != scene]
    scene_file = os.path.join(project_dir, "chapters", f"scene_{num:03d}_{scene:03d}.json")
    if os.path.exists(scene_file):
        os.remove(scene_file)
        deleted_files.append(scene_file)

    if not new_scenes:
        os.remove(path)
        deleted_files.append(path)
        return {"deleted": deleted_files}

    total_words = sum(s.word_count for s in new_scenes)
    updated_chapter = GeneratedChapter(
        chapter_number=num,
        chapter_title=chapter.chapter_title,
        scenes=new_scenes,
        total_words=total_words,
    )
    _write_json(path, updated_chapter.model_dump())
    deleted_files.append(f"scene_{scene}")
    return {"deleted": deleted_files, "total_words": total_words}


