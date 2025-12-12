"""
项目管理服务

封装项目的创建、查询与状态计算逻辑，供 API 与任务层复用。

开发者: jamesenh
日期: 2025-12-08
更新: 2025-12-11 - 增强删除逻辑，支持 Redis/Mem0/向量存储清理
"""
import glob
import json
import logging
import os
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional

from novelgen.models import GeneratedChapter, Settings
from novelgen.api.schemas.project import ProjectStepState, ProjectState

logger = logging.getLogger(__name__)

PROJECTS_ROOT = os.getenv("NOVELGEN_PROJECTS_DIR", "projects")


def _load_json(filepath: str):
    """加载 JSON 文件，读取失败返回 None"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def _get_last_modified(project_dir: str) -> datetime:
    """计算项目目录内的最近修改时间"""
    latest_ts = None
    for root, _, files in os.walk(project_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                stat = os.stat(filepath)
            except FileNotFoundError:
                # 文件在遍历过程中被删除时忽略
                continue
            if latest_ts is None or stat.st_mtime > latest_ts:
                latest_ts = stat.st_mtime
    if latest_ts is None:
        return datetime.utcnow()
    return datetime.fromtimestamp(latest_ts)


def get_project_last_modified(project_name: str) -> datetime:
    """获取指定项目的最近修改时间"""
    project_dir = os.path.join(PROJECTS_ROOT, project_name)
    return _get_last_modified(project_dir)


def list_projects() -> List[Dict[str, Any]]:
    """
    列出所有项目

    Returns:
        包含 name、created_at、updated_at、status 的项目列表
    """
    projects = []
    if not os.path.exists(PROJECTS_ROOT):
        return projects

    for entry in os.listdir(PROJECTS_ROOT):
        project_dir = os.path.join(PROJECTS_ROOT, entry)
        settings_path = os.path.join(project_dir, "settings.json")
        if not os.path.isdir(project_dir) or not os.path.exists(settings_path):
            continue

        stat = os.stat(settings_path)
        created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        updated_at = _get_last_modified(project_dir).isoformat()
        step_state = _calculate_step_state(project_dir)
        status = "completed" if step_state.chapters else "running" if step_state.outline else "idle"
        projects.append(
            {
                "name": entry,
                "created_at": created_at,
                "updated_at": updated_at,
                "status": status,
            }
        )
    return sorted(projects, key=lambda p: p["created_at"], reverse=True)


def create_project(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建新项目

    Args:
        data: 请求体字段

    Returns:
        创建后的 settings.json 内容
        
    更新: 2025-12-11 - 移除 world_description/theme_description，由独立内容生成接口管理
    """
    project_name = data["project_name"]
    project_dir = os.path.join(PROJECTS_ROOT, project_name)
    os.makedirs(os.path.join(project_dir, "chapters"), exist_ok=True)

    settings = Settings(
        project_name=project_name,
        author="Jamesenh",
        initial_chapters=data.get("initial_chapters", 3),
        max_chapters=max(data.get("initial_chapters", 3), 50),
    )
    settings_path = os.path.join(project_dir, "settings.json")
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
    return settings.model_dump()


def delete_project(project_name: str) -> Dict[str, Any]:
    """
    删除项目及其所有关联数据
    
    清理顺序：
    1. 停止活跃的生成任务
    2. 清理 Redis 运行时状态（进度、日志、活跃任务）
    3. 清理 Mem0 记忆（如果启用）
    4. 删除项目专属向量存储目录（如果位于项目目录内）
    5. 删除项目文件目录
    
    Args:
        project_name: 项目名称
        
    Returns:
        包含清理结果的字典：
        - deleted_files: 是否删除了项目目录
        - cleared_redis: 清理的 Redis 键数量
        - cleared_mem0: 是否清理了 Mem0 记忆
        - deleted_vectors: 是否删除了向量存储目录
    """
    project_dir = os.path.join(PROJECTS_ROOT, project_name)
    result = {
        "deleted_files": False,
        "cleared_redis": 0,
        "cleared_mem0": False,
        "deleted_vectors": False,
    }
    
    # 1. 停止活跃任务并清理 Redis 状态
    try:
        from novelgen.services import generation_service
        # 先尝试停止正在运行的任务
        generation_service.stop_generation(project_name)
        # 清理 Redis 运行时状态
        result["cleared_redis"] = generation_service.clear_runtime_state(project_name)
        logger.info(f"已清理项目 {project_name} 的 Redis 状态，删除 {result['cleared_redis']} 个键")
    except Exception as e:
        logger.warning(f"清理 Redis 状态时出错: {e}")
    
    # 2. 尝试加载项目配置以获取向量存储路径和 Mem0 配置
    vector_store_dir: Optional[str] = None
    mem0_enabled = False
    
    try:
        settings_path = os.path.join(project_dir, "settings.json")
        if os.path.exists(settings_path):
            from novelgen.config import ProjectConfig
            config = ProjectConfig(
                project_name=project_name,
                project_dir=project_dir,
            )
            vector_store_dir = config.get_vector_store_dir()
            mem0_enabled = config.mem0_config is not None and config.mem0_config.enabled
    except Exception as e:
        logger.warning(f"加载项目配置时出错: {e}")
    
    # 3. 清理 Mem0 记忆（如果启用）
    if mem0_enabled:
        try:
            from novelgen.runtime.mem0_manager import Mem0Manager, Mem0InitializationError
            from novelgen.config import ProjectConfig
            
            config = ProjectConfig(
                project_name=project_name,
                project_dir=project_dir,
            )
            if config.mem0_config and config.mem0_config.enabled:
                mem0_manager = Mem0Manager(
                    config=config.mem0_config,
                    project_id=project_name,
                    embedding_config=config.embedding_config,
                )
                mem0_manager.clear_project_memory()
                mem0_manager.close(timeout=3.0)
                result["cleared_mem0"] = True
                logger.info(f"已清理项目 {project_name} 的 Mem0 记忆")
        except Mem0InitializationError as e:
            logger.warning(f"Mem0 初始化失败，跳过记忆清理: {e}")
        except Exception as e:
            logger.warning(f"清理 Mem0 记忆时出错: {e}")
    
    # 4. 删除向量存储目录（仅当位于项目目录内时）
    if vector_store_dir and os.path.exists(vector_store_dir):
        # 安全检查：只删除位于项目目录内的向量存储
        abs_vector_dir = os.path.abspath(vector_store_dir)
        abs_project_dir = os.path.abspath(project_dir)
        if abs_vector_dir.startswith(abs_project_dir + os.sep):
            try:
                shutil.rmtree(vector_store_dir)
                result["deleted_vectors"] = True
                logger.info(f"已删除项目 {project_name} 的向量存储目录: {vector_store_dir}")
            except Exception as e:
                logger.warning(f"删除向量存储目录时出错: {e}")
        else:
            logger.info(f"向量存储目录 {vector_store_dir} 不在项目目录内，跳过删除")
    
    # 5. 删除项目目录
    if os.path.exists(project_dir):
        try:
            shutil.rmtree(project_dir)
            result["deleted_files"] = True
            logger.info(f"已删除项目目录: {project_dir}")
        except Exception as e:
            logger.error(f"删除项目目录时出错: {e}")
            raise
    
    return result


def load_settings(project_name: str) -> Dict[str, Any]:
    """读取 settings.json，失败返回空字典"""
    settings_path = os.path.join(PROJECTS_ROOT, project_name, "settings.json")
    return _load_json(settings_path) or {}


def _calculate_step_state(project_dir: str) -> ProjectStepState:
    """根据文件存在性推断六步完成状态"""
    world = os.path.exists(os.path.join(project_dir, "world.json"))
    theme = os.path.exists(os.path.join(project_dir, "theme_conflict.json"))
    characters = os.path.exists(os.path.join(project_dir, "characters.json"))
    outline = os.path.exists(os.path.join(project_dir, "outline.json"))
    chapters_plan = bool(glob.glob(os.path.join(project_dir, "chapters", "*_plan.json")))
    chapters = bool(glob.glob(os.path.join(project_dir, "chapters", "chapter_*.json")))
    return ProjectStepState(
        world=world,
        theme=theme,
        characters=characters,
        outline=outline,
        chapters_plan=chapters_plan,
        chapters=chapters,
    )


def load_project_state(project_name: str) -> ProjectState:
    """汇总项目状态"""
    project_dir = os.path.join(PROJECTS_ROOT, project_name)
    step_state = _calculate_step_state(project_dir)
    checkpoint_exists = os.path.exists(os.path.join(project_dir, "workflow_checkpoints.db"))

    chapter_metas: List[Dict[str, Any]] = []
    chapter_files = sorted(glob.glob(os.path.join(project_dir, "chapters", "chapter_*.json")))
    for path in chapter_files:
        chapter_data = _load_json(path)
        if not chapter_data:
            continue
        try:
            chapter = GeneratedChapter(**chapter_data)
            chapter_metas.append(
                {
                    "chapter_number": chapter.chapter_number,
                    "chapter_title": chapter.chapter_title,
                    "scenes_count": len(chapter.scenes),
                    "total_words": chapter.total_words,
                    "status": "completed",
                }
            )
        except Exception:
            continue

    return ProjectState(steps=step_state, checkpoint_exists=checkpoint_exists, chapters=chapter_metas)


