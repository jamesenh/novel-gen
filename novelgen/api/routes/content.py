"""
内容展示与编辑 API 路由

开发者: jamesenh
日期: 2025-12-08
更新: 2025-12-11 - 增加内容生成接口（LLM 多候选）
"""
import glob
import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from novelgen.api.schemas.content import (
    ChapterContentResponse,
    ChapterMeta,
    ChapterUpdateRequest,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ContentVariant,
    GenericContentPayload,
)
from novelgen.models import GeneratedChapter, GeneratedScene
from novelgen.services import project_service

logger = logging.getLogger(__name__)

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


def _load_json(path: str):
    """加载 JSON 文件，不存在返回 None"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== 内容生成接口 ====================


@router.post("/content/generate", response_model=ContentGenerateResponse)
async def generate_content(name: str, body: ContentGenerateRequest):
    """
    调用 LLM 生成内容草稿（支持多候选）
    
    - world: 世界观多候选生成
    - theme: 主题冲突多候选生成（需先有 world.json）
    - characters: 角色生成（单候选，需 world + theme，可指定 num_characters）
    - outline: 大纲生成（单候选，需 world + theme + characters）
    """
    project_dir = _ensure_project(name)
    settings_path = os.path.join(project_dir, "settings.json")
    settings = _load_json(settings_path) or {}
    
    target = body.target
    user_prompt = body.user_prompt.strip()
    num_variants = body.num_variants
    num_characters = body.num_characters
    num_chapters = body.num_chapters
    
    try:
        if target == "world":
            variants = await _generate_world_variants(
                project_dir, settings, user_prompt, num_variants, body.expand
            )
        elif target == "theme":
            variants = await _generate_theme_variants(
                project_dir, settings, user_prompt, num_variants
            )
        elif target == "characters":
            variants = await _generate_characters_variants(
                project_dir, settings, num_characters
            )
        elif target == "outline":
            variants = await _generate_outline_variants(
                project_dir, settings, num_chapters
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的目标类型: {target}"
            )
        
        return ContentGenerateResponse(
            target=target,
            variants=variants,
            generated_at=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"内容生成失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {str(e)}"
        )


async def _generate_world_variants(
    project_dir: str,
    settings: dict,
    user_prompt: str,
    num_variants: int,
    expand: bool,
) -> List[ContentVariant]:
    """生成世界观多候选
    
    更新: 2025-12-11 - 移除 settings.world_description 回退，仅接受 user_prompt
    """
    from novelgen.chains.world_chain import generate_world_variants, expand_world_prompt
    
    # 必须提供 user_prompt
    if not user_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供世界观描述（user_prompt）"
        )
    prompt = user_prompt
    
    result = generate_world_variants(
        user_input=prompt,
        num_variants=num_variants,
        expand=expand,
        verbose=False,
    )
    
    variants = []
    for v in result.variants:
        variants.append(ContentVariant(
            variant_id=v.variant_id,
            style_tag=v.style_tag,
            brief_description=v.brief_description,
            payload=v.world_setting.model_dump(),
        ))
    return variants


async def _generate_theme_variants(
    project_dir: str,
    settings: dict,
    user_prompt: str,
    num_variants: int,
) -> List[ContentVariant]:
    """生成主题冲突多候选（需要已有 world.json）
    
    更新: 2025-12-11 - 移除 settings.theme_description 回退，user_prompt 可选（留空则由 AI 自动推断）
    """
    from novelgen.chains.theme_conflict_chain import generate_theme_conflict_variants
    from novelgen.models import WorldSetting
    
    world_path = os.path.join(project_dir, "world.json")
    world_data = _load_json(world_path)
    if not world_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先生成世界观（world.json 不存在）"
        )
    
    world_setting = WorldSetting(**world_data)
    # user_prompt 可选，留空则由 AI 根据世界观自动推断主题
    direction = user_prompt or None
    
    result = generate_theme_conflict_variants(
        world_setting=world_setting,
        user_direction=direction if direction else None,
        num_variants=num_variants,
        verbose=False,
    )
    
    variants = []
    for v in result.variants:
        variants.append(ContentVariant(
            variant_id=v.variant_id,
            style_tag=v.style_tag,
            brief_description=v.brief_description,
            payload=v.theme_conflict.model_dump(),
        ))
    return variants


async def _generate_characters_variants(
    project_dir: str,
    settings: dict,
    num_characters: Optional[int],
) -> List[ContentVariant]:
    """生成角色（单候选，需要 world + theme，支持指定生成角色数量）"""
    from novelgen.chains.characters_chain import generate_characters
    from novelgen.models import WorldSetting, ThemeConflict
    
    world_path = os.path.join(project_dir, "world.json")
    theme_path = os.path.join(project_dir, "theme_conflict.json")
    
    world_data = _load_json(world_path)
    theme_data = _load_json(theme_path)
    
    if not world_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先生成世界观（world.json 不存在）"
        )
    if not theme_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先生成主题冲突（theme_conflict.json 不存在）"
        )
    
    world_setting = WorldSetting(**world_data)
    theme_conflict = ThemeConflict(**theme_data)
    
    try:
        result = generate_characters(
            world_setting=world_setting,
            theme_conflict=theme_conflict,
            num_characters=num_characters,
            verbose=False,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    
    # 角色暂时只生成单候选
    return [ContentVariant(
        variant_id="variant_1",
        style_tag="默认方案",
        brief_description=f"主角：{result.protagonist.name}，{result.protagonist.role}",
        payload=result.model_dump(),
    )]


async def _generate_outline_variants(
    project_dir: str,
    settings: dict,
    num_chapters: Optional[int] = None,
) -> List[ContentVariant]:
    """生成大纲（单候选，需要 world + theme + characters）
    
    Args:
        project_dir: 项目目录
        settings: 项目设置
        num_chapters: 章节数量（未提供则使用 settings.initial_chapters）
    """
    from novelgen.chains.outline_chain import generate_initial_outline
    from novelgen.models import WorldSetting, ThemeConflict, CharactersConfig

    world_path = os.path.join(project_dir, "world.json")
    theme_path = os.path.join(project_dir, "theme_conflict.json")
    characters_path = os.path.join(project_dir, "characters.json")

    world_data = _load_json(world_path)
    theme_data = _load_json(theme_path)
    characters_data = _load_json(characters_path)

    if not world_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先生成世界观（world.json 不存在）"
        )
    if not theme_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先生成主题冲突（theme_conflict.json 不存在）"
        )
    if not characters_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先生成角色（characters.json 不存在）"
        )

    world_setting = WorldSetting(**world_data)
    theme_conflict = ThemeConflict(**theme_data)
    characters = CharactersConfig(**characters_data)

    # 优先使用请求参数，否则使用 settings 中的配置
    initial_chapters = num_chapters if num_chapters is not None else settings.get("initial_chapters", 5)

    result = generate_initial_outline(
        world_setting=world_setting,
        theme_conflict=theme_conflict,
        characters=characters,
        initial_chapters=initial_chapters,
        verbose=False,
    )
    
    # 大纲暂时只生成单候选
    chapter_count = len(result.chapters)
    return [ContentVariant(
        variant_id="variant_1",
        style_tag="默认方案",
        brief_description=f"故事前提：{result.story_premise[:80]}...（{chapter_count}章）",
        payload=result.model_dump(),
    )]


# ==================== 内容读取接口 ====================


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


@router.get("/theme_conflict")
async def get_theme_conflict(name: str):
    """主题冲突内容"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "theme_conflict.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="theme_conflict.json 不存在")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.put("/theme_conflict")
async def update_theme_conflict(name: str, body: GenericContentPayload):
    """更新主题冲突"""
    project_dir = _ensure_project(name)
    path = os.path.join(project_dir, "theme_conflict.json")
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


