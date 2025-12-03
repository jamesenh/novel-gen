"""
NovelGenerationState 模型单元测试

验证状态模型的序列化、验证和字段管理功能

开发者: jamesenh, 开发时间: 2025-11-22
"""
import pytest
from novelgen.models import (
    NovelGenerationState, Settings, WorldSetting, ThemeConflict,
    CharactersConfig, Character, Outline, ChapterSummary,
    ChapterPlan, ScenePlan, GeneratedChapter, ChapterMemoryEntry
)


def test_state_initialization_minimal():
    """测试最小化状态初始化"""
    state = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test'
    )
    
    assert state.project_name == 'test_project'
    assert state.project_dir == '/tmp/test'
    assert state.current_step == 'init'
    assert state.completed_steps == []
    assert state.failed_steps == []
    assert state.settings is None
    assert state.world is None


def test_state_initialization_with_data():
    """测试带完整数据的状态初始化"""
    settings = Settings(
        project_name='test_project',
        author='Test Author',
        world_description='测试世界描述'
    )
    
    world = WorldSetting(
        world_name='测试世界',
        time_period='现代',
        geography='城市',
        social_system='现代社会',
        technology_level='现代科技',
        culture_customs='现代文化'
    )
    
    state = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test',
        settings=settings,
        world=world,
        current_step='world_creation',
        completed_steps=['load_settings']
    )
    
    assert state.settings == settings
    assert state.world == world
    assert state.current_step == 'world_creation'
    assert 'load_settings' in state.completed_steps


def test_state_serialization():
    """测试状态序列化"""
    state = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test',
        world=WorldSetting(
            world_name='测试世界',
            time_period='现代',
            geography='城市',
            social_system='现代社会',
            technology_level='现代科技',
            culture_customs='现代文化'
        )
    )
    
    # 序列化
    data = state.model_dump()
    
    assert data['project_name'] == 'test_project'
    assert data['world']['world_name'] == '测试世界'
    assert isinstance(data['completed_steps'], list)
    
    # 反序列化
    restored = NovelGenerationState(**data)
    assert restored.project_name == state.project_name
    assert restored.world.world_name == state.world.world_name


def test_state_chapters_management():
    """测试章节管理功能"""
    state = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test'
    )
    
    # 添加章节计划
    plan = ChapterPlan(
        chapter_number=1,
        chapter_title='第一章',
        scenes=[]
    )
    state.chapters_plan[1] = plan
    
    assert 1 in state.chapters_plan
    assert state.chapters_plan[1].chapter_title == '第一章'
    
    # 添加生成的章节
    from novelgen.models import GeneratedChapter, GeneratedScene
    chapter = GeneratedChapter(
        chapter_number=1,
        chapter_title='第一章',
        scenes=[],
        total_words=1000
    )
    state.chapters[1] = chapter
    
    assert 1 in state.chapters
    assert state.chapters[1].total_words == 1000


def test_state_error_tracking():
    """测试错误跟踪功能"""
    state = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test'
    )
    
    # 添加错误
    state.error_messages['world_creation'] = '世界观生成失败'
    state.failed_steps.append('world_creation')
    
    assert 'world_creation' in state.error_messages
    assert 'world_creation' in state.failed_steps
    assert state.error_messages['world_creation'] == '世界观生成失败'


def test_state_workflow_progress():
    """测试工作流进度跟踪"""
    state = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test'
    )
    
    # 模拟工作流进度
    steps = ['load_settings', 'world_creation', 'theme_conflict_creation']
    
    for step in steps:
        state.current_step = step
        if step != steps[-1]:  # 最后一步不标记为完成
            state.completed_steps.append(step)
    
    assert state.current_step == 'theme_conflict_creation'
    assert len(state.completed_steps) == 2
    assert 'load_settings' in state.completed_steps
    assert 'world_creation' in state.completed_steps


def test_state_memory_entries():
    """测试章节记忆条目管理"""
    state = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test'
    )
    
    # 添加记忆条目
    memory = ChapterMemoryEntry(
        chapter_number=1,
        chapter_title='第一章',
        timeline_anchor='第一天早晨',
        location_summary='城市中心',
        key_events=['主角醒来', '接到任务'],
        character_states={'主角': '困惑'},
        unresolved_threads=['任务详情不明'],
        summary='主角接到神秘任务'
    )
    
    state.chapter_memories.append(memory)
    
    assert len(state.chapter_memories) == 1
    assert state.chapter_memories[0].chapter_number == 1
    assert '主角醒来' in state.chapter_memories[0].key_events


def test_state_validation():
    """测试状态验证"""
    # 测试必填字段
    with pytest.raises(Exception):
        NovelGenerationState()  # 缺少必填字段
    
    # 正常创建
    state = NovelGenerationState(
        project_name='test',
        project_dir='/tmp'
    )
    assert state is not None


def test_state_copy_and_update():
    """测试状态复制和更新"""
    original = NovelGenerationState(
        project_name='test_project',
        project_dir='/tmp/test',
        current_step='init'
    )
    
    # 更新字段
    original.current_step = 'world_creation'
    original.completed_steps.append('load_settings')
    
    # 验证更新
    assert original.current_step == 'world_creation'
    assert 'load_settings' in original.completed_steps


if __name__ == '__main__':
    print("开始 NovelGenerationState 单元测试...\n")
    
    test_state_initialization_minimal()
    print("✅ 测试 1: 最小化初始化")
    
    test_state_initialization_with_data()
    print("✅ 测试 2: 完整数据初始化")
    
    test_state_serialization()
    print("✅ 测试 3: 序列化/反序列化")
    
    test_state_chapters_management()
    print("✅ 测试 4: 章节管理")
    
    test_state_error_tracking()
    print("✅ 测试 5: 错误跟踪")
    
    test_state_workflow_progress()
    print("✅ 测试 6: 工作流进度")
    
    test_state_memory_entries()
    print("✅ 测试 7: 记忆条目")
    
    test_state_copy_and_update()
    print("✅ 测试 8: 状态更新")
    
    print("\n" + "="*60)
    print("✅ 所有单元测试通过！")
    print("="*60)
