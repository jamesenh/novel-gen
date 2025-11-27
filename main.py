"""
NovelGen 主入口
演示如何使用NovelGen生成小说
"""
import os
import json
from novelgen.runtime.orchestrator import NovelOrchestrator


def demo_full_flow(project_name):
    """演示完整的小说生成流程（使用 LangGraph 工作流）"""
    
    # 1. 准备项目目录和 settings.json
    project_dir = os.path.join("projects", project_name)
    os.makedirs(project_dir, exist_ok=True)
    
    settings_path = os.path.join(project_dir, "settings.json")
    
    # 检查 settings.json 是否已存在
    if not os.path.exists(settings_path):
        print("📄 创建 settings.json...")
        settings_data = {
            "project_name": project_name,
            "author": "Jamesenh",
            # "llm_model": "gpt-4",
            # "temperature": 0.7,
            "world_description": "一个2242年的未来地球，人类经历了\"大觉醒\"事件后，部分人类获得了操控量子能量的能力。社会分裂为三大阵营：保守的\"纯种人类联盟\"、追求进化的\"量子觉醒者\"、以及半机械改造的\"赛博融合体\"。地球资源枯竭，三大阵营争夺着火星殖民地的控制权，同时外太空的\"星际观察者\"文明正在默默关注着人类的内斗。科技高度发达，意识上传、虚拟现实、时空扭曲技术已经成熟，但也带来了伦理危机和身份认同的混乱。",
            "theme_description": "关于人性与科技边界的故事：当人类能够通过科技无限强化自身时，什么才是真正的\"人类\"？探讨在追求永生和超能力的过程中，人类是否正在失去最珍贵的情感和道德底线。故事聚焦于一个来自保守阵营的年轻人意外觉醒量子能力后，在三大阵营间的艰难抉择，以及他对\"人性本质\"的重新定义。核心冲突包括：传统价值观 vs 科技进化、个体自由 vs 集体利益、真实情感 vs 虚拟体验。",
            "num_chapters": 3
        }
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ settings.json 已创建: {settings_path}")
    else:
        print(f"📂 settings.json 已存在: {settings_path}")
    
    # 2. 创建编排器
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
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
        demo_full_flow("demo_013")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    # export_novel_cmd("demo_001")
    # apply_revision_cmd("demo_005", 1)

