"""
LangGraph Checkpointing 功能测试

验证工作流的暂停、恢复和检查点管理功能

开发者: jamesenh, 开发时间: 2025-11-22
"""
import os
import tempfile
import shutil
from novelgen.runtime.workflow import create_novel_generation_workflow
from novelgen.models import NovelGenerationState, Settings, WorldSetting


def test_checkpoint_creation():
    """测试检查点创建"""
    print("=== 测试 1: 检查点创建 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建工作流（使用 SQLite 持久化）
        workflow = create_novel_generation_workflow(project_dir=test_dir)
        
        # 创建初始状态
        state = NovelGenerationState(
            project_name='test_checkpoint',
            project_dir=test_dir,
            settings=Settings(
                project_name='test_checkpoint',
                author='Test Author',
            )
        )
        
        # 配置
        config = {"configurable": {"thread_id": "test_checkpoint"}}
        
        # 执行一步（加载设置）
        result = None
        step_count = 0
        for s in workflow.stream(state, config):
            result = s
            step_count += 1
            if step_count >= 1:  # 只执行第一步
                break
        
        # 验证至少执行了一步
        assert step_count >= 1, "应该执行至少一步"
        
        # 获取检查点历史
        checkpoints = list(workflow.get_state_history(config))
        
        assert len(checkpoints) > 0, "应该有检查点记录"
        print(f"  找到 {len(checkpoints)} 个检查点")
        
        # 验证检查点内容
        latest = checkpoints[0]
        assert latest.config is not None, "检查点应该有配置"
        assert latest.values is not None, "检查点应该有状态值"
        
        print("✅ 测试通过：检查点创建成功")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_workflow_resume_from_checkpoint():
    """测试从检查点恢复工作流"""
    print("\n=== 测试 2: 从检查点恢复 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建工作流（使用 SQLite 持久化）
        workflow = create_novel_generation_workflow(project_dir=test_dir)
        
        # 创建初始状态
        state = NovelGenerationState(
            project_name='test_resume',
            project_dir=test_dir,
            settings=Settings(
                project_name='test_resume',
                author='Test Author',
            )
        )
        
        # 配置
        config = {"configurable": {"thread_id": "test_resume"}}
        
        # 第一阶段：执行几步并暂停
        print("  第一阶段：执行并暂停")
        step_count_phase1 = 0
        for s in workflow.stream(state, config):
            step_count_phase1 += 1
            if step_count_phase1 >= 2:  # 执行2步后暂停
                break
        
        print(f"    第一阶段执行了 {step_count_phase1} 步")
        
        # 获取当前检查点
        checkpoints = list(workflow.get_state_history(config))
        assert len(checkpoints) > 0, "应该有检查点"
        
        # 第二阶段：从检查点恢复继续执行
        print("  第二阶段：从检查点恢复")
        step_count_phase2 = 0
        for s in workflow.stream(None, config):  # None 表示从最新检查点恢复
            step_count_phase2 += 1
            if step_count_phase2 >= 1:  # 再执行1步
                break
        
        print(f"    第二阶段执行了 {step_count_phase2} 步")
        
        # 验证总共的检查点数量增加了
        final_checkpoints = list(workflow.get_state_history(config))
        assert len(final_checkpoints) >= len(checkpoints), "检查点数量应该增加"
        
        print("✅ 测试通过：工作流恢复成功")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_checkpoint_state_preservation():
    """测试检查点状态保存"""
    print("\n=== 测试 3: 检查点状态保存 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建工作流（使用 SQLite 持久化）
        workflow = create_novel_generation_workflow(project_dir=test_dir)
        
        # 创建带自定义数据的状态
        state = NovelGenerationState(
            project_name='test_preserve',
            project_dir=test_dir,
            settings=Settings(
                project_name='test_preserve',
                author='Test Author',
            ),
            world=WorldSetting(
                world_name='保存测试世界',
                time_period='现代',
                geography='城市',
                social_system='现代社会',
                technology_level='现代科技',
                culture_customs='现代文化'
            )
        )
        
        # 配置
        config = {"configurable": {"thread_id": "test_preserve"}}
        
        # 执行一步
        for s in workflow.stream(state, config):
            break  # 只执行一步
        
        # 获取检查点
        checkpoints = list(workflow.get_state_history(config))
        assert len(checkpoints) > 0, "应该有检查点"
        
        # 验证状态数据被保存
        latest = checkpoints[0]
        saved_values = latest.values
        
        assert 'project_name' in saved_values, "应该保存 project_name"
        assert saved_values['project_name'] == 'test_preserve', "project_name 应该匹配"
        
        # 验证嵌套对象也被保存
        if 'world' in saved_values and saved_values['world']:
            world = saved_values['world']
            if isinstance(world, dict):
                assert world['world_name'] == '保存测试世界', "world 数据应该被保存"
            else:
                assert world.world_name == '保存测试世界', "world 数据应该被保存"
        
        print("✅ 测试通过：状态数据正确保存")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_multiple_checkpoint_threads():
    """测试多个检查点线程"""
    print("\n=== 测试 4: 多线程检查点 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建工作流（使用 SQLite 持久化）
        workflow = create_novel_generation_workflow(project_dir=test_dir)
        
        # 创建两个不同的项目状态
        state1 = NovelGenerationState(
            project_name='project1',
            project_dir=os.path.join(test_dir, 'project1'),
            settings=Settings(project_name='project1', author='Author 1')
        )
        
        state2 = NovelGenerationState(
            project_name='project2',
            project_dir=os.path.join(test_dir, 'project2'),
            settings=Settings(project_name='project2', author='Author 2')
        )
        
        # 为两个项目创建独立的检查点线程
        config1 = {"configurable": {"thread_id": "project1"}}
        config2 = {"configurable": {"thread_id": "project2"}}
        
        # 执行 project1
        for s in workflow.stream(state1, config1):
            break
        
        # 执行 project2
        for s in workflow.stream(state2, config2):
            break
        
        # 验证两个线程的检查点是独立的
        checkpoints1 = list(workflow.get_state_history(config1))
        checkpoints2 = list(workflow.get_state_history(config2))
        
        assert len(checkpoints1) > 0, "project1 应该有检查点"
        assert len(checkpoints2) > 0, "project2 应该有检查点"
        
        # 验证数据不混淆
        assert checkpoints1[0].values['project_name'] == 'project1', "project1 数据应该正确"
        assert checkpoints2[0].values['project_name'] == 'project2', "project2 数据应该正确"
        
        print("✅ 测试通过：多线程检查点隔离正常")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_checkpoint_time_travel():
    """测试检查点时间旅行（回到之前的状态）"""
    print("\n=== 测试 5: 检查点时间旅行 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建工作流（使用 SQLite 持久化）
        workflow = create_novel_generation_workflow(project_dir=test_dir)
        
        state = NovelGenerationState(
            project_name='test_timetravel',
            project_dir=test_dir,
            settings=Settings(project_name='test_timetravel', author='Test')
        )
        
        config = {"configurable": {"thread_id": "test_timetravel"}}
        
        # 执行多步
        step_count = 0
        for s in workflow.stream(state, config):
            step_count += 1
            if step_count >= 3:
                break
        
        # 获取所有检查点
        checkpoints = list(workflow.get_state_history(config))
        assert len(checkpoints) >= 2, "应该有多个检查点"
        
        print(f"  共有 {len(checkpoints)} 个检查点")
        
        # 选择一个早期的检查点
        if len(checkpoints) >= 2:
            earlier_checkpoint = checkpoints[-1]  # 最早的检查点
            
            # 获取该检查点的状态
            earlier_state = workflow.get_state(earlier_checkpoint.config)
            assert earlier_state is not None, "应该能获取早期状态"
            
            print("  成功获取早期检查点状态")
        
        print("✅ 测试通过：检查点时间旅行正常")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    print("开始 Checkpointing 功能测试...\n")
    
    try:
        test_checkpoint_creation()
        test_workflow_resume_from_checkpoint()
        test_checkpoint_state_preservation()
        test_multiple_checkpoint_threads()
        test_checkpoint_time_travel()
        
        print("\n" + "="*60)
        print("✅ 所有 Checkpointing 测试通过！")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
