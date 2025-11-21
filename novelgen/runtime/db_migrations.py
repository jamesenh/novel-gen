"""
数据库迁移脚本
处理数据库版本升级和结构变更
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Migration:
    """单个迁移的基类"""
    
    def __init__(self, version: int, description: str):
        self.version = version
        self.description = description
        self.created_at = datetime.now()
    
    def up(self, conn: sqlite3.Connection) -> None:
        """执行迁移"""
        raise NotImplementedError
    
    def down(self, conn: sqlite3.Connection) -> None:
        """回滚迁移"""
        raise NotImplementedError


class CreateInitialTables(Migration):
    """创建初始表结构"""
    
    def __init__(self):
        super().__init__(1, "创建实体状态快照和记忆块表")
    
    def up(self, conn: sqlite3.Connection) -> None:
        """创建初始表"""
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
    
    def down(self, conn: sqlite3.Connection) -> None:
        """回滚迁移"""
        conn.execute("DROP TABLE IF EXISTS memory_chunks")
        conn.execute("DROP TABLE IF EXISTS entity_snapshots")
        conn.execute("DROP TABLE IF EXISTS schema_migrations")


class MigrationManager:
    """迁移管理器"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.migrations: List[Migration] = [
            CreateInitialTables(),
        ]
    
    def get_applied_migrations(self, conn: sqlite3.Connection) -> List[int]:
        """获取已应用的迁移版本"""
        try:
            cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # 表不存在，返回空列表
            return []
    
    def apply_migrations(self) -> bool:
        """应用所有待执行的迁移"""
        try:
            # 确保数据库目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # 获取已应用的迁移
                applied = self.get_applied_migrations(conn)
                
                # 应用未执行的迁移
                for migration in self.migrations:
                    if migration.version not in applied:
                        logger.info(f"应用迁移 v{migration.version}: {migration.description}")
                        migration.up(conn)
                        
                        # 记录迁移历史
                        conn.execute("""
                            INSERT INTO schema_migrations (version, description, applied_at)
                            VALUES (?, ?, ?)
                        """, (migration.version, migration.description, datetime.now().isoformat()))
                        
                        logger.info(f"迁移 v{migration.version} 应用成功")
                
                conn.commit()
                logger.info("所有迁移应用完成")
                return True
                
        except Exception as e:
            logger.error(f"应用迁移失败: {e}")
            return False
    
    def rollback_to_version(self, target_version: int) -> bool:
        """回滚到指定版本"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                applied = self.get_applied_migrations(conn)
                
                # 按版本倒序回滚
                for migration in reversed(self.migrations):
                    if migration.version > target_version and migration.version in applied:
                        logger.info(f"回滚迁移 v{migration.version}: {migration.description}")
                        migration.down(conn)
                        
                        # 删除迁移记录
                        conn.execute("DELETE FROM schema_migrations WHERE version = ?", (migration.version,))
                        
                        logger.info(f"迁移 v{migration.version} 回滚成功")
                
                conn.commit()
                logger.info(f"已回滚到版本 {target_version}")
                return True
                
        except Exception as e:
            logger.error(f"回滚迁移失败: {e}")
            return False
    
    def get_current_version(self) -> int:
        """获取当前数据库版本"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                applied = self.get_applied_migrations(conn)
                return max(applied) if applied else 0
        except Exception:
            return 0


def initialize_database(db_path: Path) -> bool:
    """初始化数据库（便捷函数）"""
    manager = MigrationManager(db_path)
    return manager.apply_migrations()


def get_database_version(db_path: Path) -> int:
    """获取数据库版本（便捷函数）"""
    manager = MigrationManager(db_path)
    return manager.get_current_version()
