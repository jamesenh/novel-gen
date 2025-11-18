"""
数据库抽象接口层
提供与具体实现解耦的数据库操作接口
"""
import sqlite3
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from contextlib import contextmanager

from novelgen.models import EntityStateSnapshot, StoryMemoryChunk


logger = logging.getLogger(__name__)


class DatabaseInterface(ABC):
    """数据库操作抽象接口"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化数据库连接和表结构"""
        pass
    
    @abstractmethod
    def save_entity_snapshot(self, snapshot: EntityStateSnapshot) -> bool:
        """保存实体状态快照"""
        pass
    
    @abstractmethod
    def get_entity_snapshots(self, project_id: str, entity_id: Optional[str] = None) -> List[EntityStateSnapshot]:
        """获取实体状态快照"""
        pass
    
    @abstractmethod
    def save_memory_chunk(self, chunk: StoryMemoryChunk) -> bool:
        """保存记忆块"""
        pass
    
    @abstractmethod
    def get_memory_chunks(self, project_id: str, chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """获取记忆块"""
        pass
    
    @abstractmethod
    def get_latest_entity_state(self, project_id: str, entity_id: str) -> Optional[EntityStateSnapshot]:
        """获取实体的最新状态快照"""
        pass
    
    @abstractmethod
    def get_entity_timeline(self, project_id: str, entity_id: str, 
                           start_chapter: Optional[int] = None,
                           end_chapter: Optional[int] = None) -> List[EntityStateSnapshot]:
        """获取实体在指定章节范围内的状态时间线"""
        pass
    
    @abstractmethod
    def get_timeline_around(self, project_id: str, chapter_index: int, 
                           scene_index: Optional[int] = None,
                           context_window: int = 1) -> List[EntityStateSnapshot]:
        """获取指定场景周围的实体状态快照（用于查看某个场景前后的实体变化）"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """检查数据库健康状态"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭数据库连接"""
        pass


class SQLiteDatabase(DatabaseInterface):
    """SQLite数据库实现"""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        try:
            if self.connection is None:
                self.connection = sqlite3.connect(self.db_path)
                self.connection.row_factory = sqlite3.Row
            yield self.connection
        except sqlite3.Error as e:
            logger.error(f"数据库连接错误: {e}")
            raise
        finally:
            if self.connection:
                self.connection.commit()
    
    def initialize(self) -> bool:
        """初始化数据库和表结构"""
        try:
            # 确保数据库目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as conn:
                # 创建迁移历史表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TEXT NOT NULL
                    )
                """)
                
                # 创建实体状态快照表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS entity_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        entity_type TEXT NOT NULL,
                        entity_id TEXT NOT NULL,
                        chapter_index INTEGER,
                        scene_index INTEGER,
                        timestamp TEXT NOT NULL,
                        state_data TEXT NOT NULL,
                        version INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(project_id, entity_id, chapter_index, scene_index, timestamp)
                    )
                """)
                
                # 创建记忆块表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_chunks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chunk_id TEXT NOT NULL UNIQUE,
                        project_id TEXT NOT NULL,
                        chapter_index INTEGER,
                        scene_index INTEGER,
                        content TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        entities_mentioned TEXT DEFAULT '[]',
                        tags TEXT DEFAULT '[]',
                        embedding_id TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                
                # 创建索引
                conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_project ON entity_snapshots(project_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_id ON entity_snapshots(entity_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_chunks(project_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_chapter ON memory_chunks(chapter_index)")
                
            logger.info(f"数据库初始化成功: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return False
    
    def save_entity_snapshot(self, snapshot: EntityStateSnapshot) -> bool:
        """保存实体状态快照"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO entity_snapshots 
                    (project_id, entity_type, entity_id, chapter_index, scene_index, 
                     timestamp, state_data, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.project_id,
                    snapshot.entity_type,
                    snapshot.entity_id,
                    snapshot.chapter_index,
                    snapshot.scene_index,
                    snapshot.timestamp.isoformat(),
                    json.dumps(snapshot.state_data, ensure_ascii=False),
                    snapshot.version
                ))
            return True
            
        except Exception as e:
            logger.error(f"保存实体状态快照失败: {e}")
            return False
    
    def get_entity_snapshots(self, project_id: str, entity_id: Optional[str] = None) -> List[EntityStateSnapshot]:
        """获取实体状态快照"""
        try:
            with self.get_connection() as conn:
                if entity_id:
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots 
                        WHERE project_id = ? AND entity_id = ?
                        ORDER BY timestamp DESC
                    """, (project_id, entity_id))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots 
                        WHERE project_id = ?
                        ORDER BY timestamp DESC
                    """, (project_id,))
                
                snapshots = []
                for row in cursor.fetchall():
                    snapshot = EntityStateSnapshot(
                        project_id=row['project_id'],
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        chapter_index=row['chapter_index'],
                        scene_index=row['scene_index'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        state_data=json.loads(row['state_data']),
                        version=row['version']
                    )
                    snapshots.append(snapshot)
                
                return snapshots
                
        except Exception as e:
            logger.error(f"获取实体状态快照失败: {e}")
            return []
    
    def save_memory_chunk(self, chunk: StoryMemoryChunk) -> bool:
        """保存记忆块"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memory_chunks 
                    (chunk_id, project_id, chapter_index, scene_index, content, 
                     content_type, entities_mentioned, tags, embedding_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk.chunk_id,
                    chunk.project_id,
                    chunk.chapter_index,
                    chunk.scene_index,
                    chunk.content,
                    chunk.content_type,
                    json.dumps(chunk.entities_mentioned, ensure_ascii=False),
                    json.dumps(chunk.tags, ensure_ascii=False),
                    chunk.embedding_id,
                    chunk.created_at.isoformat()
                ))
            return True
            
        except Exception as e:
            logger.error(f"保存记忆块失败: {e}")
            return False
    
    def get_memory_chunks(self, project_id: str, chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """获取记忆块"""
        try:
            with self.get_connection() as conn:
                if chapter_index is not None:
                    cursor = conn.execute("""
                        SELECT * FROM memory_chunks 
                        WHERE project_id = ? AND chapter_index = ?
                        ORDER BY created_at DESC
                    """, (project_id, chapter_index))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM memory_chunks 
                        WHERE project_id = ?
                        ORDER BY created_at DESC
                    """, (project_id,))
                
                chunks = []
                for row in cursor.fetchall():
                    chunk = StoryMemoryChunk(
                        chunk_id=row['chunk_id'],
                        project_id=row['project_id'],
                        chapter_index=row['chapter_index'],
                        scene_index=row['scene_index'],
                        content=row['content'],
                        content_type=row['content_type'],
                        entities_mentioned=json.loads(row['entities_mentioned']),
                        tags=json.loads(row['tags']),
                        embedding_id=row['embedding_id'],
                        created_at=datetime.fromisoformat(row['created_at'])
                    )
                    chunks.append(chunk)
                
                return chunks
                
        except Exception as e:
            logger.error(f"获取记忆块失败: {e}")
            return []
    
    def get_latest_entity_state(self, project_id: str, entity_id: str) -> Optional[EntityStateSnapshot]:
        """获取实体的最新状态快照"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM entity_snapshots
                    WHERE project_id = ? AND entity_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (project_id, entity_id))
                
                row = cursor.fetchone()
                if row:
                    return EntityStateSnapshot(
                        project_id=row['project_id'],
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        chapter_index=row['chapter_index'],
                        scene_index=row['scene_index'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        state_data=json.loads(row['state_data']),
                        version=row['version']
                    )
                return None
                
        except Exception as e:
            logger.error(f"获取实体最新状态失败: {e}")
            return None
    
    def get_entity_timeline(self, project_id: str, entity_id: str,
                           start_chapter: Optional[int] = None,
                           end_chapter: Optional[int] = None) -> List[EntityStateSnapshot]:
        """获取实体在指定章节范围内的状态时间线"""
        try:
            with self.get_connection() as conn:
                if start_chapter is not None and end_chapter is not None:
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots
                        WHERE project_id = ? AND entity_id = ?
                        AND chapter_index BETWEEN ? AND ?
                        ORDER BY chapter_index ASC, scene_index ASC, timestamp ASC
                    """, (project_id, entity_id, start_chapter, end_chapter))
                elif start_chapter is not None:
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots
                        WHERE project_id = ? AND entity_id = ?
                        AND chapter_index >= ?
                        ORDER BY chapter_index ASC, scene_index ASC, timestamp ASC
                    """, (project_id, entity_id, start_chapter))
                elif end_chapter is not None:
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots
                        WHERE project_id = ? AND entity_id = ?
                        AND chapter_index <= ?
                        ORDER BY chapter_index ASC, scene_index ASC, timestamp ASC
                    """, (project_id, entity_id, end_chapter))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots
                        WHERE project_id = ? AND entity_id = ?
                        ORDER BY chapter_index ASC, scene_index ASC, timestamp ASC
                    """, (project_id, entity_id))
                
                snapshots = []
                for row in cursor.fetchall():
                    snapshot = EntityStateSnapshot(
                        project_id=row['project_id'],
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        chapter_index=row['chapter_index'],
                        scene_index=row['scene_index'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        state_data=json.loads(row['state_data']),
                        version=row['version']
                    )
                    snapshots.append(snapshot)
                
                return snapshots
                
        except Exception as e:
            logger.error(f"获取实体时间线失败: {e}")
            return []
    
    def get_timeline_around(self, project_id: str, chapter_index: int,
                           scene_index: Optional[int] = None,
                           context_window: int = 1) -> List[EntityStateSnapshot]:
        """获取指定场景周围的实体状态快照"""
        try:
            with self.get_connection() as conn:
                # 计算章节范围
                start_chapter = max(0, chapter_index - context_window)
                end_chapter = chapter_index + context_window
                
                if scene_index is not None:
                    # 如果指定了场景，获取该章节内该场景周围的快照
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots
                        WHERE project_id = ?
                        AND (
                            (chapter_index = ? AND scene_index = ?)
                            OR (chapter_index BETWEEN ? AND ?)
                        )
                        ORDER BY chapter_index ASC, scene_index ASC, timestamp ASC
                    """, (project_id, chapter_index, scene_index, start_chapter, end_chapter))
                else:
                    # 如果没有指定场景，获取章节范围内的所有快照
                    cursor = conn.execute("""
                        SELECT * FROM entity_snapshots
                        WHERE project_id = ?
                        AND chapter_index BETWEEN ? AND ?
                        ORDER BY chapter_index ASC, scene_index ASC, timestamp ASC
                    """, (project_id, start_chapter, end_chapter))
                
                snapshots = []
                for row in cursor.fetchall():
                    snapshot = EntityStateSnapshot(
                        project_id=row['project_id'],
                        entity_type=row['entity_type'],
                        entity_id=row['entity_id'],
                        chapter_index=row['chapter_index'],
                        scene_index=row['scene_index'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        state_data=json.loads(row['state_data']),
                        version=row['version']
                    )
                    snapshots.append(snapshot)
                
                return snapshots
                
        except Exception as e:
            logger.error(f"获取场景周围时间线失败: {e}")
            return []
    
    def health_check(self) -> bool:
        """检查数据库健康状态"""
        try:
            if self.connection is None:
                return False
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


class DatabaseManager:
    """数据库管理器，提供降级和错误处理"""
    
    def __init__(self, db_path: Union[str, Path], enabled: bool = True):
        self.enabled = enabled
        self.db: Optional[DatabaseInterface] = None
        
        if self.enabled:
            try:
                self.db = SQLiteDatabase(db_path)
                if not self.db.initialize():
                    logger.warning("数据库初始化失败，降级到非持久化模式")
                    self.enabled = False
                    self.db = None
            except Exception as e:
                logger.warning(f"数据库创建失败，降级到非持久化模式: {e}")
                self.enabled = False
                self.db = None
    
    def is_enabled(self) -> bool:
        """检查持久化是否启用"""
        return self.enabled and self.db is not None
    
    def save_entity_snapshot(self, snapshot: EntityStateSnapshot) -> bool:
        """保存实体状态快照（带降级处理）"""
        if not self.is_enabled():
            logger.debug("持久化未启用，跳过实体状态快照保存")
            return True
        
        try:
            return self.db.save_entity_snapshot(snapshot)
        except Exception as e:
            logger.warning(f"保存实体状态快照失败，但不影响主流程: {e}")
            return True
    
    def get_entity_snapshots(self, project_id: str, entity_id: Optional[str] = None) -> List[EntityStateSnapshot]:
        """获取实体状态快照（带降级处理）"""
        if not self.is_enabled():
            logger.debug("持久化未启用，返回空实体状态列表")
            return []
        
        try:
            return self.db.get_entity_snapshots(project_id, entity_id)
        except Exception as e:
            logger.warning(f"获取实体状态快照失败，返回空列表: {e}")
            return []
    
    def save_memory_chunk(self, chunk: StoryMemoryChunk) -> bool:
        """保存记忆块（带降级处理）"""
        if not self.is_enabled():
            logger.debug("持久化未启用，跳过记忆块保存")
            return True
        
        try:
            return self.db.save_memory_chunk(chunk)
        except Exception as e:
            logger.warning(f"保存记忆块失败，但不影响主流程: {e}")
            return True
    
    def get_memory_chunks(self, project_id: str, chapter_index: Optional[int] = None) -> List[StoryMemoryChunk]:
        """获取记忆块（带降级处理）"""
        if not self.is_enabled():
            logger.debug("持久化未启用，返回空记忆块列表")
            return []
        
        try:
            return self.db.get_memory_chunks(project_id, chapter_index)
        except Exception as e:
            logger.warning(f"获取记忆块失败，返回空列表: {e}")
            return []
    
    def get_latest_entity_state(self, project_id: str, entity_id: str) -> Optional[EntityStateSnapshot]:
        """获取实体最新状态（带降级处理）"""
        if not self.is_enabled():
            logger.debug("持久化未启用，返回None")
            return None
        
        try:
            return self.db.get_latest_entity_state(project_id, entity_id)
        except Exception as e:
            logger.warning(f"获取实体最新状态失败，返回None: {e}")
            return None
    
    def get_entity_timeline(self, project_id: str, entity_id: str,
                           start_chapter: Optional[int] = None,
                           end_chapter: Optional[int] = None) -> List[EntityStateSnapshot]:
        """获取实体时间线（带降级处理）"""
        if not self.is_enabled():
            logger.debug("持久化未启用，返回空列表")
            return []
        
        try:
            return self.db.get_entity_timeline(project_id, entity_id, start_chapter, end_chapter)
        except Exception as e:
            logger.warning(f"获取实体时间线失败，返回空列表: {e}")
            return []
    
    def get_timeline_around(self, project_id: str, chapter_index: int,
                           scene_index: Optional[int] = None,
                           context_window: int = 1) -> List[EntityStateSnapshot]:
        """获取场景周围时间线（带降级处理）"""
        if not self.is_enabled():
            logger.debug("持久化未启用，返回空列表")
            return []
        
        try:
            return self.db.get_timeline_around(project_id, chapter_index, scene_index, context_window)
        except Exception as e:
            logger.warning(f"获取场景周围时间线失败，返回空列表: {e}")
            return []
    
    def health_check(self) -> bool:
        """健康检查"""
        if not self.is_enabled():
            return True  # 降级模式下总是健康的
        
        try:
            return self.db.health_check()
        except Exception as e:
            logger.warning(f"数据库健康检查失败: {e}")
            return False
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.db:
            try:
                self.db.close()
            except Exception as e:
                logger.warning(f"关闭数据库连接失败: {e}")
