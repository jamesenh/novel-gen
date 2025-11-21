"""
向量索引重建工具
提供项目级和章节级的向量索引重建能力
"""
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from novelgen.config import ProjectConfig
from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager
from novelgen.models import StoryMemoryChunk, GeneratedChapter

logger = logging.getLogger(__name__)


def reindex_project_vectors(
    project_id: str,
    project_dir: Optional[Path] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    重建整个项目的向量索引
    
    Args:
        project_id: 项目ID
        project_dir: 项目目录路径（可选，默认为 projects/{project_id}）
        dry_run: 是否仅统计而不实际执行
        
    Returns:
        重建结果统计信息字典
    """
    if project_dir is None:
        project_dir = Path(f"projects/{project_id}")
    
    project_dir = Path(project_dir)
    
    if not project_dir.exists():
        raise FileNotFoundError(f"项目目录不存在: {project_dir}")
    
    logger.info(f"开始重建项目 '{project_id}' 的向量索引...")
    
    # 加载项目配置
    config = ProjectConfig(project_dir=str(project_dir))
    
    # 初始化数据库和向量存储管理器
    db_manager = DatabaseManager(
        db_path=config.get_db_path(),
        enabled=config.persistence_enabled
    )
    
    vector_manager = VectorStoreManager(
        persist_directory=config.get_vector_store_dir(),
        enabled=config.vector_store_enabled,
        embedding_config=config.embedding_config
    )
    
    if not vector_manager.is_enabled():
        raise RuntimeError("向量存储未启用或初始化失败，无法重建索引")
    
    # 统计信息
    stats = {
        "project_id": project_id,
        "dry_run": dry_run,
        "deleted_chunks": 0,
        "created_chunks": 0,
        "chapters_processed": 0,
        "errors": []
    }
    
    try:
        # 1. 删除项目的所有旧向量
        if not dry_run:
            logger.info(f"删除项目 '{project_id}' 的旧向量...")
            if vector_manager.vector_store:
                # 先统计要删除的数量
                existing_chunks = vector_manager.vector_store.get_chunks_by_project(project_id)
                stats["deleted_chunks"] = len(existing_chunks)
                
                # 执行删除
                vector_manager.vector_store.delete_chunks_by_project(project_id)
                logger.info(f"已删除 {stats['deleted_chunks']} 个旧向量")
        else:
            # dry-run 模式只统计
            if vector_manager.vector_store:
                existing_chunks = vector_manager.vector_store.get_chunks_by_project(project_id)
                stats["deleted_chunks"] = len(existing_chunks)
                logger.info(f"[DRY-RUN] 将删除 {stats['deleted_chunks']} 个旧向量")
        
        # 2. 从数据库或章节 JSON 重建向量
        memory_chunks = _load_project_memory_chunks(
            project_id=project_id,
            project_dir=project_dir,
            db_manager=db_manager
        )
        
        if not dry_run and memory_chunks:
            logger.info(f"开始写入 {len(memory_chunks)} 个新向量...")
            chunk_ids = vector_manager.vector_store.add_chunks(memory_chunks)
            stats["created_chunks"] = len(chunk_ids)
            logger.info(f"已写入 {stats['created_chunks']} 个新向量")
        else:
            stats["created_chunks"] = len(memory_chunks)
            if dry_run:
                logger.info(f"[DRY-RUN] 将写入 {stats['created_chunks']} 个新向量")
        
        logger.info(f"项目 '{project_id}' 向量索引重建完成")
        
    except Exception as e:
        logger.error(f"重建项目向量索引失败: {e}")
        stats["errors"].append(str(e))
        raise
    finally:
        if db_manager:
            db_manager.close()
        if vector_manager and vector_manager.vector_store:
            vector_manager.vector_store.close()
    
    return stats


def reindex_chapter_vectors(
    project_id: str,
    chapter_index: int,
    project_dir: Optional[Path] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    重建指定章节的向量索引
    
    Args:
        project_id: 项目ID
        chapter_index: 章节索引
        project_dir: 项目目录路径（可选，默认为 projects/{project_id}）
        dry_run: 是否仅统计而不实际执行
        
    Returns:
        重建结果统计信息字典
    """
    if project_dir is None:
        project_dir = Path(f"projects/{project_id}")
    
    project_dir = Path(project_dir)
    
    if not project_dir.exists():
        raise FileNotFoundError(f"项目目录不存在: {project_dir}")
    
    logger.info(f"开始重建项目 '{project_id}' 章节 {chapter_index} 的向量索引...")
    
    # 加载项目配置
    config = ProjectConfig(project_dir=str(project_dir))
    
    # 初始化数据库和向量存储管理器
    db_manager = DatabaseManager(
        db_path=config.get_db_path(),
        enabled=config.persistence_enabled
    )
    
    vector_manager = VectorStoreManager(
        persist_directory=config.get_vector_store_dir(),
        enabled=config.vector_store_enabled,
        embedding_config=config.embedding_config
    )
    
    if not vector_manager.is_enabled():
        raise RuntimeError("向量存储未启用或初始化失败，无法重建索引")
    
    # 统计信息
    stats = {
        "project_id": project_id,
        "chapter_index": chapter_index,
        "dry_run": dry_run,
        "deleted_chunks": 0,
        "created_chunks": 0,
        "errors": []
    }
    
    try:
        # 1. 删除该章节的旧向量
        if not dry_run:
            logger.info(f"删除章节 {chapter_index} 的旧向量...")
            if vector_manager.vector_store:
                # 先统计要删除的数量
                existing_chunks = vector_manager.vector_store.get_chunks_by_project(
                    project_id, chapter_index
                )
                stats["deleted_chunks"] = len(existing_chunks)
                
                # 执行删除（通过获取chunk IDs再删除）
                if existing_chunks:
                    chunk_ids = [chunk.chunk_id for chunk in existing_chunks]
                    vector_manager.vector_store.collection.delete(ids=chunk_ids)
                    logger.info(f"已删除 {stats['deleted_chunks']} 个旧向量")
        else:
            # dry-run 模式只统计
            if vector_manager.vector_store:
                existing_chunks = vector_manager.vector_store.get_chunks_by_project(
                    project_id, chapter_index
                )
                stats["deleted_chunks"] = len(existing_chunks)
                logger.info(f"[DRY-RUN] 将删除 {stats['deleted_chunks']} 个旧向量")
        
        # 2. 从数据库或章节 JSON 重建该章节的向量
        memory_chunks = _load_chapter_memory_chunks(
            project_id=project_id,
            chapter_index=chapter_index,
            project_dir=project_dir,
            db_manager=db_manager,
            vector_manager=vector_manager
        )
        
        if not dry_run and memory_chunks:
            logger.info(f"开始写入章节 {chapter_index} 的 {len(memory_chunks)} 个新向量...")
            chunk_ids = vector_manager.vector_store.add_chunks(memory_chunks)
            stats["created_chunks"] = len(chunk_ids)
            logger.info(f"已写入 {stats['created_chunks']} 个新向量")
        else:
            stats["created_chunks"] = len(memory_chunks)
            if dry_run:
                logger.info(f"[DRY-RUN] 将写入 {stats['created_chunks']} 个新向量")
        
        logger.info(f"章节 {chapter_index} 向量索引重建完成")
        
    except Exception as e:
        logger.error(f"重建章节向量索引失败: {e}")
        stats["errors"].append(str(e))
        raise
    finally:
        if db_manager:
            db_manager.close()
        if vector_manager and vector_manager.vector_store:
            vector_manager.vector_store.close()
    
    return stats


def _load_project_memory_chunks(
    project_id: str,
    project_dir: Path,
    db_manager: DatabaseManager
) -> List[StoryMemoryChunk]:
    """
    从数据库或章节 JSON 加载整个项目的记忆块
    
    优先级：
    1. 数据库 memory_chunks 表
    2. 章节 JSON 文件
    """
    memory_chunks = []
    
    # 优先从数据库加载
    if db_manager and db_manager.is_enabled():
        try:
            logger.info("尝试从数据库加载记忆块...")
            memory_chunks = db_manager.get_memory_chunks(project_id)
            if memory_chunks:
                logger.info(f"从数据库加载了 {len(memory_chunks)} 个记忆块")
                return memory_chunks
            else:
                logger.info("数据库中未找到记忆块，尝试从章节 JSON 加载...")
        except Exception as e:
            logger.warning(f"从数据库加载记忆块失败: {e}，尝试从章节 JSON 加载...")
    
    # 退回到从章节 JSON 加载
    logger.info("从章节 JSON 文件重建记忆块...")
    chapters_dir = project_dir / "chapters"
    
    if not chapters_dir.exists():
        logger.warning(f"章节目录不存在: {chapters_dir}")
        return []
    
    # 遍历所有章节 JSON 文件（排除 plan 文件）
    chapter_files = sorted([
        f for f in chapters_dir.glob("chapter_*.json")
        if not f.name.endswith("_plan.json")
    ])
    
    for chapter_file in chapter_files:
        try:
            with open(chapter_file, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
            
            chapter = GeneratedChapter(**chapter_data)
            chapter_index = chapter.chapter_number
            
            # 为每个场景创建记忆块
            for scene in chapter.scenes:
                # 使用 VectorStoreManager 的分块逻辑
                from novelgen.runtime.vector_store import TextChunker
                chunker = TextChunker()  # 使用默认配置
                
                chunks = chunker.create_chunks_from_scene(
                    scene_content=scene.content,
                    project_id=project_id,
                    chapter_index=chapter_index,
                    scene_index=scene.scene_number,
                    content_type="scene"
                )
                memory_chunks.extend(chunks)
                
        except Exception as e:
            logger.error(f"加载章节文件 {chapter_file} 失败: {e}")
            continue
    
    logger.info(f"从章节 JSON 重建了 {len(memory_chunks)} 个记忆块")
    return memory_chunks


def _load_chapter_memory_chunks(
    project_id: str,
    chapter_index: int,
    project_dir: Path,
    db_manager: DatabaseManager,
    vector_manager: VectorStoreManager
) -> List[StoryMemoryChunk]:
    """
    从数据库或章节 JSON 加载指定章节的记忆块
    
    优先级：
    1. 数据库 memory_chunks 表
    2. 章节 JSON 文件
    """
    memory_chunks = []
    
    # 优先从数据库加载
    if db_manager and db_manager.is_enabled():
        try:
            logger.info(f"尝试从数据库加载章节 {chapter_index} 的记忆块...")
            # 直接获取该章节的记忆块
            memory_chunks = db_manager.get_memory_chunks(project_id, chapter_index)
            
            if memory_chunks:
                logger.info(f"从数据库加载了 {len(memory_chunks)} 个记忆块")
                return memory_chunks
            else:
                logger.info("数据库中未找到该章节的记忆块，尝试从章节 JSON 加载...")
        except Exception as e:
            logger.warning(f"从数据库加载记忆块失败: {e}，尝试从章节 JSON 加载...")
    
    # 退回到从章节 JSON 加载
    logger.info(f"从章节 JSON 文件重建章节 {chapter_index} 的记忆块...")
    chapter_file = project_dir / "chapters" / f"chapter_{chapter_index:03d}.json"
    
    if not chapter_file.exists():
        logger.warning(f"章节文件不存在: {chapter_file}")
        return []
    
    try:
        with open(chapter_file, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        
        chapter = GeneratedChapter(**chapter_data)
        
        # 为每个场景创建记忆块
        for scene in chapter.scenes:
            chunks = vector_manager.chunker.create_chunks_from_scene(
                scene_content=scene.content,
                project_id=project_id,
                chapter_index=chapter_index,
                scene_index=scene.scene_number,
                content_type="scene"
            )
            memory_chunks.extend(chunks)
            
    except Exception as e:
        logger.error(f"加载章节文件 {chapter_file} 失败: {e}")
        return []
    
    logger.info(f"从章节 JSON 重建了 {len(memory_chunks)} 个记忆块")
    return memory_chunks
