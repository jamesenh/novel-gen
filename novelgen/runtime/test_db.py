"""
数据库操作单元测试
"""
import unittest
import tempfile
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import json

from novelgen.models import EntityStateSnapshot, StoryMemoryChunk
from novelgen.runtime.db import SQLiteDatabase, DatabaseManager
from novelgen.runtime.db_migrations import MigrationManager, initialize_database


class TestSQLiteDatabase(unittest.TestCase):
    """SQLite数据库测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = SQLiteDatabase(self.db_path)
        self.db.initialize()
    
    def tearDown(self):
        """清理测试环境"""
        self.db.close()
        shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """测试数据库初始化"""
        # 检查数据库文件是否存在
        self.assertTrue(self.db_path.exists())
        
        # 检查表是否创建成功
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('entity_snapshots', tables)
            self.assertIn('memory_chunks', tables)
            self.assertIn('schema_migrations', tables)
    
    def test_save_entity_snapshot(self):
        """测试保存实体状态快照"""
        snapshot = EntityStateSnapshot(
            project_id="test_project",
            entity_type="character",
            entity_id="test_character",
            chapter_index=1,
            scene_index=2,
            timestamp=datetime.now(),
            state_data={"health": 100, "level": 5},
            version=1
        )
        
        # 保存快照
        result = self.db.save_entity_snapshot(snapshot)
        self.assertTrue(result)
        
        # 验证数据已保存
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM entity_snapshots WHERE project_id = ?", 
                                ("test_project",))
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
    
    def test_get_entity_snapshots(self):
        """测试获取实体状态快照"""
        # 创建测试数据
        snapshot1 = EntityStateSnapshot(
            project_id="test_project",
            entity_type="character",
            entity_id="character1",
            timestamp=datetime.now(),
            state_data={"health": 100}
        )
        snapshot2 = EntityStateSnapshot(
            project_id="test_project",
            entity_type="character", 
            entity_id="character2",
            timestamp=datetime.now(),
            state_data={"health": 80}
        )
        
        # 保存数据
        self.db.save_entity_snapshot(snapshot1)
        self.db.save_entity_snapshot(snapshot2)
        
        # 获取所有快照
        all_snapshots = self.db.get_entity_snapshots("test_project")
        self.assertEqual(len(all_snapshots), 2)
        
        # 获取特定实体快照
        character1_snapshots = self.db.get_entity_snapshots("test_project", "character1")
        self.assertEqual(len(character1_snapshots), 1)
        self.assertEqual(character1_snapshots[0].entity_id, "character1")
    
    def test_save_memory_chunk(self):
        """测试保存记忆块"""
        chunk = StoryMemoryChunk(
            chunk_id="test_chunk_1",
            project_id="test_project",
            chapter_index=1,
            scene_index=1,
            content="这是一个测试场景内容",
            content_type="scene",
            entities_mentioned=["character1"],
            tags=["test", "scene"],
            created_at=datetime.now()
        )
        
        # 保存记忆块
        result = self.db.save_memory_chunk(chunk)
        self.assertTrue(result)
        
        # 验证数据已保存
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM memory_chunks WHERE chunk_id = ?", 
                                ("test_chunk_1",))
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
    
    def test_get_memory_chunks(self):
        """测试获取记忆块"""
        # 创建测试数据
        chunk1 = StoryMemoryChunk(
            chunk_id="chunk_1",
            project_id="test_project",
            chapter_index=1,
            content="第一章内容",
            content_type="scene",
            created_at=datetime.now()
        )
        chunk2 = StoryMemoryChunk(
            chunk_id="chunk_2",
            project_id="test_project",
            chapter_index=2,
            content="第二章内容",
            content_type="dialogue",
            created_at=datetime.now()
        )
        
        # 保存数据
        self.db.save_memory_chunk(chunk1)
        self.db.save_memory_chunk(chunk2)
        
        # 获取所有记忆块
        all_chunks = self.db.get_memory_chunks("test_project")
        self.assertEqual(len(all_chunks), 2)
        
        # 获取特定章节的记忆块
        chapter1_chunks = self.db.get_memory_chunks("test_project", 1)
        self.assertEqual(len(chapter1_chunks), 1)
        self.assertEqual(chapter1_chunks[0].chapter_index, 1)
    
    def test_health_check(self):
        """测试健康检查"""
        # 正常情况下应该返回True
        self.assertTrue(self.db.health_check())
        
        # 关闭连接后应该返回False
        self.db.close()
        self.assertFalse(self.db.health_check())


class TestDatabaseManager(unittest.TestCase):
    """数据库管理器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_manager.db"
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_enabled_manager(self):
        """测试启用的数据库管理器"""
        manager = DatabaseManager(self.db_path, enabled=True)
        
        # 应该成功初始化
        self.assertTrue(manager.is_enabled())
        self.assertTrue(manager.health_check())
        
        # 测试保存操作
        snapshot = EntityStateSnapshot(
            project_id="test_project",
            entity_type="character",
            entity_id="test_character",
            timestamp=datetime.now(),
            state_data={"test": "data"}
        )
        
        result = manager.save_entity_snapshot(snapshot)
        self.assertTrue(result)
        
        # 测试获取操作
        snapshots = manager.get_entity_snapshots("test_project")
        self.assertEqual(len(snapshots), 1)
        
        manager.close()
    
    def test_disabled_manager(self):
        """测试禁用的数据库管理器"""
        manager = DatabaseManager(self.db_path, enabled=False)
        
        # 应该处于禁用状态
        self.assertFalse(manager.is_enabled())
        
        # 测试保存操作（应该返回True但不实际保存）
        snapshot = EntityStateSnapshot(
            project_id="test_project",
            entity_type="character",
            entity_id="test_character",
            timestamp=datetime.now(),
            state_data={"test": "data"}
        )
        
        result = manager.save_entity_snapshot(snapshot)
        self.assertTrue(result)  # 降级模式下应该返回True
        
        # 测试获取操作（应该返回空列表）
        snapshots = manager.get_entity_snapshots("test_project")
        self.assertEqual(len(snapshots), 0)
        
        manager.close()
    
    def test_fallback_handling(self):
        """测试降级处理"""
        # 使用无效路径创建管理器
        invalid_path = Path("/invalid/path/test.db")
        manager = DatabaseManager(invalid_path, enabled=True)
        
        # 应该自动降级到禁用状态
        self.assertFalse(manager.is_enabled())
        
        # 操作应该正常返回但不报错
        snapshot = EntityStateSnapshot(
            project_id="test_project",
            entity_type="character",
            entity_id="test_character",
            timestamp=datetime.now(),
            state_data={"test": "data"}
        )
        
        result = manager.save_entity_snapshot(snapshot)
        self.assertTrue(result)
        
        snapshots = manager.get_entity_snapshots("test_project")
        self.assertEqual(len(snapshots), 0)


class TestMigrations(unittest.TestCase):
    """迁移测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_migrations.db"
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_apply_migrations(self):
        """测试应用迁移"""
        manager = MigrationManager(self.db_path)
        
        # 初始版本应该是0
        self.assertEqual(manager.get_current_version(), 0)
        
        # 应用迁移
        result = manager.apply_migrations()
        self.assertTrue(result)
        
        # 版本应该更新
        self.assertEqual(manager.get_current_version(), 1)
        
        # 表应该被创建
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('entity_snapshots', tables)
            self.assertIn('memory_chunks', tables)
    
    def test_initialize_database_function(self):
        """测试数据库初始化便捷函数"""
        result = initialize_database(self.db_path)
        self.assertTrue(result)
        
        # 数据库文件应该存在
        self.assertTrue(self.db_path.exists())


if __name__ == '__main__':
    unittest.main()
