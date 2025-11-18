"""
测试数据查询接口的基本功能
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager
from novelgen.models import EntityStateSnapshot, StoryMemoryChunk


class TestDatabaseQueryInterfaces:
    """测试数据库查询接口"""
    
    @pytest.fixture
    def db_manager(self):
        """创建临时数据库管理器"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = DatabaseManager(db_path=db_path, enabled=True)
            yield manager
            manager.close()
    
    def test_get_latest_entity_state(self, db_manager):
        """测试获取实体最新状态"""
        project_id = "test_project"
        entity_id = "char_001"
        
        # 保存多个状态快照
        for i in range(3):
            snapshot = EntityStateSnapshot(
                project_id=project_id,
                entity_type="character",
                entity_id=entity_id,
                chapter_index=i,
                scene_index=0,
                timestamp=datetime.now(),
                state_data={"level": i + 1, "status": f"chapter_{i}"},
                version=1
            )
            assert db_manager.save_entity_snapshot(snapshot)
        
        # 获取最新状态
        latest = db_manager.get_latest_entity_state(project_id, entity_id)
        assert latest is not None
        assert latest.entity_id == entity_id
        assert latest.state_data["level"] == 3  # 最新的是level 3
        
        # 测试不存在的实体
        non_exist = db_manager.get_latest_entity_state(project_id, "non_exist")
        assert non_exist is None
    
    def test_get_entity_timeline(self, db_manager):
        """测试获取实体时间线"""
        project_id = "test_project"
        entity_id = "char_001"
        
        # 保存5个章节的状态
        for i in range(5):
            snapshot = EntityStateSnapshot(
                project_id=project_id,
                entity_type="character",
                entity_id=entity_id,
                chapter_index=i,
                scene_index=0,
                timestamp=datetime.now(),
                state_data={"chapter": i},
                version=1
            )
            assert db_manager.save_entity_snapshot(snapshot)
        
        # 获取完整时间线
        timeline = db_manager.get_entity_timeline(project_id, entity_id)
        assert len(timeline) == 5
        assert timeline[0].chapter_index == 0
        assert timeline[-1].chapter_index == 4
        
        # 获取指定范围的时间线
        partial = db_manager.get_entity_timeline(project_id, entity_id, start_chapter=1, end_chapter=3)
        assert len(partial) == 3
        assert partial[0].chapter_index == 1
        assert partial[-1].chapter_index == 3
    
    def test_get_timeline_around(self, db_manager):
        """测试获取场景周围的时间线"""
        project_id = "test_project"
        
        # 保存多个实体在不同章节的状态
        for chapter in range(5):
            for entity_idx in range(2):
                snapshot = EntityStateSnapshot(
                    project_id=project_id,
                    entity_type="character",
                    entity_id=f"char_{entity_idx:03d}",
                    chapter_index=chapter,
                    scene_index=0,
                    timestamp=datetime.now(),
                    state_data={"chapter": chapter},
                    version=1
                )
                assert db_manager.save_entity_snapshot(snapshot)
        
        # 获取章节2周围的状态（context_window=1，即章节1-3）
        around = db_manager.get_timeline_around(project_id, chapter_index=2, context_window=1)
        assert len(around) > 0
        # 应该包含章节1, 2, 3的快照
        chapters = set(s.chapter_index for s in around)
        assert 1 in chapters
        assert 2 in chapters
        assert 3 in chapters
    
    def test_health_check(self, db_manager):
        """测试数据库健康检查"""
        assert db_manager.health_check() is True


class TestVectorStoreQueryInterfaces:
    """测试向量存储查询接口"""
    
    @pytest.fixture
    def vector_manager(self):
        """创建临时向量存储管理器"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VectorStoreManager(persist_directory=temp_dir, enabled=True)
            if not manager.is_enabled():
                pytest.skip("向量存储未启用（ChromaDB可能未安装或初始化失败）")
            yield manager
            manager.close()
    
    def test_search_memory_with_filters(self, vector_manager):
        """测试带过滤条件的记忆搜索"""
        project_id = "test_project"
        
        # 添加测试记忆块
        chunks = [
            StoryMemoryChunk(
                chunk_id="chunk_001",
                project_id=project_id,
                chapter_index=1,
                scene_index=0,
                content="主角在森林中遇到了神秘的老人",
                content_type="scene",
                entities_mentioned=["char_protagonist", "char_elder"],
                tags=["encounter", "forest"],
                created_at=datetime.now()
            ),
            StoryMemoryChunk(
                chunk_id="chunk_002",
                project_id=project_id,
                chapter_index=1,
                scene_index=1,
                content="老人给了主角一把古老的剑",
                content_type="scene",
                entities_mentioned=["char_protagonist", "char_elder"],
                tags=["gift", "weapon"],
                created_at=datetime.now()
            ),
            StoryMemoryChunk(
                chunk_id="chunk_003",
                project_id=project_id,
                chapter_index=2,
                scene_index=0,
                content="主角使用新剑击败了敌人",
                content_type="scene",
                entities_mentioned=["char_protagonist", "char_enemy"],
                tags=["battle", "weapon"],
                created_at=datetime.now()
            ),
        ]
        
        # 保存到向量存储
        for chunk in chunks:
            vector_manager.vector_store.add_chunk(chunk)
        
        # 测试基本搜索
        results = vector_manager.search_memory_with_filters("老人", project_id, limit=10)
        assert len(results) > 0
        
        # 测试带实体过滤的搜索
        results = vector_manager.search_memory_with_filters(
            "剑", project_id, entities=["char_protagonist"], limit=10
        )
        assert len(results) > 0
        # 所有结果都应该包含指定实体
        for result in results:
            assert "char_protagonist" in result.entities_mentioned
        
        # 测试带标签过滤的搜索
        results = vector_manager.search_memory_with_filters(
            "主角", project_id, tags=["weapon"], limit=10
        )
        assert len(results) > 0
        for result in results:
            assert "weapon" in result.tags
    
    def test_get_chunks_by_entities(self, vector_manager):
        """测试根据实体获取记忆块"""
        project_id = "test_project"
        
        # 添加测试记忆块
        chunks = [
            StoryMemoryChunk(
                chunk_id="chunk_004",
                project_id=project_id,
                chapter_index=1,
                scene_index=0,
                content="角色A和角色B在对话",
                content_type="scene",
                entities_mentioned=["char_a", "char_b"],
                created_at=datetime.now()
            ),
            StoryMemoryChunk(
                chunk_id="chunk_005",
                project_id=project_id,
                chapter_index=1,
                scene_index=1,
                content="角色A独自思考",
                content_type="scene",
                entities_mentioned=["char_a"],
                created_at=datetime.now()
            ),
            StoryMemoryChunk(
                chunk_id="chunk_006",
                project_id=project_id,
                chapter_index=2,
                scene_index=0,
                content="角色C登场",
                content_type="scene",
                entities_mentioned=["char_c"],
                created_at=datetime.now()
            ),
        ]
        
        for chunk in chunks:
            vector_manager.vector_store.add_chunk(chunk)
        
        # 获取包含char_a的记忆块
        results = vector_manager.get_chunks_by_entities(project_id, ["char_a"])
        assert len(results) == 2
        for result in results:
            assert "char_a" in result.entities_mentioned
        
        # 获取包含多个实体之一的记忆块
        results = vector_manager.get_chunks_by_entities(project_id, ["char_a", "char_c"])
        assert len(results) == 3  # 应该包含所有提及这些实体的记忆块
        
        # 指定章节过滤
        results = vector_manager.get_chunks_by_entities(project_id, ["char_a"], chapter_index=1)
        assert len(results) == 2
        assert all(r.chapter_index == 1 for r in results)
    
    def test_health_check(self, vector_manager):
        """测试向量存储健康检查"""
        assert vector_manager.health_check() is True


def test_integration_query_flow():
    """集成测试：完整的查询流程"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "test.db"
        vector_path = temp_path / "chroma"
        
        # 初始化管理器
        db_manager = DatabaseManager(db_path=db_path, enabled=True)
        
        try:
            import chromadb
            vector_manager = VectorStoreManager(persist_directory=vector_path, enabled=True)
        except ImportError:
            pytest.skip("ChromaDB未安装")
        
        if not vector_manager.is_enabled():
            pytest.skip("向量存储初始化失败")
        
        project_id = "integration_test"
        
        # 1. 保存实体状态
        snapshot = EntityStateSnapshot(
            project_id=project_id,
            entity_type="character",
            entity_id="char_hero",
            chapter_index=1,
            scene_index=0,
            timestamp=datetime.now(),
            state_data={"name": "英雄", "level": 10},
            version=1
        )
        assert db_manager.save_entity_snapshot(snapshot)
        
        # 2. 保存记忆块
        chunk = StoryMemoryChunk(
            chunk_id="integration_chunk",
            project_id=project_id,
            chapter_index=1,
            scene_index=0,
            content="英雄在村庄中接受了任务",
            content_type="scene",
            entities_mentioned=["char_hero"],
            tags=["quest"],
            created_at=datetime.now()
        )
        vector_manager.vector_store.add_chunk(chunk)
        
        # 3. 查询实体最新状态
        latest = db_manager.get_latest_entity_state(project_id, "char_hero")
        assert latest is not None
        assert latest.state_data["name"] == "英雄"
        
        # 4. 查询相关记忆块
        memories = vector_manager.get_chunks_by_entities(project_id, ["char_hero"])
        assert len(memories) > 0
        
        # 5. 健康检查
        assert db_manager.health_check()
        assert vector_manager.health_check()
        
        # 清理
        db_manager.close()
        vector_manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
