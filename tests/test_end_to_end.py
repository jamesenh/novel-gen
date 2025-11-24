"""
端到端验证测试

验证完整的 LangGraph 工作流功能

开发者: jamesenh, 开发时间: 2025-11-22
"""
import os
import tempfile
import shutil
from novelgen.runtime.orchestrator import NovelOrchestrator
from novelgen.models import Settings, WorldSetting


def test_backward_compatibility_api():
    """测试向后兼容的 API"""
    print("="*60)
    print("验证 1: 向后兼容 API")
    print("="*60)
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='compat_test',
            base_dir=test_dir,
            verbose=False
        )
        
        # 验证原有方法存在
        assert hasattr(orchestrator, 'step1_create_world'), "step1_create_world 应该存在"
        assert hasattr(orchestrator, 'step2_create_theme_conflict'), "step2_create_theme_conflict 应该存在"
        assert hasattr(orchestrator, 'step3_create_characters'), "step3_create_characters 应该存在"
        assert hasattr(orchestrator, 'step4_create_outline'), "step4_create_outline 应该存在"
        assert hasattr(orchestrator, 'step5_create_chapter_plan'), "step5_create_chapter_plan 应该存在"
        assert hasattr(orchestrator, 'step6_generate_chapter_text'), "step6_generate_chapter_text 应该存在"
        assert hasattr(orchestrator, 'generate_all_chapters'), "generate_all_chapters 应该存在"
        
        # 验证新方法存在
        assert hasattr(orchestrator, 'run_workflow'), "run_workflow 应该存在"
        assert hasattr(orchestrator, 'resume_workflow'), "resume_workflow 应该存在"
        assert hasattr(orchestrator, '_get_or_create_workflow_state'), "_get_or_create_workflow_state 应该存在"
        
        orchestrator.close()
        print("✅ 向后兼容 API 验证通过")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_workflow_initialization():
    """测试工作流初始化"""
    print("\n" + "="*60)
    print("验证 2: 工作流初始化")
    print("="*60)
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='workflow_init_test',
            base_dir=test_dir,
            verbose=False
        )
        
        # 验证工作流已初始化
        assert orchestrator.workflow is not None, "workflow 应该已初始化"
        assert orchestrator._workflow_state is None, "初始状态应该为 None"
        
        # 验证工作流类型
        workflow_type = type(orchestrator.workflow).__name__
        assert workflow_type == 'CompiledStateGraph', f"应该是 CompiledStateGraph 类型，当前是 {workflow_type}"
        
        orchestrator.close()
        print("✅ 工作流初始化验证通过")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_state_creation_and_sync():
    """测试状态创建和同步"""
    print("\n" + "="*60)
    print("验证 3: 状态创建和同步")
    print("="*60)
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='state_sync_test',
            base_dir=test_dir,
            verbose=False
        )
        
        # 创建一些测试数据
        import json
        world_data = {
            'world_name': '验证测试世界',
            'time_period': '现代',
            'geography': '城市',
            'social_system': '现代社会',
            'technology_level': '现代科技',
            'culture_customs': '现代文化'
        }
        world_path = os.path.join(orchestrator.project_dir, 'world.json')
        with open(world_path, 'w', encoding='utf-8') as f:
            json.dump(world_data, f, ensure_ascii=False, indent=2)
        
        # 获取或创建状态
        state = orchestrator._get_or_create_workflow_state()
        
        # 验证状态
        assert state is not None, "状态应该被创建"
        assert state.project_name == 'state_sync_test', "项目名称应该匹配"
        assert state.world is not None, "world 应该被加载"
        assert state.world.world_name == '验证测试世界', "world 数据应该正确"
        
        orchestrator.close()
        print("✅ 状态创建和同步验证通过")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_checkpointing_integration():
    """测试 Checkpointing 集成"""
    print("\n" + "="*60)
    print("验证 4: Checkpointing 集成")
    print("="*60)
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='checkpoint_test',
            base_dir=test_dir,
            verbose=False
        )
        
        # 执行工作流的一部分
        state = orchestrator._get_or_create_workflow_state()
        config = {"configurable": {"thread_id": "checkpoint_test"}}
        
        # 执行几步
        step_count = 0
        for s in orchestrator.workflow.stream(state, config):
            step_count += 1
            if step_count >= 2:
                break
        
        # 验证检查点存在
        checkpoints = list(orchestrator.workflow.get_state_history(config))
        assert len(checkpoints) > 0, "应该有检查点"
        
        orchestrator.close()
        print(f"✅ Checkpointing 集成验证通过（{len(checkpoints)} 个检查点）")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_json_persistence():
    """测试 JSON 持久化"""
    print("\n" + "="*60)
    print("验证 5: JSON 持久化")
    print("="*60)
    
    test_dir = tempfile.mkdtemp()
    try:
        from novelgen.runtime.state_sync import state_to_json_files, json_files_to_state
        from novelgen.models import NovelGenerationState, WorldSetting
        
        # 创建状态
        state = NovelGenerationState(
            project_name='persist_test',
            project_dir=test_dir,
            world=WorldSetting(
                world_name='持久化测试',
                time_period='现代',
                geography='城市',
                social_system='现代社会',
                technology_level='现代科技',
                culture_customs='现代文化'
            )
        )
        
        # 导出到 JSON
        saved_files = state_to_json_files(state)
        assert 'world' in saved_files, "world 文件应该被保存"
        assert os.path.exists(saved_files['world']), "world 文件应该存在"
        
        # 从 JSON 加载
        loaded_state = json_files_to_state(test_dir, 'persist_test')
        assert loaded_state.world is not None, "world 应该被加载"
        assert loaded_state.world.world_name == '持久化测试', "数据应该一致"
        
        print("✅ JSON 持久化验证通过")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_workflow_nodes_structure():
    """测试工作流节点结构"""
    print("\n" + "="*60)
    print("验证 6: 工作流节点结构")
    print("="*60)
    
    from novelgen.runtime.workflow import create_novel_generation_workflow
    
    workflow = create_novel_generation_workflow()
    
    # 获取节点列表
    nodes = list(workflow.get_graph().nodes.keys())
    
    # 验证关键节点存在
    expected_nodes = [
        'load_settings',
        'world_creation',
        'theme_conflict_creation',
        'character_creation',
        'outline_creation',
        'chapter_planning',
        'chapter_generation',
        'consistency_check'
    ]
    
    for node in expected_nodes:
        assert node in nodes, f"节点 '{node}' 应该存在"
    
    print(f"✅ 工作流节点结构验证通过（{len(nodes)} 个节点）")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("验证 7: 错误处理")
    print("="*60)
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='error_test',
            base_dir=test_dir,
            verbose=False
        )
        
        # 创建状态
        state = orchestrator._get_or_create_workflow_state()
        
        # 验证错误跟踪字段存在
        assert hasattr(state, 'error_messages'), "应该有 error_messages 字段"
        assert hasattr(state, 'failed_steps'), "应该有 failed_steps 字段"
        assert isinstance(state.error_messages, dict), "error_messages 应该是字典"
        assert isinstance(state.failed_steps, list), "failed_steps 应该是列表"
        
        orchestrator.close()
        print("✅ 错误处理验证通过")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_memory_management():
    """测试内存管理"""
    print("\n" + "="*60)
    print("验证 8: 内存管理")
    print("="*60)
    
    test_dir = tempfile.mkdtemp()
    try:
        # 创建多个编排器实例
        orchestrators = []
        for i in range(3):
            orch = NovelOrchestrator(
                project_name=f'memory_test_{i}',
                base_dir=test_dir,
                verbose=False
            )
            orchestrators.append(orch)
        
        # 验证每个实例独立
        for i, orch in enumerate(orchestrators):
            assert orch.project_name == f'memory_test_{i}', "项目名称应该独立"
            assert orch.workflow is not None, "每个实例应该有独立的工作流"
        
        # 清理
        for orch in orchestrators:
            orch.close()
        
        print("✅ 内存管理验证通过（3 个独立实例）")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def run_all_validations():
    """运行所有验证测试"""
    print("\n" + "🔍 开始 LangGraph 迁移端到端验证...\n")
    
    try:
        test_backward_compatibility_api()
        test_workflow_initialization()
        test_state_creation_and_sync()
        test_checkpointing_integration()
        test_json_persistence()
        test_workflow_nodes_structure()
        test_error_handling()
        test_memory_management()
        
        print("\n" + "="*60)
        print("✅ 所有验证测试通过！")
        print("="*60)
        print("\n🎉 LangGraph 迁移核心功能验证成功！")
        print("\n核心功能清单:")
        print("  ✅ 向后兼容 API")
        print("  ✅ 工作流初始化")
        print("  ✅ 状态管理")
        print("  ✅ Checkpointing")
        print("  ✅ JSON 持久化")
        print("  ✅ 节点结构")
        print("  ✅ 错误处理")
        print("  ✅ 内存管理")
        print("\n" + "="*60)
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ 验证失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 验证异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_validations()
    exit(0 if success else 1)
