"""
NovelGen 主入口
演示如何使用NovelGen生成小说
"""
import os
import json
from novelgen.runtime.orchestrator import NovelOrchestrator


def demo_full_flow(project_name, verbose=False, show_prompt=True):
    """演示完整的小说生成流程（使用 LangGraph 工作流）
    
    Args:
        project_name: 项目名称
        verbose: 是否启用详细日志
        show_prompt: verbose 模式下是否显示完整提示词（默认 True）
    """
    
    # 1. 准备项目目录和 settings.json
    project_dir = os.path.join("projects", project_name)
    os.makedirs(project_dir, exist_ok=True)
    
    settings_path = os.path.join(project_dir, "settings.json")
    
    # 检查 settings.json 是否已存在
    if not os.path.exists(settings_path):
        print("📄 创建 settings.json...")
        # 注意：world_description/theme_description 已移除，由独立 JSON 文件管理
        # 请先通过内容生成 API 或 CLI 创建 world.json 和 theme_conflict.json
        settings_data = {
            "project_name": project_name,
            "author": "Jamesenh",
            "initial_chapters": 3,
            "max_chapters": 50,
        }
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ settings.json 已创建: {settings_path}")
        print("⚠️  提示：请先通过 Web UI 或 CLI 创建 world.json 和 theme_conflict.json")
    else:
        print(f"📂 settings.json 已存在: {settings_path}")
    
    # 2. 创建编排器
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=verbose, show_prompt=show_prompt)
    print(f"📁 项目目录: {orchestrator.project_dir}")
    
    # 3. 运行 LangGraph 工作流
    print("\n" + "="*60)
    print("🚀 开始运行 LangGraph 工作流")
    print("="*60)
    print("提示：工作流将自动执行所有步骤：")
    print("  1. 加载配置")
    print("  2. 生成世界观")
    print("  3. 生成主题冲突")
    print("  4. 生成角色")
    print("  5. 生成大纲")
    print("  6. 生成章节计划")
    print("  7. 生成章节文本")
    print("  8. 一致性检查")
    print()
    
    try:
        # 运行工作流（不指定 stop_at，将执行全部步骤）
        final_state = orchestrator.run_workflow()
        
        print("\n" + "="*60)
        print("✅ 工作流执行完成！")
        print("="*60)
        print(f"当前步骤: {final_state.get('current_step')}")
        print(f"已完成: {', '.join(final_state.get('completed_steps', []))}")
        
        if final_state.get('failed_steps'):
            print(f"⚠️  失败步骤: {', '.join(final_state.get('failed_steps', []))}")
            for step, error in final_state.get('error_messages', {}).items():
                print(f"  - {step}: {error}")
        
        # 4. 导出章节
        print("\n" + "="*60)
        print("💾 导出章节")
        print("="*60)
        orchestrator.export_all_chapters()
        
    except Exception as e:
        print(f"\n❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()


def export_novel_cmd(project_name: str):
    """
    导出整本小说为txt文件
    
    Args:
        project_name: 项目名称
    """
    orchestrator = NovelOrchestrator(project_name=project_name)
    orchestrator.export_all_chapters()


def export_chapter_cmd(project_name: str, chapter_number: int):
    """
    导出单个章节为txt文件
    
    Args:
        project_name: 项目名称
        chapter_number: 章节编号
    """
    orchestrator = NovelOrchestrator(project_name=project_name)
    orchestrator.export_chapter(chapter_number)


def apply_revision_cmd(project_name: str, chapter_number: int, rebuild_memory: bool = True):
    """
    应用待确认的修订
    
    Args:
        project_name: 项目名称
        chapter_number: 章节编号
        rebuild_memory: 是否重建章节记忆
    """
    orchestrator = NovelOrchestrator(project_name=project_name)
    orchestrator.apply_revision(chapter_number, rebuild_memory=rebuild_memory)
    print(f"\n✅ 第{chapter_number}章修订已应用")

if __name__ == "__main__":
    # test_generate_chapter_text()
    try:
        # verbose=True 显示详细日志，show_prompt=False 不显示提示词（只看响应）
        demo_full_flow("demo_019", verbose=True, show_prompt=False)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    # export_novel_cmd("demo_001")
    # apply_revision_cmd("demo_005", 1)

