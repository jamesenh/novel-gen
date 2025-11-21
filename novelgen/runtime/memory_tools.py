"""
记忆检索工具函数层
提供便捷的记忆和实体状态检索接口，供记忆上下文检索链使用
"""
import logging
from typing import List, Optional, Dict, Any

from novelgen.models import StoryMemoryChunk, EntityStateSnapshot
from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager


logger = logging.getLogger(__name__)


def search_story_memory_tool(
    db_manager: DatabaseManager,
    vector_manager: VectorStoreManager,
    project_id: str,
    query: str,
    entities: Optional[List[str]] = None,
    content_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    top_k: int = 10
) -> List[StoryMemoryChunk]:
    """
    搜索与查询相关的故事记忆块
    
    Args:
        db_manager: 数据库管理器实例
        vector_manager: 向量存储管理器实例
        project_id: 项目ID
        query: 查询关键词或语义描述
        entities: 可选的实体ID列表，用于过滤
        content_type: 可选的内容类型过滤（如 scene, dialogue, description）
        tags: 可选的标签列表过滤
        top_k: 返回的记忆块数量上限，默认10
        
    Returns:
        相关记忆块列表，如果检索失败或无结果则返回空列表
    """
    try:
        # 使用向量存储管理器的过滤搜索方法
        chunks = vector_manager.search_memory_with_filters(
            query=query,
            project_id=project_id,
            content_type=content_type,
            entities=entities,
            tags=tags,
            limit=top_k
        )
        
        if chunks:
            logger.info(f"搜索到{len(chunks)}个相关记忆块")
        else:
            logger.info("未搜索到相关记忆块")
            
        return chunks
        
    except Exception as e:
        logger.warning(f"搜索故事记忆失败，返回空列表: {e}")
        return []


def get_entity_state_tool(
    db_manager: DatabaseManager,
    project_id: str,
    entity_id: str,
    chapter_index: Optional[int] = None,
    scene_index: Optional[int] = None
) -> Optional[EntityStateSnapshot]:
    """
    获取指定实体的状态快照
    
    Args:
        db_manager: 数据库管理器实例
        project_id: 项目ID
        entity_id: 实体ID
        chapter_index: 可选的章节索引，如果提供则尝试获取该章节附近的状态
        scene_index: 可选的场景索引，进一步精确定位状态
        
    Returns:
        实体状态快照，未找到或失败则返回None
    """
    try:
        # 如果提供了章节和场景信息，尝试获取更精确的状态
        if chapter_index is not None:
            # 获取该实体在指定章节周围的时间线
            timeline = db_manager.get_timeline_around(
                project_id=project_id,
                chapter_index=chapter_index,
                scene_index=scene_index,
                context_window=0  # 只获取当前章节
            )
            
            # 从时间线中找到该实体的状态
            for snapshot in timeline:
                if snapshot.entity_id == entity_id:
                    logger.info(f"找到实体 {entity_id} 在章节 {chapter_index} 的状态")
                    return snapshot
        
        # 如果没有找到或没有提供章节信息，则获取最新状态
        snapshot = db_manager.get_latest_entity_state(project_id, entity_id)
        if snapshot:
            logger.info(f"找到实体 {entity_id} 的最新状态")
        else:
            logger.info(f"未找到实体 {entity_id} 的状态")
            
        return snapshot
        
    except Exception as e:
        logger.warning(f"获取实体状态失败，返回None: {e}")
        return None


def get_recent_timeline_tool(
    db_manager: DatabaseManager,
    project_id: str,
    chapter_index: int,
    context_window: int = 1,
    scene_index: Optional[int] = None
) -> List[EntityStateSnapshot]:
    """
    获取指定章节周围的实体状态时间线
    
    Args:
        db_manager: 数据库管理器实例
        project_id: 项目ID
        chapter_index: 章节索引
        context_window: 前后章节的窗口大小，默认1（即当前章节及前后各1章）
        scene_index: 可选的场景索引
        
    Returns:
        实体状态快照列表，按时间排序，失败则返回空列表
    """
    try:
        snapshots = db_manager.get_timeline_around(
            project_id=project_id,
            chapter_index=chapter_index,
            scene_index=scene_index,
            context_window=context_window
        )
        
        if snapshots:
            logger.info(f"获取到{len(snapshots)}个时间线状态快照")
        else:
            logger.info("未获取到时间线状态")
            
        return snapshots
        
    except Exception as e:
        logger.warning(f"获取时间线失败，返回空列表: {e}")
        return []


def get_entity_states_for_characters(
    db_manager: DatabaseManager,
    project_id: str,
    character_names: List[str],
    chapter_index: Optional[int] = None,
    scene_index: Optional[int] = None
) -> List[EntityStateSnapshot]:
    """
    批量获取多个角色的状态快照
    
    Args:
        db_manager: 数据库管理器实例
        project_id: 项目ID
        character_names: 角色名称列表
        chapter_index: 可选的章节索引
        scene_index: 可选的场景索引
        
    Returns:
        实体状态快照列表
    """
    snapshots = []
    
    for name in character_names:
        # 将角色名称作为entity_id（根据实际系统的entity_id生成规则调整）
        entity_id = f"character:{name}"
        snapshot = get_entity_state_tool(
            db_manager=db_manager,
            project_id=project_id,
            entity_id=entity_id,
            chapter_index=chapter_index,
            scene_index=scene_index
        )
        if snapshot:
            snapshots.append(snapshot)
    
    return snapshots
