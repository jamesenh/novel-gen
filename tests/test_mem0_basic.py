"""
Mem0 基础功能测试
测试 Mem0 客户端初始化和基本操作

开发者: Jamesenh, 开发时间: 2025-11-23
"""
import os
import sys
import tempfile
from pathlib import Path

# 检查是否有真实的 API Key（Mem0 需要真实 API 来生成 embeddings）
HAS_REAL_API_KEY = bool(os.getenv("OPENAI_API_KEY") or os.getenv("EMBEDDING_API_KEY"))

# 如果没有真实 API Key，设置一个假的（仅用于初始化测试）
if not HAS_REAL_API_KEY:
    os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"
    print("\n⚠️ 警告: 未检测到真实的 OpenAI API Key")
    print("   某些测试（如添加/检索记忆）将被跳过")
    print("   如需完整测试，请在 .env 文件中设置 OPENAI_API_KEY 或 EMBEDDING_API_KEY\n")

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novelgen.models import Mem0Config
from novelgen.config import ProjectConfig
from novelgen.runtime.mem0_manager import Mem0Manager


def test_mem0_initialization():
    """测试 Mem0 客户端初始化"""
    print("\n" + "="*60)
    print("测试 1: Mem0 客户端初始化")
    print("="*60)
    
    # 创建临时目录用于 ChromaDB
    with tempfile.TemporaryDirectory() as temp_dir:
        # 使用 ProjectConfig 读取配置（从 .env 文件）
        project_config = ProjectConfig(project_dir=temp_dir)
        
        config = Mem0Config(
            enabled=True,
            chroma_path=temp_dir,
            collection_name="test_mem0",
        )
        
        manager = Mem0Manager(
            config=config,
            project_id="test_project",
            embedding_config=project_config.embedding_config
        )
        
        # 健康检查
        health = manager.health_check()
        print(f"\n健康检查结果: {health}")
        
        assert health["enabled"] is True, "Mem0 应该被启用"
        print("✅ Mem0 客户端初始化成功")


def test_user_preferences():
    """测试用户偏好存储和检索"""
    print("\n" + "="*60)
    print("测试 2: 用户偏好存储和检索")
    print("="*60)
    
    if not HAS_REAL_API_KEY:
        print("\n⏭️  跳过测试：需要真实的 OpenAI API Key 来生成 embeddings")
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 使用 ProjectConfig 读取配置（从 .env 文件）
        project_config = ProjectConfig(project_dir=temp_dir)
        
        config = Mem0Config(
            enabled=True,
            chroma_path=temp_dir,
            collection_name="test_mem0_user",
        )
        
        manager = Mem0Manager(
            config=config,
            project_id="test_project",
            embedding_config=project_config.embedding_config
        )
        
        # 添加用户偏好
        print("\n添加用户偏好...")
        success = manager.add_user_preference(
            preference_type="writing_style",
            content="喜欢使用细腻的心理描写，避免过于直白的叙述",
            source="revision"
        )
        assert success, "添加用户偏好应该成功"
        
        success = manager.add_user_preference(
            preference_type="tone",
            content="整体基调偏向悬疑和紧张感",
            source="feedback"
        )
        assert success, "添加用户偏好应该成功"
        
        # 检索用户偏好
        print("\n检索用户偏好...")
        preferences = manager.search_user_preferences(
            query="写作风格",
            limit=5
        )
        
        print(f"\n检索到 {len(preferences)} 条偏好:")
        for i, pref in enumerate(preferences, 1):
            print(f"{i}. {pref.get('memory', 'N/A')}")
        
        assert len(preferences) > 0, "应该检索到至少一条偏好"
        print("\n✅ 用户偏好存储和检索成功")


def test_entity_states():
    """测试实体状态管理"""
    print("\n" + "="*60)
    print("测试 3: 实体状态管理")
    print("="*60)
    
    if not HAS_REAL_API_KEY:
        print("\n⏭️  跳过测试：需要真实的 OpenAI API Key 来生成 embeddings")
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 使用 ProjectConfig 读取配置（从 .env 文件）
        project_config = ProjectConfig(project_dir=temp_dir)
        
        config = Mem0Config(
            enabled=True,
            chroma_path=temp_dir,
            collection_name="test_mem0_entity",
        )
        
        manager = Mem0Manager(
            config=config,
            project_id="test_project",
            embedding_config=project_config.embedding_config
        )
        
        # 添加实体状态
        print("\n添加角色状态...")
        success = manager.add_entity_state(
            entity_id="张三",
            entity_type="character",
            state_description="在第一章中首次登场，表现出强烈的好奇心和探索欲望",
            chapter_index=1,
            scene_index=1,
        )
        assert success, "添加实体状态应该成功"
        
        success = manager.add_entity_state(
            entity_id="张三",
            entity_type="character",
            state_description="在第二章中经历了重大挫折，变得更加谨慎和内敛",
            chapter_index=2,
            scene_index=3,
        )
        assert success, "添加实体状态应该成功"
        
        # 检索实体状态
        print("\n检索角色状态...")
        states = manager.get_entity_state(
            entity_id="张三",
            query="张三的当前状态",
            limit=3
        )
        
        print(f"\n检索到 {len(states)} 条状态:")
        for i, state in enumerate(states, 1):
            print(f"{i}. {state.get('memory', 'N/A')}")
        
        assert len(states) > 0, "应该检索到至少一条状态"
        print("\n✅ 实体状态管理成功")


def test_disabled_mem0():
    """测试禁用 Mem0 的降级行为"""
    print("\n" + "="*60)
    print("测试 4: Mem0 禁用时的降级行为")
    print("="*60)
    
    # 使用 ProjectConfig 读取配置（从 .env 文件）
    with tempfile.TemporaryDirectory() as temp_dir:
        project_config = ProjectConfig(project_dir=temp_dir)
        
        config = Mem0Config(enabled=False)
        
        manager = Mem0Manager(
            config=config,
            project_id="test_project",
            embedding_config=project_config.embedding_config
        )
        
        health = manager.health_check()
        print(f"\n健康检查结果: {health}")
        assert health["enabled"] is False, "Mem0 应该被禁用"
        
        # 尝试操作应该安全失败
        success = manager.add_user_preference(
            preference_type="writing_style",
            content="测试内容",
            source="test"
        )
        assert success is False, "禁用时添加操作应该返回 False"
        
        preferences = manager.search_user_preferences()
        assert len(preferences) == 0, "禁用时检索应该返回空列表"
        
        print("\n✅ Mem0 禁用时的降级行为正确")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("开始 Mem0 基础功能测试")
    print("="*60)
    
    try:
        test_mem0_initialization()
        test_user_preferences()
        test_entity_states()
        test_disabled_mem0()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

