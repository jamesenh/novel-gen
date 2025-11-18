"""
测试记忆上下文检索链
验证记忆检索功能的正确性
"""
import os
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from novelgen.models import (
    ScenePlan,
    CharactersConfig,
    Character,
    EntityStateSnapshot,
    StoryMemoryChunk,
    SceneMemoryContext
)
from novelgen.config import LLMConfig
from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager
from novelgen.chains.memory_context_chain import retrieve_scene_memory_context
from novelgen.runtime.memory_tools import (
    search_story_memory_tool,
    get_entity_state_tool,
    get_recent_timeline_tool
)


@pytest.fixture
def temp_project_dir():
    """创建临时项目目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def db_manager(temp_project_dir):
    """创建测试用数据库管理器"""
    db_path = Path(temp_project_dir) / "test.db"
    manager = DatabaseManager(db_path, enabled=True)
    yield manager
    manager.close()


@pytest.fixture
def vector_manager(temp_project_dir):
    """创建测试用向量存储管理器"""
    vector_dir = Path(temp_project_dir) / "vectors"
    manager = VectorStoreManager(vector_dir, enabled=True)
    yield manager
    manager.close()


@pytest.fixture
def sample_characters_config():
    """创建示例角色配置"""
    protagonist = Character(
        name="张三",
        role="主角",
        age=25,
        gender="男",
        appearance="高大英俊",
        personality="勇敢正直",
        background="普通家庭出身",
        motivation="成为英雄"
    )
    return CharactersConfig(protagonist=protagonist)


@pytest.fixture
def sample_scene_plan():
    """创建示例场景计划"""
    return ScenePlan(
        scene_number=1,
        location="城市广场",
        characters=["张三", "李四"],
        purpose="主角遇到神秘人物",
        key_actions=["张三在广场散步", "李四突然出现", "两人开始对话"],
        estimated_words=500,
        scene_type="对话",
        intensity="中"
    )


def test_memory_tools_with_empty_data(db_manager, vector_manager):
    """测试在空数据库情况下的降级处理"""
    project_id = "test_project"
    
    # 测试搜索故事记忆
    memories = search_story_memory_tool(
        db_manager=db_manager,
        vector_manager=vector_manager,
        project_id=project_id,
        query="测试查询",
        top_k=5
    )
    assert isinstance(memories, list)
    assert len(memories) == 0
    
    # 测试获取实体状态
    state = get_entity_state_tool(
        db_manager=db_manager,
        project_id=project_id,
        entity_id="character:张三"
    )
    assert state is None
    
    # 测试获取时间线
    timeline = get_recent_timeline_tool(
        db_manager=db_manager,
        project_id=project_id,
        chapter_index=1
    )
    assert isinstance(timeline, list)
    assert len(timeline) == 0


def test_memory_tools_with_test_data(db_manager, vector_manager):
    """测试在有数据的情况下的记忆检索"""
    project_id = "test_project"
    
    # 准备测试数据：添加一些记忆块
    test_chunks = [
        StoryMemoryChunk(
            chunk_id="chunk_1",
            project_id=project_id,
            chapter_index=1,
            scene_index=1,
            content="张三在城市广场遇到了李四，两人开始了一段重要的对话。",
            content_type="scene",
            entities_mentioned=["张三", "李四"],
            tags=["对话", "初次见面"],
            created_at=datetime.now()
        ),
        StoryMemoryChunk(
            chunk_id="chunk_2",
            project_id=project_id,
            chapter_index=1,
            scene_index=2,
            content="李四向张三透露了一个重要的秘密。",
            content_type="dialogue",
            entities_mentioned=["张三", "李四"],
            tags=["秘密", "对话"],
            created_at=datetime.now()
        )
    ]
    
    # 添加到数据库和向量存储
    for chunk in test_chunks:
        db_manager.save_memory_chunk(chunk)
    
    # 添加到向量存储（实际会生成embedding）
    vector_manager.vector_store.add_chunks(test_chunks)
    
    # 测试搜索
    memories = search_story_memory_tool(
        db_manager=db_manager,
        vector_manager=vector_manager,
        project_id=project_id,
        query="张三和李四的对话",
        top_k=5
    )
    
    assert isinstance(memories, list)
    # 注意：实际返回数量取决于向量检索结果


def test_retrieve_scene_memory_context_basic(
    db_manager, 
    vector_manager, 
    sample_scene_plan, 
    sample_characters_config,
    temp_project_dir
):
    """测试基本的场景记忆上下文检索"""
    project_id = "test_project"
    chapter_index = 1
    scene_index = 1
    
    # 调用检索函数
    context = retrieve_scene_memory_context(
        scene_plan=sample_scene_plan,
        characters_config=sample_characters_config,
        project_id=project_id,
        chapter_index=chapter_index,
        scene_index=scene_index,
        db_manager=db_manager,
        vector_manager=vector_manager,
        output_dir=temp_project_dir
    )
    
    # 验证返回的对象类型
    assert isinstance(context, SceneMemoryContext)
    assert context.project_id == project_id
    assert context.chapter_index == chapter_index
    assert context.scene_index == scene_index
    
    # 验证字段存在
    assert isinstance(context.entity_states, list)
    assert isinstance(context.relevant_memories, list)
    assert isinstance(context.retrieval_timestamp, datetime)
    
    # 验证JSON文件已生成
    json_file = Path(temp_project_dir) / f"scene_{chapter_index}_{scene_index}_memory.json"
    assert json_file.exists()
    
    # 验证JSON内容
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["project_id"] == project_id
        assert data["chapter_index"] == chapter_index
        assert data["scene_index"] == scene_index


def test_retrieve_with_disabled_persistence(
    sample_scene_plan, 
    sample_characters_config,
    temp_project_dir
):
    """测试在持久化禁用的情况下的降级处理"""
    project_id = "test_project"
    
    # 创建禁用持久化的管理器
    db_manager = DatabaseManager(
        db_path=Path(temp_project_dir) / "test.db",
        enabled=False
    )
    vector_manager = VectorStoreManager(
        persist_directory=Path(temp_project_dir) / "vectors",
        enabled=False
    )
    
    # 调用检索函数，应该成功执行但返回空数据
    context = retrieve_scene_memory_context(
        scene_plan=sample_scene_plan,
        characters_config=sample_characters_config,
        project_id=project_id,
        chapter_index=1,
        scene_index=1,
        db_manager=db_manager,
        vector_manager=vector_manager,
        output_dir=temp_project_dir
    )
    
    # 验证降级处理正常
    assert isinstance(context, SceneMemoryContext)
    assert len(context.entity_states) == 0
    assert len(context.relevant_memories) == 0
    
    db_manager.close()
    vector_manager.close()


def test_chain_with_test_data_and_states(db_manager, vector_manager, sample_scene_plan, sample_characters_config, temp_project_dir):
    """测试在有记忆和实体状态数据时的完整检索流程"""
    project_id = "test_project"
    chapter_index = 2
    scene_index = 3
    
    # 准备测试数据：记忆块
    test_chunk = StoryMemoryChunk(
        chunk_id="chunk_3",
        project_id=project_id,
        chapter_index=1,
        scene_index=5,
        content="张三在广场上展现出惊人的勇气，赢得了众人的尊敬。",
        content_type="scene",
        entities_mentioned=["张三"],
        tags=["勇气", "广场"],
        created_at=datetime.now()
    )
    db_manager.save_memory_chunk(test_chunk)
    vector_manager.vector_store.add_chunks([test_chunk])
    
    # 准备测试数据：实体状态
    entity_state = EntityStateSnapshot(
        project_id=project_id,
        entity_type="character",
        entity_id="character:张三",
        chapter_index=1,
        scene_index=5,
        timestamp=datetime.now(),
        state_data={"mood": "兴奋", "location": "广场", "status": "健康"}
    )
    db_manager.save_entity_snapshot(entity_state)
    
    # 执行检索
    context = retrieve_scene_memory_context(
        scene_plan=sample_scene_plan,
        characters_config=sample_characters_config,
        project_id=project_id,
        chapter_index=chapter_index,
        scene_index=scene_index,
        db_manager=db_manager,
        vector_manager=vector_manager,
        output_dir=temp_project_dir
    )
    
    # 验证结果
    assert isinstance(context, SceneMemoryContext)
    # 注意：实际检索结果取决于向量检索和数据库查询的匹配度


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
