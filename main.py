"""
NovelGen 主入口
演示如何使用NovelGen生成小说
"""
from novelgen.runtime.orchestrator import NovelOrchestrator


def demo_full_flow():
    """演示完整的小说生成流程"""
    # 创建编排器（verbose=True 将显示详细日志）
    orchestrator = NovelOrchestrator(project_name="demo_001", verbose=False)
    
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
    outline = orchestrator.step4_create_outline(num_chapters=10)
    print(f"章节数: {len(outline.chapters)}")
    
    # 步骤5: 生成第一章计划
    print("\n" + "="*60)
    print("步骤5: 生成章节计划")
    print("="*60)
    chapter_plan = orchestrator.step5_create_chapter_plan(chapter_number=1)
    print(f"第1章: {chapter_plan.chapter_title}")
    print(f"场景数: {len(chapter_plan.scenes)}")
    
    # 步骤6: 生成第一章文本
    print("\n" + "="*60)
    print("步骤6: 生成章节文本")
    print("="*60)
    chapter = orchestrator.step6_generate_chapter_text(chapter_number=1)
    print(f"第1章完成，总字数: {chapter.total_words}")
    
    print("\n" + "="*60)
    print("🎉 演示完成！")
    print("="*60)
    print(f"项目文件已保存到: {orchestrator.project_dir}")


def demo_single_step():
    """演示单步执行"""
    # verbose=True 会显示完整提示词、响应时间和token使用情况
    orchestrator = NovelOrchestrator(project_name="my_novel", verbose=True)
    
    # 只执行某一步
    world = orchestrator.step1_create_world(
        "一个赛博朋克世界，充满了高科技和低生活"
    )
    print(f"世界观已创建: {world.world_name}")


def main():
    """主函数"""
    print("NovelGen - AI小说生成器")
    print("作者: Jamesenh")
    print()
    
    # 取消注释以运行演示
    demo_full_flow()
    # demo_single_step()
    
    print("请取消注释 main() 中的演示函数来运行示例")

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

if __name__ == "__main__":
    test_generate_chapter_text()
