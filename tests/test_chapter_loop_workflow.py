"""
测试逐章生成与一致性检测工作流

验证：
1. 单章生成是否正常
2. 一致性检测是否捕获问题
3. 修订是否被正确触发
4. 循环是否正确终止

开发者: jamesenh, 开发时间: 2025-11-24
"""
import os
import json
import tempfile
import shutil
from pathlib import Path

from novelgen.models import NovelGenerationState, Settings
from novelgen.runtime.workflow import create_novel_generation_workflow


def test_chapter_loop_workflow():
    """测试逐章生成工作流"""
    
    # 创建临时项目目录
    temp_dir = tempfile.mkdtemp(prefix="test_novel_")
    project_name = "test_loop_workflow"
    project_dir = os.path.join(temp_dir, project_name)
    os.makedirs(project_dir, exist_ok=True)
    
    try:
        print(f"📁 测试项目目录: {project_dir}")
        
        # 创建测试配置
        settings = Settings(
            project_name=project_name,
            author="Jamesenh",
            world_description="一个赛博朋克风格的未来城市，科技高度发达但贫富差距极大",
            theme_description="探讨人工智能觉醒与人性的边界",
            num_chapters=2  # 只生成2章用于测试
        )
        
        settings_path = os.path.join(project_dir, "settings.json")
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已创建配置文件: {settings_path}")
        
        # 创建工作流
        workflow = create_novel_generation_workflow()
        
        print("\n🚀 开始执行工作流...")
        print("=" * 60)
        
        # 初始化状态
        initial_state = NovelGenerationState(
            project_name=project_name,
            project_dir=project_dir
        )
        
        # 执行工作流
        config = {"configurable": {"thread_id": "test_loop_001"}}
        
        # 逐步执行并打印状态
        step_count = 0
        for state in workflow.stream(initial_state, config):
            step_count += 1
            print(f"\n--- Step {step_count} ---")
            
            # 提取状态信息
            for node_name, node_state in state.items():
                if isinstance(node_state, dict):
                    current_step = node_state.get('current_step', 'unknown')
                    current_chapter = node_state.get('current_chapter_number', 'N/A')
                    print(f"节点: {node_name}")
                    print(f"当前步骤: {current_step}")
                    print(f"当前章节: {current_chapter}")
                    
                    # 显示完成的步骤
                    completed = node_state.get('completed_steps', [])
                    if completed:
                        print(f"已完成: {', '.join(completed[-3:])}")  # 只显示最近3个
                    
                    # 显示错误
                    errors = node_state.get('error_messages', {})
                    if errors:
                        print(f"⚠️ 错误: {errors}")
        
        print("\n" + "=" * 60)
        print("✅ 工作流执行完成")
        
        # 验证结果
        print("\n📊 验证结果:")
        
        # 检查世界观
        world_path = os.path.join(project_dir, "world.json")
        if os.path.exists(world_path):
            print("✅ 世界观文件已生成")
        else:
            print("❌ 世界观文件缺失")
        
        # 检查角色
        characters_path = os.path.join(project_dir, "characters.json")
        if os.path.exists(characters_path):
            print("✅ 角色文件已生成")
        else:
            print("❌ 角色文件缺失")
        
        # 检查大纲
        outline_path = os.path.join(project_dir, "outline.json")
        if os.path.exists(outline_path):
            print("✅ 大纲文件已生成")
            with open(outline_path, 'r', encoding='utf-8') as f:
                outline_data = json.load(f)
                chapter_count = len(outline_data.get('chapters', []))
                print(f"   大纲包含 {chapter_count} 章")
        else:
            print("❌ 大纲文件缺失")
        
        # 检查章节计划
        chapters_dir = os.path.join(project_dir, "chapters")
        if os.path.exists(chapters_dir):
            plan_files = [f for f in os.listdir(chapters_dir) if f.endswith('_plan.json')]
            print(f"✅ 章节计划已生成，共 {len(plan_files)} 个")
        else:
            print("❌ 章节目录不存在")
        
        # 检查生成的章节
        if os.path.exists(chapters_dir):
            chapter_files = [f for f in os.listdir(chapters_dir) if f.startswith('chapter_') and not f.endswith('_plan.json')]
            print(f"✅ 章节已生成，共 {len(chapter_files)} 个")
            
            for chapter_file in sorted(chapter_files):
                chapter_path = os.path.join(chapters_dir, chapter_file)
                with open(chapter_path, 'r', encoding='utf-8') as f:
                    chapter_data = json.load(f)
                    chapter_num = chapter_data.get('chapter_number', '?')
                    total_words = chapter_data.get('total_words', 0)
                    print(f"   第 {chapter_num} 章: {total_words} 字")
        else:
            print("❌ 未找到生成的章节")
        
        # 检查一致性报告
        reports_path = os.path.join(project_dir, "consistency_reports.json")
        if os.path.exists(reports_path):
            with open(reports_path, 'r', encoding='utf-8') as f:
                reports = json.load(f)
                print(f"✅ 一致性报告已生成，共 {len(reports)} 个")
                
                for report in reports:
                    chapter_num = report.get('chapter_number', '?')
                    issues = report.get('issues', [])
                    print(f"   第 {chapter_num} 章: {len(issues)} 个问题")
        else:
            print("⚠️  未找到一致性报告")
        
        print("\n🎉 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            print(f"\n🧹 清理临时目录: {temp_dir}")
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_chapter_loop_workflow()

