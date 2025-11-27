"""
记忆检索工具函数层
提供便捷的记忆和实体状态检索接口

更新: 2025-11-25 - 简化为使用 Mem0Manager 作为唯一记忆源
"""
import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from novelgen.models import StoryMemoryChunk, EntityStateSnapshot

if TYPE_CHECKING:
    from novelgen.runtime.mem0_manager import Mem0Manager


logger = logging.getLogger(__name__)


def search_story_memory_tool(
    mem0_manager: "Mem0Manager",
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
        mem0_manager: Mem0 管理器实例
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
        # 使用 Mem0Manager 的过滤搜索方法
        chunks = mem0_manager.search_memory_with_filters(
            query=query,
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
    mem0_manager: "Mem0Manager",
    project_id: str,
    entity_id: str,
    chapter_index: Optional[int] = None,
    scene_index: Optional[int] = None
) -> Optional[EntityStateSnapshot]:
    """
    获取指定实体的状态快照
    
    Args:
        mem0_manager: Mem0 管理器实例
        project_id: 项目ID
        entity_id: 实体ID
        chapter_index: 可选的章节索引
        scene_index: 可选的场景索引
        
    Returns:
        实体状态快照，未找到或失败则返回None
    """
    try:
        # 从 Mem0 获取实体状态
        states = mem0_manager.get_entity_state(
            entity_id=entity_id,
            query=f"{entity_id} 的最新状态",
            limit=1
        )
        
        if states:
            # 转换为 EntityStateSnapshot
            from datetime import datetime
            latest_state = states[0]
            snapshot = EntityStateSnapshot(
                project_id=project_id,
                entity_type="character",
                entity_id=entity_id,
                chapter_index=chapter_index,
                scene_index=scene_index,
                timestamp=datetime.now(),
                state_data={
                    "source": "mem0",
                    "memory": latest_state.get('memory', ''),
                    "metadata": latest_state.get('metadata', {}),
                },
                version=1
            )
            logger.info(f"找到实体 {entity_id} 的状态")
            return snapshot
        else:
            logger.info(f"未找到实体 {entity_id} 的状态")
            return None
        
    except Exception as e:
        logger.warning(f"获取实体状态失败，返回None: {e}")
        return None


def get_recent_timeline_tool(
    mem0_manager: "Mem0Manager",
    project_id: str,
    chapter_index: int,
    context_window: int = 1,
    scene_index: Optional[int] = None
) -> List[EntityStateSnapshot]:
    """
    获取指定章节周围的实体状态时间线
    
    Args:
        mem0_manager: Mem0 管理器实例
        project_id: 项目ID
        chapter_index: 章节索引
        context_window: 前后章节的窗口大小，默认1
        scene_index: 可选的场景索引
        
    Returns:
        实体状态快照列表，失败则返回空列表
    """
    try:
        # 从 Mem0 搜索该章节的场景内容
        memories = mem0_manager.search_scene_content(
            query=f"第{chapter_index}章的内容和角色状态",
            chapter_index=chapter_index,
            limit=10
        )
        
        # 将记忆转换为 EntityStateSnapshot（简化版本）
        from datetime import datetime
        snapshots = []
        for memory in memories:
            snapshot = EntityStateSnapshot(
                project_id=project_id,
                entity_type="scene_memory",
                entity_id=f"scene_{memory.chapter_index}_{memory.scene_index}",
                chapter_index=memory.chapter_index,
                scene_index=memory.scene_index,
                timestamp=datetime.now(),
                state_data={
                    "source": "mem0",
                    "content": memory.content[:200],
                    "content_type": memory.content_type,
                },
                version=1
            )
            snapshots.append(snapshot)
        
        if snapshots:
            logger.info(f"获取到{len(snapshots)}个时间线状态快照")
        else:
            logger.info("未获取到时间线状态")
            
        return snapshots
        
    except Exception as e:
        logger.warning(f"获取时间线失败，返回空列表: {e}")
        return []


def get_entity_states_for_characters(
    mem0_manager: "Mem0Manager",
    project_id: str,
    character_names: List[str],
    chapter_index: Optional[int] = None,
    scene_index: Optional[int] = None
) -> List[EntityStateSnapshot]:
    """
    批量获取多个角色的状态快照
    
    Args:
        mem0_manager: Mem0 管理器实例
        project_id: 项目ID
        character_names: 角色名称列表
        chapter_index: 可选的章节索引
        scene_index: 可选的场景索引
        
    Returns:
        实体状态快照列表
    """
    try:
        snapshots = mem0_manager.get_entity_states_for_characters(
            character_names=character_names,
            chapter_index=chapter_index,
            scene_index=scene_index
        )
        return snapshots
    except Exception as e:
        logger.warning(f"批量获取角色状态失败: {e}")
        return []
