"""
Mem0 基础功能测试
测试 Mem0 客户端初始化和基本操作

开发者: Jamesenh, 开发时间: 2025-11-23
更新: 2025-11-25 - 移除降级测试，Mem0 现在是必需的记忆层
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

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
from novelgen.runtime.mem0_manager import Mem0Manager, Mem0InitializationError


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


def test_disabled_mem0_raises_exception():
    """测试禁用 Mem0 时应该抛出异常"""
    print("\n" + "="*60)
    print("测试 2: Mem0 禁用时应该抛出异常")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_config = ProjectConfig(project_dir=temp_dir)
        
        config = Mem0Config(enabled=False)
        
        # Mem0 禁用时应该抛出 Mem0InitializationError
        with pytest.raises(Mem0InitializationError) as exc_info:
            Mem0Manager(
                config=config,
                project_id="test_project",
                embedding_config=project_config.embedding_config
            )
        
        assert "未启用" in str(exc_info.value)
        print("\n✅ Mem0 禁用时正确抛出异常")


@pytest.mark.skipif(not HAS_REAL_API_KEY, reason="需要真实的 OpenAI API Key")
def test_user_preferences():
    """测试用户偏好存储和检索"""
    print("\n" + "="*60)
    print("测试 3: 用户偏好存储和检索")
    print("="*60)
    
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
            source="manual"
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


@pytest.mark.skipif(not HAS_REAL_API_KEY, reason="需要真实的 OpenAI API Key")
def test_entity_states():
    """测试实体状态管理"""
    print("\n" + "="*60)
    print("测试 4: 实体状态管理")
    print("="*60)
    
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


@pytest.mark.skipif(not HAS_REAL_API_KEY, reason="需要真实的 OpenAI API Key")
def test_scene_content_storage():
    """测试场景内容存储和检索"""
    print("\n" + "="*60)
    print("测试 5: 场景内容存储和检索")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_config = ProjectConfig(project_dir=temp_dir)
        
        config = Mem0Config(
            enabled=True,
            chroma_path=temp_dir,
            collection_name="test_mem0_scene",
        )
        
        manager = Mem0Manager(
            config=config,
            project_id="test_project",
            embedding_config=project_config.embedding_config
        )
        
        # 添加场景内容
        print("\n添加场景内容...")
        test_content = """
        张三站在山顶，望着远方的城市。风吹过他的头发，带来一丝凉意。
        他已经在这里等了三个小时，但约定的人始终没有出现。
        "也许这一切都是个陷阱，"他心想，"但我必须确认真相。"
        """
        
        chunks = manager.add_scene_content(
            content=test_content,
            chapter_index=1,
            scene_index=1,
            content_type="scene"
        )
        
        assert len(chunks) > 0, "应该创建至少一个记忆块"
        print(f"创建了 {len(chunks)} 个记忆块")
        
        # 搜索场景内容
        print("\n搜索场景内容...")
        results = manager.search_scene_content(
            query="张三在山顶等待",
            limit=5
        )
        
        print(f"检索到 {len(results)} 个相关结果")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.content[:100]}...")
        
        print("\n✅ 场景内容存储和检索成功")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("开始 Mem0 基础功能测试")
    print("="*60)
    
    try:
        test_mem0_initialization()
        test_disabled_mem0_raises_exception()
        
        if HAS_REAL_API_KEY:
            test_user_preferences()
            test_entity_states()
            test_scene_content_storage()
        else:
            print("\n⏭️ 跳过需要真实 API Key 的测试")
        
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
