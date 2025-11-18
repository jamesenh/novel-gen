"""
编排器持久化集成测试
验证数据库和向量存储的集成是否正常工作
"""
import os
import unittest
import tempfile
import shutil
from pathlib import Path

from novelgen.runtime.orchestrator import NovelOrchestrator
from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager


class TestOrchestratorPersistenceIntegration(unittest.TestCase):
    """编排器持久化集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_name = "test_persistence_project"
        self.orchestrator = NovelOrchestrator(
            project_name=self.project_name,
            base_dir=self.temp_dir,
            verbose=False
        )
    
    def tearDown(self):
        """清理测试环境"""
        self.orchestrator.close()
        shutil.rmtree(self.temp_dir)
    
    def test_persistence_initialization(self):
        """测试持久化初始化"""
        # 验证数据库管理器是否正确初始化
        self.assertIsNotNone(self.orchestrator.db_manager)
        
        # 验证向量管理器是否正确初始化（可能降级）
        self.assertIsNotNone(self.orchestrator.vector_manager)
        
        # 验证健康检查
        if self.orchestrator.db_manager.is_enabled():
            self.assertTrue(self.orchestrator.db_manager.health_check())
        
        if self.orchestrator.vector_manager.is_enabled():
            self.assertTrue(self.orchestrator.vector_manager.health_check())
    
    def test_step1_world_persistence(self):
        """测试步骤1世界观持久化"""
        world = self.orchestrator.step1_create_world(
            "测试世界：一个充满魔法的奇幻世界", 
            force=True
        )
        
        # 验证JSON文件保存
        self.assertTrue(Path(self.orchestrator.config.world_file).exists())
        
        # 验证数据库保存（如果启用）
        if self.orchestrator.db_manager.is_enabled():
            snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                self.project_name, "main_world"
            )
            self.assertGreater(len(snapshots), 0)
            self.assertEqual(snapshots[0].entity_type, "world")
            self.assertEqual(snapshots[0].entity_id, "main_world")
    
    def test_step2_theme_persistence(self):
        """测试步骤2主题冲突持久化"""
        # 先创建世界观
        self.orchestrator.step1_create_world("测试世界", force=True)
        
        theme = self.orchestrator.step2_create_theme_conflict(
            "关于勇气与成长的故事", 
            force=True
        )
        
        # 验证JSON文件保存
        self.assertTrue(Path(self.orchestrator.config.theme_conflict_file).exists())
        
        # 验证数据库保存（如果启用）
        if self.orchestrator.db_manager.is_enabled():
            snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                self.project_name, "main_theme"
            )
            self.assertGreater(len(snapshots), 0)
            self.assertEqual(snapshots[0].entity_type, "theme")
    
    def test_step3_characters_persistence(self):
        """测试步骤3角色持久化"""
        # 准备前置数据
        self.orchestrator.step1_create_world("测试世界", force=True)
        self.orchestrator.step2_create_theme_conflict("测试主题", force=True)
        
        characters = self.orchestrator.step3_create_characters(force=True)
        
        # 验证JSON文件保存
        self.assertTrue(Path(self.orchestrator.config.characters_file).exists())
        
        # 验证数据库保存（如果启用）
        if self.orchestrator.db_manager.is_enabled():
            # 检查角色集合
            snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                self.project_name, "main_characters"
            )
            self.assertGreater(len(snapshots), 0)
            
            # 检查单个角色
            for character in characters.characters:
                character_snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                    self.project_name, character.character_id
                )
                self.assertGreater(len(character_snapshots), 0)
    
    def test_step4_outline_persistence(self):
        """测试步骤4大纲持久化"""
        # 准备前置数据
        self.orchestrator.step1_create_world("测试世界", force=True)
        self.orchestrator.step2_create_theme_conflict("测试主题", force=True)
        self.orchestrator.step3_create_characters(force=True)
        
        outline = self.orchestrator.step4_create_outline(num_chapters=5, force=True)
        
        # 验证JSON文件保存
        self.assertTrue(Path(self.orchestrator.config.outline_file).exists())
        
        # 验证数据库保存（如果启用）
        if self.orchestrator.db_manager.is_enabled():
            # 检查大纲
            snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                self.project_name, "main_outline"
            )
            self.assertGreater(len(snapshots), 0)
            
            # 检查章节
            for chapter in outline.chapters:
                chapter_snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                    self.project_name, f"chapter_{chapter.chapter_number}"
                )
                self.assertGreater(len(chapter_snapshots), 0)
    
    def test_step5_chapter_plan_persistence(self):
        """测试步骤5章节计划持久化"""
        # 准备前置数据
        self.orchestrator.step1_create_world("测试世界", force=True)
        self.orchestrator.step2_create_theme_conflict("测试主题", force=True)
        self.orchestrator.step3_create_characters(force=True)
        self.orchestrator.step4_create_outline(num_chapters=3, force=True)
        
        chapter_plan = self.orchestrator.step5_create_chapter_plan(1, force=True)
        
        # 验证JSON文件保存
        plan_file = Path(self.orchestrator.config.chapters_dir) / "chapter_001_plan.json"
        self.assertTrue(plan_file.exists())
        
        # 验证数据库保存（如果启用）
        if self.orchestrator.db_manager.is_enabled():
            snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                self.project_name, "chapter_1_plan"
            )
            self.assertGreater(len(snapshots), 0)
            self.assertEqual(snapshots[0].entity_type, "chapter_plan")
    
    def test_step6_chapter_text_persistence(self):
        """测试步骤6章节文本持久化（包括向量存储）"""
        # 准备前置数据
        self.orchestrator.step1_create_world("测试世界", force=True)
        self.orchestrator.step2_create_theme_conflict("测试主题", force=True)
        self.orchestrator.step3_create_characters(force=True)
        self.orchestrator.step4_create_outline(num_chapters=3, force=True)
        self.orchestrator.step5_create_chapter_plan(1, force=True)
        
        chapter = self.orchestrator.step6_generate_chapter_text(1, force=True)
        
        # 验证JSON文件保存
        chapter_file = Path(self.orchestrator.config.chapters_dir) / "chapter_001.json"
        self.assertTrue(chapter_file.exists())
        
        # 验证数据库保存（如果启用）
        if self.orchestrator.db_manager.is_enabled():
            snapshots = self.orchestrator.db_manager.get_entity_snapshots(
                self.project_name, "chapter_1_text"
            )
            self.assertGreater(len(snapshots), 0)
            self.assertEqual(snapshots[0].entity_type, "chapter_text")
        
        # 验证向量存储保存（如果启用）
        if self.orchestrator.vector_manager.is_enabled():
            chunks = self.orchestrator.vector_manager.get_chunks_by_project(
                self.project_name, 1
            )
            # 应该有场景内容被保存到向量存储
            self.assertGreater(len(chunks), 0)
    
    def test_persistence_fallback(self):
        """测试持久化降级处理"""
        # 创建一个禁用持久化的编排器
        disabled_orchestrator = NovelOrchestrator(
            project_name="disabled_project",
            base_dir=self.temp_dir,
            verbose=False
        )

        # 手动禁用持久化
        disabled_orchestrator.db_manager = DatabaseManager(":memory:", enabled=False)
        disabled_orchestrator.vector_manager = VectorStoreManager(":memory:", enabled=False)

        # 执行步骤应该不会报错
        try:
            world = disabled_orchestrator.step1_create_world("测试世界", force=True)
            self.assertIsNotNone(world)

            # 验证JSON文件仍然保存
            self.assertTrue(Path(disabled_orchestrator.config.world_file).exists())

        except Exception as e:
            self.fail(f"降级模式下执行失败: {e}")
        finally:
            disabled_orchestrator.close()

    def test_custom_persistence_paths_via_env(self):
        """测试通过环境变量配置数据库和向量存储路径"""
        original_db = os.getenv("NOVELGEN_DB_PATH")
        original_vector_dir = os.getenv("NOVELGEN_VECTOR_STORE_DIR")
        original_persistence = os.getenv("NOVELGEN_PERSISTENCE_ENABLED")
        original_vector_enabled = os.getenv("NOVELGEN_VECTOR_STORE_ENABLED")

        try:
            os.environ["NOVELGEN_DB_PATH"] = "custom_data/novel.db"
            os.environ["NOVELGEN_VECTOR_STORE_DIR"] = "custom_vectors"
            os.environ["NOVELGEN_PERSISTENCE_ENABLED"] = "true"
            os.environ["NOVELGEN_VECTOR_STORE_ENABLED"] = "true"

            orchestrator = NovelOrchestrator(
                project_name="custom_paths_project",
                base_dir=self.temp_dir,
                verbose=False,
            )

            # 验证数据库路径解析（仅在启用时检查）
            self.assertIsNotNone(orchestrator.db_manager)
            if orchestrator.db_manager.is_enabled():
                expected_db = Path(orchestrator.project_dir) / "custom_data" / "novel.db"
                self.assertEqual(orchestrator.db_manager.db.db_path, expected_db)

            # 验证向量存储目录解析（仅在启用时检查）
            if orchestrator.vector_manager and orchestrator.vector_manager.is_enabled():
                expected_vectors = Path(orchestrator.project_dir) / "custom_vectors"
                self.assertEqual(
                    orchestrator.vector_manager.vector_store.persist_directory,
                    expected_vectors,
                )

            orchestrator.close()
        finally:
            # 恢复环境变量
            if original_db is None:
                os.environ.pop("NOVELGEN_DB_PATH", None)
            else:
                os.environ["NOVELGEN_DB_PATH"] = original_db

            if original_vector_dir is None:
                os.environ.pop("NOVELGEN_VECTOR_STORE_DIR", None)
            else:
                os.environ["NOVELGEN_VECTOR_STORE_DIR"] = original_vector_dir

            if original_persistence is None:
                os.environ.pop("NOVELGEN_PERSISTENCE_ENABLED", None)
            else:
                os.environ["NOVELGEN_PERSISTENCE_ENABLED"] = original_persistence

            if original_vector_enabled is None:
                os.environ.pop("NOVELGEN_VECTOR_STORE_ENABLED", None)
            else:
                os.environ["NOVELGEN_VECTOR_STORE_ENABLED"] = original_vector_enabled

    def test_close_method(self):
        """测试关闭方法"""
        # 测试关闭方法不会抛出异常
        try:
            self.orchestrator.close()
        except Exception as e:
            self.fail(f"关闭方法执行失败: {e}")


if __name__ == '__main__':
    unittest.main()
