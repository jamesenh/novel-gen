"""
NovelGen 主入口
演示如何使用NovelGen生成小说
"""
from novelgen.runtime.orchestrator import NovelOrchestrator


def demo_full_flow(project_name):
    """演示完整的小说生成流程"""
    # 创建编排器（verbose=True 将显示详细日志）
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
    print(f"项目目录: {orchestrator.project_dir}")
    print("提示：重复运行会自动续写，已生成的阶段会跳过(如需重建可传入 force=True)。")
    
    # 步骤1: 创建世界观
    print("\n" + "="*60)
    print("步骤1: 创建世界观")
    print("="*60)
    world = orchestrator.step1_create_world(
        "一个2242年的未来地球，人类经历了\"大觉醒\"事件后，部分人类获得了操控量子能量的能力。社会分裂为三大阵营：保守的\"纯种人类联盟\"、追求进化的\"量子觉醒者\"、以及半机械改造的\"赛博融合体\"。地球资源枯竭，三大阵营争夺着火星殖民地的控制权，同时外太空的\"星际观察者\"文明正在默默关注着人类的内斗。科技高度发达，意识上传、虚拟现实、时空扭曲技术已经成熟，但也带来了伦理危机和身份认同的混乱。"
    )
    print(f"世界名称: {world.world_name}")
    
    # 步骤2: 创建主题冲突
    print("\n" + "="*60)
    print("步骤2: 创建主题冲突")
    print("="*60)
    theme_conflict = orchestrator.step2_create_theme_conflict(
        "关于人性与科技边界的故事：当人类能够通过科技无限强化自身时，什么才是真正的\"人类\"？探讨在追求永生和超能力的过程中，人类是否正在失去最珍贵的情感和道德底线。故事聚焦于一个来自保守阵营的年轻人意外觉醒量子能力后，在三大阵营间的艰难抉择，以及他对\"人性本质\"的重新定义。核心冲突包括：传统价值观 vs 科技进化、个体自由 vs 集体利益、真实情感 vs 虚拟体验。"
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
    outline = orchestrator.step4_create_outline(num_chapters=3)
    print(f"章节数: {len(outline.chapters)}")

    # print("\n" + "="*60)
    # print("步骤5: 生成所有章节文本")
    # print("="*60)
    # orchestrator.generate_all_chapters()
    
    # 步骤5: 生成章节计划（演示全部章节生成）
    print("\n" + "="*60)
    print("步骤5: 生成章节计划（全部章节）")
    print("="*60)
    chapter_plans = orchestrator.step5_create_chapter_plan()  # 不传参数，自动生成全部章节
    print(f"已生成 {len(chapter_plans)} 个章节计划")
    
    # 步骤6: 生成章节文本（演示部分章节生成）
    print("\n" + "="*60)
    print("步骤6: 生成章节文本（全部章节）")
    print("="*60)
    orchestrator.generate_all_chapters()  # 生成全部章节
    print("已生成全部章节文本")
    
    # 可选：生成剩余章节
    # print("\n" + "="*60)
    # print("生成剩余章节文本")
    # print("="*60)
    # orchestrator.generate_all_chapters()  # 生成全部章节
    # print("已生成全部章节文本")
    
    orchestrator.export_all_chapters()

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

def export_novel_cmd(project_name: str):
    """
    导出整本小说为txt文件
    
    Args:
        project_name: 项目名称
    """
    orchestrator = NovelOrchestrator(project_name=project_name)
    orchestrator.export_all_chapters()

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
        demo_full_flow("demo_008")
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    # export_novel_cmd("demo_001")
    # apply_revision_cmd("demo_005", 1)
