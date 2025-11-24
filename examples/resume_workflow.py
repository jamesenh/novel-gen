"""
LangGraph 工作流恢复示例

演示如何使用 Checkpointing 功能暂停和恢复小说生成流程

使用方法:
    uv run python examples/resume_workflow.py

作者: jamesenh
日期: 2025-11-22
"""
import os
import sys
import time

# 添加项目根目录到 path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from novelgen.runtime.orchestrator import NovelOrchestrator


def demo_basic_workflow():
    """演示基本的工作流执行"""
    print("="*60)
    print("示例 1: 基本工作流执行")
    print("="*60)
    
    orchestrator = NovelOrchestrator(
        project_name='workflow_demo',
        base_dir='examples/temp_projects',
        verbose=False
    )
    
    try:
        print("\n🚀 开始运行工作流...")
        print("   注意：这将执行完整的小说生成流程")
        print("   （实际项目中会调用 LLM，此处仅演示流程）\n")
        
        # 运行工作流到世界观创建
        state = orchestrator.run_workflow(stop_at='world_creation')
        
        print(f"\n✅ 工作流已暂停在: {state.get('current_step')}")
        print(f"   已完成步骤: {', '.join(state.get('completed_steps', []))}")
        
        return orchestrator
        
    except Exception as e:
        print(f"\n❌ 工作流执行失败: {e}")
        return None


def demo_resume_workflow(orchestrator):
    """演示从检查点恢复工作流"""
    print("\n" + "="*60)
    print("示例 2: 从检查点恢复工作流")
    print("="*60)
    
    if orchestrator is None:
        print("⚠️ 没有可用的编排器，跳过恢复演示")
        return
    
    try:
        print("\n⏸️  工作流已暂停，准备恢复...")
        time.sleep(1)
        
        print("🔄 从最新检查点恢复...\n")
        
        # 从检查点恢复（这里会继续之前的流程）
        state = orchestrator.resume_workflow()
        
        print(f"\n✅ 工作流恢复完成")
        print(f"   当前步骤: {state.get('current_step')}")
        print(f"   已完成步骤: {', '.join(state.get('completed_steps'))}")
        
    except Exception as e:
        print(f"\n❌ 恢复失败: {e}")


def demo_checkpoint_inspection():
    """演示检查点检查"""
    print("\n" + "="*60)
    print("示例 3: 检查检查点历史")
    print("="*60)
    
    from novelgen.runtime.workflow import create_novel_generation_workflow
    
    workflow = create_novel_generation_workflow()
    config = {"configurable": {"thread_id": "workflow_demo"}}
    
    try:
        checkpoints = list(workflow.get_state_history(config))
        
        if checkpoints:
            print(f"\n📋 找到 {len(checkpoints)} 个检查点:\n")
            for i, checkpoint in enumerate(checkpoints[:5]):  # 只显示前5个
                values = checkpoint.values
                step = values.get('current_step', '未知')
                completed = len(values.get('completed_steps', []))
                print(f"   {i+1}. 步骤: {step}, 已完成: {completed} 步")
        else:
            print("\n⚠️ 未找到检查点")
            
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")


def demo_error_recovery():
    """演示错误恢复"""
    print("\n" + "="*60)
    print("示例 4: 错误恢复")
    print("="*60)
    
    orchestrator = NovelOrchestrator(
        project_name='error_demo',
        base_dir='examples/temp_projects',
        verbose=False
    )
    
    try:
        print("\n🚀 模拟工作流执行...")
        
        # 第一次尝试（可能失败）
        try:
            state = orchestrator.run_workflow(stop_at='theme_conflict_creation')
            print("\n✅ 第一阶段完成")
        except Exception as e:
            print(f"\n⚠️ 第一阶段失败: {e}")
            print("   从检查点恢复...")
            state = orchestrator.resume_workflow()
        
        print(f"\n✅ 最终状态: {state.get('current_step')}")
        
    except Exception as e:
        print(f"\n❌ 无法恢复: {e}")


def cleanup():
    """清理临时文件"""
    import shutil
    temp_dir = 'examples/temp_projects'
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print(f"\n🧹 清理临时目录: {temp_dir}")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("LangGraph 工作流恢复功能演示")
    print("="*60)
    print("\n这个示例演示如何:")
    print("  1. 运行工作流并暂停")
    print("  2. 从检查点恢复执行")
    print("  3. 查看检查点历史")
    print("  4. 处理错误和恢复")
    print()
    
    try:
        # 示例 1: 基本工作流
        orchestrator = demo_basic_workflow()
        
        # 示例 2: 恢复工作流
        if orchestrator:
            demo_resume_workflow(orchestrator)
        
        # 示例 3: 检查点检查
        demo_checkpoint_inspection()
        
        # 示例 4: 错误恢复
        demo_error_recovery()
        
        print("\n" + "="*60)
        print("✅ 所有示例完成！")
        print("="*60)
        
    finally:
        # 清理
        cleanup()


if __name__ == '__main__':
    main()
