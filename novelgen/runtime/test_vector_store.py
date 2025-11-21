"""
向量存储操作单元测试
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from novelgen.models import StoryMemoryChunk
from novelgen.runtime.vector_store import (
    VectorStoreInterface, ChromaVectorStore, VectorStoreManager, 
    TextChunker, CHROMA_AVAILABLE
)


class TestTextChunker(unittest.TestCase):
    """文本分块器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.chunker = TextChunker(chunk_size=100, overlap=20)
    
    def test_short_text_chunking(self):
        """测试短文本分块"""
        text = "这是一个短文本，不需要分块。"
        chunks = self.chunker.chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)
    
    def test_long_text_chunking(self):
        """测试长文本分块"""
        text = "这是一个很长的文本。" * 20
        chunks = self.chunker.chunk_text(text)
        self.assertGreater(len(chunks), 1)
        
        # 检查每个块的大小
        for chunk in chunks:
            self.assertLessEqual(len(chunk), self.chunker.chunk_size + 10)  # 允许一些误差
    
    def test_sentence_boundary_chunking(self):
        """测试按句子边界分块"""
        text = "第一句话。第二句话！第三句话？第四句话。" * 5
        chunks = self.chunker.chunk_text(text)
        
        # 检查分块是否在句子边界
        for chunk in chunks[:-1]:  # 除了最后一块
            self.assertTrue(
                chunk.endswith('。') or chunk.endswith('！') or chunk.endswith('？'),
                f"分块应该在句子结尾: {chunk[-10:]}"
            )
    
    def test_create_chunks_from_scene(self):
        """测试从场景内容创建记忆块"""
        scene_content = "这是一个场景内容。包含多个句子。用于测试分块功能。"
        project_id = "test_project"
        chapter_index = 1
        scene_index = 2
        
        chunks = self.chunker.create_chunks_from_scene(
            scene_content, project_id, chapter_index, scene_index, "scene"
        )
        
        self.assertGreater(len(chunks), 0)
        
        for chunk in chunks:
            self.assertIsInstance(chunk, StoryMemoryChunk)
            self.assertEqual(chunk.project_id, project_id)
            self.assertEqual(chunk.chapter_index, chapter_index)
            self.assertEqual(chunk.scene_index, scene_index)
            self.assertEqual(chunk.content_type, "scene")
            self.assertIsNotNone(chunk.chunk_id)
            self.assertIsInstance(chunk.created_at, datetime)


@unittest.skipUnless(CHROMA_AVAILABLE, "ChromaDB未安装")
class TestChromaVectorStore(unittest.TestCase):
    """Chroma向量存储测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.persist_dir = Path(self.temp_dir) / "chroma_test"
        self.vector_store = ChromaVectorStore(self.persist_dir, "test_collection")
        self.vector_store.initialize()
    
    def tearDown(self):
        """清理测试环境"""
        self.vector_store.close()
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """测试初始化"""
        # 检查目录是否创建
        self.assertTrue(self.persist_dir.exists())
        
        # 检查健康状态
        self.assertTrue(self.vector_store.health_check())
    
    def test_add_single_chunk(self):
        """测试添加单个记忆块"""
        chunk = StoryMemoryChunk(
            chunk_id="test_chunk_1",
            project_id="test_project",
            content="测试内容",
            content_type="scene",
            created_at=datetime.now()
        )
        
        chunk_id = self.vector_store.add_chunk(chunk)
        self.assertEqual(chunk_id, "test_chunk_1")
        
        # 验证添加成功
        chunks = self.vector_store.get_chunks_by_project("test_project")
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_id, "test_chunk_1")
    
    def test_add_multiple_chunks(self):
        """测试批量添加记忆块"""
        chunks = [
            StoryMemoryChunk(
                chunk_id=f"test_chunk_{i}",
                project_id="test_project",
                content=f"测试内容{i}",
                content_type="scene",
                created_at=datetime.now()
            )
            for i in range(3)
        ]
        
        chunk_ids = self.vector_store.add_chunks(chunks)
        self.assertEqual(len(chunk_ids), 3)
        self.assertEqual(set(chunk_ids), {"test_chunk_0", "test_chunk_1", "test_chunk_2"})
        
        # 验证添加成功
        retrieved_chunks = self.vector_store.get_chunks_by_project("test_project")
        self.assertEqual(len(retrieved_chunks), 3)
    
    def test_search_similar(self):
        """测试搜索相似内容"""
        # 添加测试数据
        chunks = [
            StoryMemoryChunk(
                chunk_id="chunk_1",
                project_id="test_project",
                content="关于战斗的场景描述",
                content_type="scene",
                created_at=datetime.now()
            ),
            StoryMemoryChunk(
                chunk_id="chunk_2",
                project_id="test_project",
                content="关于对话的场景描述",
                content_type="dialogue",
                created_at=datetime.now()
            )
        ]
        
        self.vector_store.add_chunks(chunks)
        
        # 搜索相似内容
        results = self.vector_store.search_similar("战斗", "test_project", limit=5)
        self.assertGreater(len(results), 0)
        
        # 验证结果属于正确的项目
        for result in results:
            self.assertEqual(result.project_id, "test_project")
    
    def test_get_chunks_by_project(self):
        """测试根据项目获取记忆块"""
        # 添加不同项目的数据
        chunks_project1 = [
            StoryMemoryChunk(
                chunk_id=f"p1_chunk_{i}",
                project_id="project_1",
                content=f"项目1内容{i}",
                content_type="scene",
                created_at=datetime.now()
            )
            for i in range(2)
        ]
        
        chunks_project2 = [
            StoryMemoryChunk(
                chunk_id="p2_chunk_1",
                project_id="project_2",
                content="项目2内容",
                content_type="scene",
                created_at=datetime.now()
            )
        ]
        
        self.vector_store.add_chunks(chunks_project1)
        self.vector_store.add_chunks(chunks_project2)
        
        # 获取项目1的记忆块
        project1_chunks = self.vector_store.get_chunks_by_project("project_1")
        self.assertEqual(len(project1_chunks), 2)
        
        for chunk in project1_chunks:
            self.assertEqual(chunk.project_id, "project_1")
        
        # 获取项目2的记忆块
        project2_chunks = self.vector_store.get_chunks_by_project("project_2")
        self.assertEqual(len(project2_chunks), 1)
        self.assertEqual(project2_chunks[0].project_id, "project_2")
    
    def test_delete_chunks_by_project(self):
        """测试删除项目的记忆块"""
        # 添加测试数据
        chunks = [
            StoryMemoryChunk(
                chunk_id=f"chunk_{i}",
                project_id="test_project",
                content=f"内容{i}",
                content_type="scene",
                created_at=datetime.now()
            )
            for i in range(3)
        ]
        
        self.vector_store.add_chunks(chunks)
        
        # 验证数据存在
        before_delete = self.vector_store.get_chunks_by_project("test_project")
        self.assertEqual(len(before_delete), 3)
        
        # 删除项目数据
        result = self.vector_store.delete_chunks_by_project("test_project")
        self.assertTrue(result)
        
        # 验证数据已删除
        after_delete = self.vector_store.get_chunks_by_project("test_project")
        self.assertEqual(len(after_delete), 0)


class TestVectorStoreManager(unittest.TestCase):
    """向量存储管理器测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.persist_dir = Path(self.temp_dir) / "manager_test"
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_enabled_manager(self):
        """测试启用的向量存储管理器"""
        if not CHROMA_AVAILABLE:
            self.skipTest("ChromaDB未安装")
        
        manager = VectorStoreManager(self.persist_dir, enabled=True)
        
        # 应该成功初始化
        self.assertTrue(manager.is_enabled())
        self.assertTrue(manager.health_check())
        
        # 测试添加场景内容
        chunks = manager.add_scene_content(
            "这是一个测试场景内容，用于验证向量存储功能。",
            "test_project", 1, 1
        )
        
        if manager.is_enabled():  # 只有在向量存储可用时才验证
            self.assertGreater(len(chunks), 0)
            # 验证返回的是 StoryMemoryChunk 对象
            self.assertEqual(chunks[0].project_id, "test_project")
            self.assertEqual(chunks[0].chapter_index, 1)
            
            # 测试搜索
            results = manager.search_similar("测试", "test_project")
            self.assertGreater(len(results), 0)
        
        manager.close()
    
    def test_disabled_manager(self):
        """测试禁用的向量存储管理器"""
        manager = VectorStoreManager(self.persist_dir, enabled=False)
        
        # 应该处于禁用状态
        self.assertFalse(manager.is_enabled())
        
        # 测试添加操作（应该返回空列表但不报错）
        chunks = manager.add_scene_content("测试内容", "test_project")
        self.assertEqual(len(chunks), 0)
        
        # 测试搜索操作（应该返回空列表）
        results = manager.search_similar("测试", "test_project")
        self.assertEqual(len(results), 0)
        
        # 测试获取操作（应该返回空列表）
        chunks = manager.get_chunks_by_project("test_project")
        self.assertEqual(len(chunks), 0)
        
        manager.close()
    
    @unittest.skipUnless(CHROMA_AVAILABLE, "ChromaDB未安装")
    def test_fallback_handling(self):
        """测试降级处理"""
        # 使用无效路径创建管理器
        invalid_path = Path("/invalid/path/test")
        manager = VectorStoreManager(invalid_path, enabled=True)
        
        # 应该自动降级到禁用状态
        self.assertFalse(manager.is_enabled())
        
        # 操作应该正常返回但不报错
        chunks = manager.add_scene_content("测试内容", "test_project")
        self.assertEqual(len(chunks), 0)
        
        results = manager.search_similar("测试", "test_project")
        self.assertEqual(len(results), 0)
        
        manager.close()
    
    def test_scene_content_chunking(self):
        """测试场景内容自动分块"""
        if not CHROMA_AVAILABLE:
            self.skipTest("ChromaDB未安装")
        
        manager = VectorStoreManager(self.persist_dir, enabled=True)
        
        if not manager.is_enabled():
            self.skipTest("向量存储初始化失败")
        
        # 测试长内容分块（确保超过默认chunk_size=500）
        long_content = "这是一个很长的场景内容，用于测试文本分块功能。" * 50
        chunks = manager.add_scene_content(long_content, "test_project", 1, 1)
        
        self.assertGreater(len(chunks), 1)  # 长内容应该被分块
        chunk_count = len(chunks)
        
        # 验证每个块都有正确的元数据
        for chunk in chunks:
            self.assertEqual(chunk.project_id, "test_project")
            self.assertIsNotNone(chunk.content)
        
        # 验证分块结果
        retrieved_chunks = manager.get_chunks_by_project("test_project", 1)
        self.assertEqual(len(retrieved_chunks), chunk_count)
        
        for chunk in retrieved_chunks:
            self.assertEqual(chunk.project_id, "test_project")
            self.assertEqual(chunk.chapter_index, 1)
            self.assertEqual(chunk.scene_index, 1)
            self.assertEqual(chunk.content_type, "scene")
        
        manager.close()


class TestVectorStoreInterface(unittest.TestCase):
    """向量存储接口测试"""
    
    def test_interface_methods(self):
        """测试接口方法定义"""
        # 验证接口定义了所有必需的方法
        interface_methods = VectorStoreInterface.__abstractmethods__
        expected_methods = {
            'initialize', 'add_chunk', 'add_chunks', 'search_similar',
            'get_chunks_by_project', 'delete_chunks_by_project', 
            'health_check', 'close'
        }
        
        self.assertEqual(interface_methods, expected_methods)


if __name__ == '__main__':
    unittest.main()
