"""
NovelGen 主入口
演示如何使用NovelGen生成小说
"""
from novelgen.runtime.orchestrator import NovelOrchestrator


def demo_full_flow():
    """演示完整的小说生成流程"""
    # 创建编排器（verbose=True 将显示详细日志）
    orchestrator = NovelOrchestrator(project_name="demo_002", verbose=True)
    print(f"项目目录: {orchestrator.project_dir}")
    print("提示：重复运行会自动续写，已生成的阶段会跳过（如需重建可传入 force=True）。")
    
    # 步骤1: 创建世界观
    print("\n" + "="*60)
    print("步骤1: 创建世界观")
    print("="*60)
    world = orchestrator.step1_create_world(
        "一个修真世界，有五大宗门，主角从小宗门崛起"
    )
    print(f"世界名称: {world.world_name}")
    
    # 步骤2: 创建主题冲突
    print("\n" + "="*60)
    print("步骤2: 创建主题冲突")
    print("="*60)
    theme_conflict = orchestrator.step2_create_theme_conflict(
        "关于个人奋斗与宗门争斗的故事"
    )
    print(f"核心主题: {theme_conflict.core_theme}")
    
    # 步骤3: 创建角色
    print("\n" + "="*60)
    print("步骤3: 创建角色")
    print("="*60)
    characters = orchestrator.step3_create_characters()
    print(f"主角: {characters.protagonist.name}")
    
    # 步骤4: 创建大纲
    print("\n" + "="*60)
    print("步骤4: 创建大纲")
    print("="*60)
    outline = orchestrator.step4_create_outline(num_chapters=5)
    print(f"章节数: {len(outline.chapters)}")

    # print("\n" + "="*60)
    # print("步骤5: 生成所有章节文本")
    # print("="*60)
    # orchestrator.generate_all_chapters()
    
    # 步骤5: 生成第一章计划
    print("\n" + "="*60)
    print("步骤5: 生成章节计划")
    print("="*60)
    chapter_plan = orchestrator.step5_create_chapter_plan(chapter_number=[1, 2, 3, 4, 5])
    # print(f"第1章: {chapter_plan.chapter_title}")
    # print(f"场景数: {len(chapter_plan.scenes)}")
    
    # 步骤6: 生成第一章文本
    print("\n" + "="*60)
    print("步骤6: 生成章节文本")
    print("="*60)
    chapter = orchestrator.step6_generate_chapter_text(chapter_number=5)
    print(f"第1章完成，总字数: {chapter.total_words}")
    
    print("\n" + "="*60)
    print("🎉 演示完成！")
    print("="*60)
    print(f"项目文件已保存到: {orchestrator.project_dir}")

    # orchestrator.export_all_chapters()
    # print(f"小说已导出到: {orchestrator.project_dir}/demo_002_full.txt")

def export_novel_cmd(project_name: str):
    """
    导出整本小说为txt文件
    
    Args:
        project_name: 项目名称
    """
    orchestrator = NovelOrchestrator(project_name=project_name)
    orchestrator.export_all_chapters()

def main():
    """主函数"""
    print("NovelGen - AI小说生成器")
    print("作者: Jamesenh")
    print()
    
    demo_full_flow()

def test_world_chain():
    """测试世界观生成链"""
    orchestrator = NovelOrchestrator(project_name="test_world_chain", verbose=True)
    world = orchestrator.step1_create_world("一个修真世界，有五大宗门，主角从小宗门崛起")

def test_create_theme_conflict():
    """测试主题冲突生成链"""
    orchestrator = NovelOrchestrator(project_name="test_world_chain", verbose=True)
    theme_conflict = orchestrator.step2_create_theme_conflict("关于个人奋斗与宗门争斗的故事")

def test_create_characters():
    """测试角色生成链"""
    orchestrator = NovelOrchestrator(project_name="test_world_chain", verbose=True)
    characters = orchestrator.step3_create_characters()

def test_create_outline():
    """测试大纲生成链"""
    orchestrator = NovelOrchestrator(project_name="test_world_chain", verbose=True)
    outline = orchestrator.step4_create_outline(num_chapters=10)

def test_create_chapter_plan():
    """测试章节计划生成链"""
    orchestrator = NovelOrchestrator(project_name="test_world_chain", verbose=True)
    chapter_plan = orchestrator.step5_create_chapter_plan(chapter_number=3)

def test_generate_chapter_text():
    """测试章节文本生成链"""
    orchestrator = NovelOrchestrator(project_name="test_world_chain", verbose=True)
    chapter = orchestrator.step6_generate_chapter_text(chapter_number=1)

def export_chapter_cmd(project_name: str, chapter_number: int):
    """
    导出单个章节为txt文件
    
    Args:
        project_name: 项目名称
        chapter_number: 章节编号
    """
    orchestrator = NovelOrchestrator(project_name=project_name)
    orchestrator.export_chapter(chapter_number)

def export_novel_cmd(project_name: str):
    """
    导出整本小说为txt文件
    
    Args:
        project_name: 项目名称
    """
    orchestrator = NovelOrchestrator(project_name=project_name)
    orchestrator.export_all_chapters()

if __name__ == "__main__":
    # test_generate_chapter_text()
    demo_full_flow()
    # export_novel_cmd("demo_001")
