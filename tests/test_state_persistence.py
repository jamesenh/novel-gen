"""
状态持久化测试

验证 LangGraph 状态与 JSON 文件的双向同步功能

开发者: jamesenh, 开发时间: 2025-11-22
"""
import os
import json
import tempfile
import shutil
from novelgen.runtime.state_sync import (
    state_to_json_files,
    json_files_to_state,
    sync_state_from_json,
    validate_state_json_consistency
)
from novelgen.models import (
    NovelGenerationState, Settings, WorldSetting, ThemeConflict
)


def test_state_to_json_export():
    """测试状态导出到 JSON 文件"""
    print("=== 测试 1: 状态导出到 JSON ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建一个包含部分数据的状态
        state = NovelGenerationState(
            project_name='test_export',
            project_dir=test_dir,
            settings=Settings(
                project_name='test_export',
                author='Test Author',
            ),
            world=WorldSetting(
                world_name='测试世界',
                time_period='现代',
                geography='城市',
                social_system='现代社会',
                technology_level='现代科技',
                culture_customs='现代文化'
            )
        )
        
        # 导出到 JSON
        saved_files = state_to_json_files(state)
        
        # 验证文件已创建
        assert 'settings' in saved_files, "应该保存 settings 文件"
        assert 'world' in saved_files, "应该保存 world 文件"
        assert os.path.exists(saved_files['settings']), "settings 文件应该存在"
        assert os.path.exists(saved_files['world']), "world 文件应该存在"
        
        # 验证文件内容
        with open(saved_files['world'], 'r', encoding='utf-8') as f:
            world_data = json.load(f)
            assert world_data['world_name'] == '测试世界', "世界名称应该匹配"
        
        print(f"✅ 测试通过：成功导出 {len(saved_files)} 个文件")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_json_to_state_import():
    """测试从 JSON 文件导入状态"""
    print("\n=== 测试 2: 从 JSON 导入状态 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建测试 JSON 文件
        world_data = {
            'world_name': '导入测试世界',
            'time_period': '未来',
            'geography': '太空站',
            'social_system': '星际联盟',
            'technology_level': '超级科技',
            'culture_customs': '星际文化'
        }
        
        world_path = os.path.join(test_dir, 'world.json')
        with open(world_path, 'w', encoding='utf-8') as f:
            json.dump(world_data, f, ensure_ascii=False, indent=2)
        
        theme_data = {
            'core_theme': '探索未知',
            'sub_themes': ['冒险', '科技'],
            'main_conflict': '人类与未知的对抗',
            'sub_conflicts': ['资源争夺'],
            'tone': '严肃'
        }
        
        theme_path = os.path.join(test_dir, 'theme_conflict.json')
        with open(theme_path, 'w', encoding='utf-8') as f:
            json.dump(theme_data, f, ensure_ascii=False, indent=2)
        
        # 从 JSON 导入状态
        state = json_files_to_state(test_dir, 'test_import')
        
        # 验证状态内容
        assert state.project_name == 'test_import', "项目名称应该匹配"
        assert state.world is not None, "world 应该被加载"
        assert state.world.world_name == '导入测试世界', "世界名称应该匹配"
        assert state.theme_conflict is not None, "theme_conflict 应该被加载"
        assert state.theme_conflict.core_theme == '探索未知', "核心主题应该匹配"
        
        print("✅ 测试通过：成功从 JSON 导入状态")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_bidirectional_sync():
    """测试双向同步（状态 <-> JSON）"""
    print("\n=== 测试 3: 双向同步 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 1. 创建初始状态并导出
        initial_state = NovelGenerationState(
            project_name='test_sync',
            project_dir=test_dir,
            world=WorldSetting(
                world_name='同步测试世界_v1',
                time_period='古代',
                geography='大陆',
                social_system='封建制度',
                technology_level='冷兵器时代',
                culture_customs='古典文化'
            )
        )
        
        saved_files = state_to_json_files(initial_state)
        assert 'world' in saved_files, "应该保存 world 文件"
        
        # 2. 手动修改 JSON 文件
        world_path = saved_files['world']
        with open(world_path, 'r', encoding='utf-8') as f:
            world_data = json.load(f)
        
        world_data['world_name'] = '同步测试世界_v2'  # 修改世界名称
        
        with open(world_path, 'w', encoding='utf-8') as f:
            json.dump(world_data, f, ensure_ascii=False, indent=2)
        
        # 3. 从 JSON 重新加载状态
        reloaded_state = json_files_to_state(test_dir, 'test_sync')
        
        # 验证修改已同步
        assert reloaded_state.world is not None, "world 应该被加载"
        assert reloaded_state.world.world_name == '同步测试世界_v2', "修改应该被同步"
        
        # 4. 再次导出，验证往返一致性
        state_to_json_files(reloaded_state)
        
        with open(world_path, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
        
        assert final_data['world_name'] == '同步测试世界_v2', "往返后数据应该一致"
        
        print("✅ 测试通过：双向同步正常工作")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_partial_state_handling():
    """测试部分状态的处理（只有部分字段有值）"""
    print("\n=== 测试 4: 部分状态处理 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建只有部分字段的状态
        partial_state = NovelGenerationState(
            project_name='test_partial',
            project_dir=test_dir,
            world=WorldSetting(
                world_name='部分状态世界',
                time_period='现代',
                geography='城市',
                social_system='现代社会',
                technology_level='现代科技',
                culture_customs='现代文化'
            )
            # 注意：没有 theme_conflict, characters 等
        )
        
        # 导出
        saved_files = state_to_json_files(partial_state)
        
        # 只应该有 world 文件
        assert 'world' in saved_files, "应该保存 world 文件"
        assert 'theme_conflict' not in saved_files, "不应该保存不存在的 theme_conflict"
        
        # 重新加载
        reloaded_state = json_files_to_state(test_dir, 'test_partial')
        
        # 验证部分状态
        assert reloaded_state.world is not None, "world 应该存在"
        assert reloaded_state.theme_conflict is None, "theme_conflict 应该为 None"
        assert reloaded_state.characters is None, "characters 应该为 None"
        
        print("✅ 测试通过：部分状态处理正常")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_sync_state_from_json():
    """测试同步状态更新功能"""
    print("\n=== 测试 5: 同步状态更新 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建初始状态
        state = NovelGenerationState(
            project_name='test_sync_update',
            project_dir=test_dir,
            current_step='world_creation',
            completed_steps=['load_settings'],
            world=WorldSetting(
                world_name='原始世界',
                time_period='现代',
                geography='城市',
                social_system='现代社会',
                technology_level='现代科技',
                culture_customs='现代文化'
            )
        )
        
        # 导出状态
        state_to_json_files(state)
        
        # 修改磁盘上的 JSON
        world_path = os.path.join(test_dir, 'world.json')
        with open(world_path, 'r', encoding='utf-8') as f:
            world_data = json.load(f)
        world_data['world_name'] = '更新后的世界'
        with open(world_path, 'w', encoding='utf-8') as f:
            json.dump(world_data, f, ensure_ascii=False, indent=2)
        
        # 同步状态
        updated_state = sync_state_from_json(state)
        
        # 验证数据已更新，但工作流字段保留
        assert updated_state.world.world_name == '更新后的世界', "数据应该更新"
        assert updated_state.current_step == 'world_creation', "工作流状态应该保留"
        assert updated_state.completed_steps == ['load_settings'], "完成步骤应该保留"
        
        print("✅ 测试通过：同步状态更新正常")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    print("开始状态持久化测试...\n")
    
    try:
        test_state_to_json_export()
        test_json_to_state_import()
        test_bidirectional_sync()
        test_partial_state_handling()
        test_sync_state_from_json()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！状态持久化功能正常")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
