"""
回滚 API 路由

开发者: jamesenh
日期: 2025-12-08
"""
import glob
import os
import shutil
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from novelgen.services import generation_service, project_service

router = APIRouter(prefix="/api/projects/{name}", tags=["rollback"])

# 定义步骤顺序，便于“及之后”清理
STEP_ORDER = [
    "world_creation",
    "theme_conflict_creation",
    "character_creation",
    "outline_creation",
    "chapter_planning",
    "chapter_generation",
]

STEP_OUTPUTS: Dict[str, List[str]] = {
    "world_creation": ["world.json", "world_variants.json"],
    "theme_conflict_creation": ["theme_conflict.json", "theme_conflict_variants.json"],
    "character_creation": ["characters.json"],
    "outline_creation": ["outline.json"],
    "chapter_planning": [os.path.join("chapters", "*_plan.json")],
    "chapter_generation": [os.path.join("chapters", "chapter_*.json"), os.path.join("chapters", "scene_*.json")],
}


class RollbackRequest(BaseModel):
    """回滚请求体"""

    step: Optional[str] = Field(
        default=None, description="步骤名，例如 world_creation/theme_conflict_creation/character_creation/outline_creation/chapter_planning"
    )
    chapter: Optional[int] = Field(default=None, description="回滚到章节号（含此章节后全部删除）")
    scene: Optional[int] = Field(default=None, description="回滚到场景号（仅在指定章节时有效）")


def _ensure_project_dir(name: str) -> str:
    project_dir = os.path.join(project_service.PROJECTS_ROOT, name)
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project_dir


@router.post("/rollback")
async def rollback_project(name: str, body: RollbackRequest):
    """回滚项目生成产物"""
    project_dir = _ensure_project_dir(name)
    deleted_files: Set[str] = set()

    if body.step:
        deleted_files.update(_rollback_by_step(project_dir, body.step))
    if body.chapter is not None:
        deleted_files.update(_rollback_chapters(project_dir, body.chapter, body.scene))

    # 清理 Redis 状态（active/progress/logs）
    cleared_memories = generation_service.reset_runtime_state(name, message="已回滚")

    return {"deleted_files": len(deleted_files), "cleared_memories": cleared_memories, "files": sorted(deleted_files)}


def _rollback_by_step(project_dir: str, step: str) -> List[str]:
    """根据步骤删除该步骤及其后续步骤的输出文件"""
    if step not in STEP_ORDER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的步骤名")

    start_index = STEP_ORDER.index(step)
    targets: List[str] = []
    for s in STEP_ORDER[start_index:]:
        targets.extend(STEP_OUTPUTS.get(s, []))

    deleted: List[str] = []
    for target in targets:
        absolute_glob = target if os.path.isabs(target) else os.path.join(project_dir, target)
        matched = glob.glob(absolute_glob)
        if matched:
            for path in matched:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    deleted.append(path)
                elif os.path.exists(path):
                    os.remove(path)
                    deleted.append(path)
        else:
            if os.path.exists(absolute_glob):
                os.remove(absolute_glob)
                deleted.append(absolute_glob)
    return deleted


def _rollback_chapters(project_dir: str, chapter_num: int, scene_num: Optional[int]) -> List[str]:
    """回滚章节或场景（保留章节计划文件）"""
    deleted: List[str] = []
    chapters_dir = os.path.join(project_dir, "chapters")
    if not os.path.exists(chapters_dir):
        return deleted

    # 删除章节文件（含目标及之后）
    for file in glob.glob(os.path.join(chapters_dir, "chapter_*.json")):
        try:
            num = int(os.path.basename(file).split("_")[1])
        except Exception:
            continue
        if num >= chapter_num:
            os.remove(file)
            deleted.append(file)

    # 删除场景文件（目标章节及之后的场景）
    for file in glob.glob(os.path.join(chapters_dir, "scene_*.json")):
        filename = os.path.basename(file)
        parts = filename.split("_")
        if len(parts) < 3:
            continue
        try:
            ch_num = int(parts[1])
            scene_index = int(parts[2].split(".")[0])
        except Exception:
            continue
        if ch_num > chapter_num or (ch_num == chapter_num and (scene_num is None or scene_index >= scene_num)):
            os.remove(file)
            deleted.append(file)

    return deleted


