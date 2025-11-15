#!/usr/bin/env python3
"""测试章节计划批量生成功能"""

from novelgen.runtime.orchestrator import NovelOrchestrator

def test_batch_chapter_plan_generation():
    """测试批量生成章节计划"""
    # 创建编排器实例
    orchestrator = NovelOrchestrator(project_name="demo_test", verbose=False)

    # 执行前置步骤
    print("="*60)
    print("执行前置步骤...")
    print("="*60)

    # 创建世界观
    world_input = "一个未来科幻世界，人类在月球建立了殖民地，发现了神秘的外星文明遗迹。"
    world = orchestrator.step1_create_world(user_input=world_input)
    print(f"✓ 世界观生成完成: {world.world_name}")

    # 创建主题冲突
    theme_conflict = orchestrator.step2_create_theme_conflict()
    print(f"✓ 主题冲突生成完成: {theme_conflict.main_theme}")

    # 创建角色
    characters = orchestrator.step3_create_characters()
    print(f"✓ 角色生成完成: 共{len(characters.main_characters)}个主要角色")

    # 创建大纲
    outline = orchestrator.step4_create_outline(num_chapters=5)
    print(f"✓ 大纲生成完成: 共{len(outline.chapters)}个章节")

    # 1. 测试单个章节生成（验证向后兼容性）
    print("\n" + "="*60)
    print("测试1: 单个章节生成")
    print("="*60)

    try:
        chapter_plan_1 = orchestrator.step5_create_chapter_plan(chapter_number=1)
        print(f"✓ 单个章节生成成功")
        print(f"  章节标题: {chapter_plan_1.chapter_title}")
        print(f"  场景数量: {len(chapter_plan_1.scenes)}")
    except Exception as e:
        print(f"✗ 单个章节生成失败: {e}")
        raise

    # 2. 测试多个章节生成
    print("\n" + "="*60)
    print("测试2: 多个章节生成")
    print("="*60)

    try:
        chapter_plans = orchestrator.step5_create_chapter_plan(chapter_number=[1, 2, 3])
        print(f"✓ 多个章节生成成功")
        print(f"  生成的章节数量: {len(chapter_plans)}")

        for i, plan in enumerate(chapter_plans, 1):
            print(f"  章节 {i}: {plan.chapter_title} ({len(plan.scenes)} 个场景)")
    except Exception as e:
        print(f"✗ 多个章节生成失败: {e}")

    # 3. 测试强制重新生成
    print("\n" + "="*60)
    print("测试3: 强制重新生成")
    print("="*60)

    try:
        chapter_plans = orchestrator.step5_create_chapter_plan(chapter_number=[1, 2], force=True)
        print(f"✓ 强制重新生成成功")
        print(f"  重新生成的章节数量: {len(chapter_plans)}")
    except Exception as e:
        print(f"✗ 强制重新生成失败: {e}")

if __name__ == "__main__":
    test_batch_chapter_plan_generation()