"""
LangGraph 集成测试

验证 NovelOrchestrator 的 LangGraph 集成功能

开发者: jamesenh, 开发时间: 2025-11-22
"""
import os
import json
import tempfile
import shutil
from novelgen.runtime.orchestrator import NovelOrchestrator
from novelgen.models import NovelGenerationState


def test_orchestrator_initialization():
    """测试编排器初始化"""
    print("=== 测试 1: 编排器初始化 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='test_init',
            base_dir=test_dir,
            verbose=False
        )
        
        # 验证工作流已初始化
        assert orchestrator.workflow is not None, "工作流应该已初始化"
        assert orchestrator._workflow_state is None, "初始状态应该为 None"
        
        # 验证新方法存在
        assert hasattr(orchestrator, 'run_workflow'), "应该有 run_workflow 方法"
        assert hasattr(orchestrator, 'resume_workflow'), "应该有 resume_workflow 方法"
        
        # 验证向后兼容
        assert hasattr(orchestrator, 'step1_create_world'), "应该保留 step1_create_world 方法"
        
        orchestrator.close()
        print("✅ 测试通过：编排器初始化正常")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_workflow_state_creation():
    """测试工作流状态创建"""
    print("\n=== 测试 2: 工作流状态创建 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='test_state',
            base_dir=test_dir,
            verbose=False
        )
        
        # 创建基本的 settings.json（world/theme 由独立 JSON 文件管理）
        settings_data = {
            "project_name": "test_state",
            "author": "Test Author",
            "llm_model": "gpt-4o-mini",
            "temperature": 0.7,
        }
        settings_path = os.path.join(orchestrator.project_dir, "settings.json")
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        # 获取或创建工作流状态
        state = orchestrator._get_or_create_workflow_state()
        
        # 验证状态结构
        assert isinstance(state, NovelGenerationState), "状态应该是 NovelGenerationState 类型"
        assert state.project_name == 'test_state', "项目名称应该匹配"
        assert state.project_dir == orchestrator.project_dir, "项目目录应该匹配"
        assert state.current_step == 'init', "初始步骤应该是 init"
        assert state.completed_steps == [], "完成步骤列表应该为空"
        
        orchestrator.close()
        print("✅ 测试通过：工作流状态创建正常")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试 3: 向后兼容性 ===")
    
    test_dir = tempfile.mkdtemp()
    try:
        orchestrator = NovelOrchestrator(
            project_name='test_compat',
            base_dir=test_dir,
            verbose=False
        )
        
        # 验证所有原有的 step 方法都存在
        step_methods = [
            'step1_create_world',
            'step2_create_theme_conflict',
            'step3_create_characters',
            'step4_create_outline',
            'step5_create_chapter_plan',
            'step6_generate_chapter_text'
        ]
        
        for method_name in step_methods:
            assert hasattr(orchestrator, method_name), f"应该保留 {method_name} 方法"
            method = getattr(orchestrator, method_name)
            assert callable(method), f"{method_name} 应该可调用"
        
        # 验证其他重要方法
        other_methods = [
            'generate_all_chapters',
            'export_chapter',
            'export_all_chapters',
            'apply_revision',
            'save_json',
            'load_json',
            'close'
        ]
        
        for method_name in other_methods:
            assert hasattr(orchestrator, method_name), f"应该保留 {method_name} 方法"
        
        orchestrator.close()
        print("✅ 测试通过：向后兼容性良好")
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    print("开始 LangGraph 集成测试...\n")
    
    try:
        test_orchestrator_initialization()
        test_workflow_state_creation()
        test_backward_compatibility()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！LangGraph 集成验证成功")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
