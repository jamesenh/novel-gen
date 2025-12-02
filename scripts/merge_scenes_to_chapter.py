#!/usr/bin/env python3
"""
合并场景文件为章节文件

将指定章节的所有场景 JSON 文件合并为一个完整的章节 JSON 文件。
用于修复场景已生成但章节文件缺失的情况。

开发者: Jamesenh
开发时间: 2025-11-30

用法:
    python scripts/merge_scenes_to_chapter.py <project_name> <chapter_number>
    
示例:
    python scripts/merge_scenes_to_chapter.py demo_020 7
    python scripts/merge_scenes_to_chapter.py demo_020 7 8 9  # 合并多个章节
    python scripts/merge_scenes_to_chapter.py demo_020 --all  # 合并所有未完成的章节
"""
import os
import sys
import json
import argparse
from typing import List, Optional

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from novelgen.models import ChapterPlan, GeneratedChapter, GeneratedScene


def load_json(filepath: str):
    """加载 JSON 文件"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, filepath: str):
    """保存 JSON 文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_project_dir(project_name: str) -> str:
    """获取项目目录"""
    return os.path.join(project_root, "projects", project_name)


def merge_scenes_to_chapter(
    project_name: str, 
    chapter_number: int,
    force: bool = False
) -> Optional[GeneratedChapter]:
    """
    合并指定章节的场景文件为章节文件
    
    Args:
        project_name: 项目名称
        chapter_number: 章节编号
        force: 是否强制覆盖已存在的章节文件
        
    Returns:
        合并后的章节对象，失败返回 None
    """
    project_dir = get_project_dir(project_name)
    chapters_dir = os.path.join(project_dir, "chapters")
    
    # 检查项目目录
    if not os.path.exists(chapters_dir):
        print(f"❌ 章节目录不存在: {chapters_dir}")
        return None
    
    # 章节文件路径
    chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")
    plan_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}_plan.json")
    
    # 检查章节文件是否已存在
    if os.path.exists(chapter_file) and not force:
        print(f"⚠️ 第 {chapter_number} 章文件已存在: {chapter_file}")
        print("   使用 --force 参数强制覆盖")
        return None
    
    # 加载章节计划
    plan_data = load_json(plan_file)
    if not plan_data:
        print(f"❌ 章节计划文件不存在: {plan_file}")
        return None
    
    plan = ChapterPlan(**plan_data)
    print(f"📋 章节计划: {plan.chapter_title}")
    print(f"   预期场景数: {len(plan.scenes)}")
    
    # 加载所有场景文件
    scenes: List[GeneratedScene] = []
    missing_scenes: List[int] = []
    
    for scene_plan in plan.scenes:
        scene_file = os.path.join(
            chapters_dir,
            f"scene_{chapter_number:03d}_{scene_plan.scene_number:03d}.json"
        )
        
        if os.path.exists(scene_file):
            scene_data = load_json(scene_file)
            scene = GeneratedScene(**scene_data)
            scenes.append(scene)
            print(f"   ✅ 场景 {scene_plan.scene_number}: {scene.word_count} 字")
        else:
            missing_scenes.append(scene_plan.scene_number)
            print(f"   ❌ 场景 {scene_plan.scene_number}: 文件缺失")
    
    # 检查是否有缺失的场景
    if missing_scenes:
        print(f"\n⚠️ 缺失 {len(missing_scenes)} 个场景: {missing_scenes}")
        print("   无法合并不完整的章节")
        return None
    
    # 合并场景为章节
    total_words = sum(s.word_count for s in scenes)
    chapter = GeneratedChapter(
        chapter_number=chapter_number,
        chapter_title=plan.chapter_title,
        scenes=scenes,
        total_words=total_words
    )
    
    # 保存章节文件
    save_json(chapter.model_dump(), chapter_file)
    
    print(f"\n✅ 章节合并成功!")
    print(f"   文件: {chapter_file}")
    print(f"   场景数: {len(scenes)}")
    print(f"   总字数: {total_words:,}")
    
    return chapter


def find_incomplete_chapters(project_name: str) -> List[int]:
    """
    查找所有未完成的章节（有场景文件但无章节文件）
    
    Args:
        project_name: 项目名称
        
    Returns:
        未完成章节的编号列表
    """
    import re
    
    project_dir = get_project_dir(project_name)
    chapters_dir = os.path.join(project_dir, "chapters")
    
    if not os.path.exists(chapters_dir):
        return []
    
    # 扫描场景文件，按章节分组
    scene_pattern = re.compile(r"scene_(\d{3})_(\d{3})\.json")
    scenes_by_chapter = {}
    
    for filename in os.listdir(chapters_dir):
        match = scene_pattern.match(filename)
        if match:
            chapter_num = int(match.group(1))
            scene_num = int(match.group(2))
            if chapter_num not in scenes_by_chapter:
                scenes_by_chapter[chapter_num] = []
            scenes_by_chapter[chapter_num].append(scene_num)
    
    # 找出有场景但无章节文件的章节
    incomplete = []
    for chapter_num in sorted(scenes_by_chapter.keys()):
        chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num:03d}.json")
        plan_file = os.path.join(chapters_dir, f"chapter_{chapter_num:03d}_plan.json")
        
        if os.path.exists(chapter_file):
            continue  # 章节已存在
        
        if not os.path.exists(plan_file):
            continue  # 无计划文件
        
        # 检查是否所有场景都已生成
        plan_data = load_json(plan_file)
        if plan_data:
            plan = ChapterPlan(**plan_data)
            expected_scenes = {s.scene_number for s in plan.scenes}
            existing_scenes = set(scenes_by_chapter[chapter_num])
            
            if expected_scenes <= existing_scenes:
                incomplete.append(chapter_num)
    
    return incomplete


def main():
    parser = argparse.ArgumentParser(
        description="合并场景文件为章节文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/merge_scenes_to_chapter.py demo_020 7
  python scripts/merge_scenes_to_chapter.py demo_020 7 8 9
  python scripts/merge_scenes_to_chapter.py demo_020 --all
  python scripts/merge_scenes_to_chapter.py demo_020 --all --force
        """
    )
    
    parser.add_argument(
        "project_name",
        help="项目名称"
    )
    
    parser.add_argument(
        "chapters",
        nargs="*",
        type=int,
        help="要合并的章节编号（可以指定多个）"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="合并所有未完成的章节"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制覆盖已存在的章节文件"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="仅列出未完成的章节，不执行合并"
    )
    
    args = parser.parse_args()
    
    # 检查项目是否存在
    project_dir = get_project_dir(args.project_name)
    if not os.path.exists(project_dir):
        print(f"❌ 项目不存在: {args.project_name}")
        sys.exit(1)
    
    print(f"📁 项目: {args.project_name}")
    print(f"   目录: {project_dir}")
    print()
    
    # 列出未完成章节模式
    if args.list:
        incomplete = find_incomplete_chapters(args.project_name)
        if incomplete:
            print(f"🔍 发现 {len(incomplete)} 个未完成章节:")
            for ch in incomplete:
                print(f"   - 第 {ch} 章")
        else:
            print("✅ 没有未完成的章节")
        sys.exit(0)
    
    # 确定要合并的章节
    if args.all:
        chapters_to_merge = find_incomplete_chapters(args.project_name)
        if not chapters_to_merge:
            print("✅ 没有需要合并的章节")
            sys.exit(0)
        print(f"🔍 发现 {len(chapters_to_merge)} 个待合并章节: {chapters_to_merge}")
        print()
    elif args.chapters:
        chapters_to_merge = args.chapters
    else:
        print("❌ 请指定章节编号或使用 --all 参数")
        parser.print_help()
        sys.exit(1)
    
    # 执行合并
    success_count = 0
    fail_count = 0
    
    for chapter_num in chapters_to_merge:
        print(f"{'='*60}")
        print(f"📖 处理第 {chapter_num} 章")
        print(f"{'='*60}")
        
        result = merge_scenes_to_chapter(
            args.project_name,
            chapter_num,
            force=args.force
        )
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        print()
    
    # 汇总结果
    print(f"{'='*60}")
    print(f"📊 合并结果汇总")
    print(f"{'='*60}")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")


if __name__ == "__main__":
    main()

