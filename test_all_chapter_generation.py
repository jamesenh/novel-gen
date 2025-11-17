#!/usr/bin/env python3
"""
测试 add-all-chapter-generation 功能
验证单章、部分章节、全部章节生成是否正常工作
"""

import os
import shutil
from novelgen.runtime.orchestrator import NovelOrchestrator

def test_all_chapter_generation():
    """测试全部章节生成功能"""
    project_name = "test_all_chapters"
    
    # 清理已存在的测试项目
    if os.path.exists(f"projects/{project_name}"):
        shutil.rmtree(f"projects/{project_name}")
    
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
    
    print("=" * 60)
    print("测试 add-all-chapter-generation 功能")
    print("=" * 60)
    
    # 步骤1-4：准备基础数据
    print("\n1. 创建基础数据...")
    world = orchestrator.step1_create_world("一个修真世界，有五大宗门")
    theme = orchestrator.step2_create_theme_conflict("个人奋斗与宗门争斗")
    characters = orchestrator.step3_create_characters()
    outline = orchestrator.step4_create_outline(num_chapters=5)
    print(f"   已创建大纲，包含 {len(outline.chapters)} 章")
    
    # 测试1：生成全部章节计划
    print("\n2. 测试生成全部章节计划...")
    all_plans = orchestrator.step5_create_chapter_plan()  # 不传参数
    print(f"   成功生成 {len(all_plans)} 个章节计划")
    assert len(all_plans) == 5, "应该生成5个章节计划"
    
    # 测试2：生成部分章节计划
    print("\n3. 测试生成部分章节计划...")
    partial_plans = orchestrator.step5_create_chapter_plan(chapter_number=[1, 3, 5])
    print(f"   成功生成 {len(partial_plans)} 个章节计划")
    assert len(partial_plans) == 3, "应该生成3个章节计划"
    
    # 测试3：生成单个章节计划
    print("\n4. 测试生成单个章节计划...")
    single_plan = orchestrator.step5_create_chapter_plan(chapter_number=2)
    print(f"   成功生成第2章计划")
    assert single_plan.chapter_number == 2, "应该是第2章"
    
    # 测试4：生成部分章节文本
    print("\n5. 测试生成部分章节文本...")
    orchestrator.generate_all_chapters(chapter_numbers=[1, 2])
    
    # 验证文件存在
    for i in [1, 2]:
        file_path = f"projects/{project_name}/chapters/chapter_{i:03d}.json"
        assert os.path.exists(file_path), f"章节{i}文件应该存在"
    print("   成功生成第1-2章文本")
    
    # 测试5：生成剩余章节文本
    print("\n6. 测试生成剩余章节文本...")
    orchestrator.generate_all_chapters(chapter_numbers=[3, 4, 5])
    
    # 验证所有文件存在
    for i in range(1, 6):
        file_path = f"projects/{project_name}/chapters/chapter_{i:03d}.json"
        assert os.path.exists(file_path), f"章节{i}文件应该存在"
    print("   成功生成第3-5章文本")
    
    # 测试6：测试错误处理
    print("\n7. 测试错误处理...")
    try:
        orchestrator.generate_all_chapters(chapter_numbers=[99])  # 不存在的章节
        assert False, "应该抛出异常"
    except ValueError as e:
        print(f"   正确捕获异常: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    
    # 清理测试项目
    if os.path.exists(f"projects/{project_name}"):
        shutil.rmtree(f"projects/{project_name}")

if __name__ == "__main__":
    test_all_chapter_generation()
