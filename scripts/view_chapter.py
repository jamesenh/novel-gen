#!/usr/bin/env python3
"""
交互式章节查看工具
将小说章节内容格式化输出到控制台，便于直接复制到 Word

作者: Jamesenh
日期: 2025-11-30
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from novelgen.runtime.exporter import format_chapter_number, load_chapter_from_json
from novelgen.models import GeneratedChapter


def get_projects_dir() -> Path:
    """获取项目目录路径"""
    return PROJECT_ROOT / "projects"


def list_projects() -> list[str]:
    """列出所有可用项目"""
    projects_dir = get_projects_dir()
    if not projects_dir.exists():
        return []
    
    projects = []
    for item in sorted(projects_dir.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            # 检查是否有 chapters 目录
            chapters_dir = item / "chapters"
            if chapters_dir.exists():
                projects.append(item.name)
    return projects


def list_chapters(project_name: str) -> list[tuple[str, str, int]]:
    """
    列出项目中所有章节
    
    Returns:
        列表，每项为 (文件路径, 章节标题, 字数)
    """
    chapters_dir = get_projects_dir() / project_name / "chapters"
    if not chapters_dir.exists():
        return []
    
    chapters = []
    for filename in sorted(chapters_dir.iterdir()):
        # 只处理章节文件，排除计划文件
        if filename.name.startswith("chapter_") and filename.name.endswith(".json") and "_plan" not in filename.name:
            chapter = load_chapter_from_json(str(filename))
            if chapter:
                title = f"{format_chapter_number(chapter.chapter_number)} {chapter.chapter_title}"
                chapters.append((str(filename), title, chapter.total_words))
    
    return chapters


def format_chapter_content(chapter: GeneratedChapter) -> str:
    """
    格式化章节内容为可直接复制的文本
    
    Args:
        chapter: GeneratedChapter 对象
        
    Returns:
        格式化后的章节文本
    """
    lines = []
    
    # 章节标题
    chapter_title = f"{format_chapter_number(chapter.chapter_number)} {chapter.chapter_title}"
    lines.append(chapter_title)
    lines.append("")  # 标题后空一行
    
    # 遍历所有场景
    for i, scene in enumerate(chapter.scenes):
        # 添加场景内容
        lines.append(scene.content)
        
        # 场景之间空两行（最后一个场景不需要）
        if i < len(chapter.scenes) - 1:
            lines.append("")
            lines.append("")
    
    return '\n'.join(lines)


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 20} {title} {'=' * 20}\n")
    else:
        print("\n" + "=" * 60 + "\n")


def select_project() -> str | None:
    """交互式选择项目"""
    projects = list_projects()
    
    if not projects:
        print("错误: 未找到任何项目")
        return None
    
    print("\n请选择项目:")
    for i, project in enumerate(projects, 1):
        print(f"  {i}. {project}")
    
    while True:
        try:
            choice = input("\n输入编号 (q=退出): ").strip()
            if choice.lower() == 'q':
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                return projects[idx]
            else:
                print("无效的编号，请重新输入")
        except ValueError:
            print("请输入有效的数字")


def select_chapter(project_name: str) -> int | None:
    """
    交互式选择章节
    
    Returns:
        章节索引 (0-based)，-1 表示全部，None 表示退出
    """
    chapters = list_chapters(project_name)
    
    if not chapters:
        print(f"错误: 项目 {project_name} 中未找到任何章节")
        return None
    
    print(f"\n项目 {project_name} 的章节列表:")
    for i, (_, title, words) in enumerate(chapters, 1):
        print(f"  {i}. {title} ({words}字)")
    
    while True:
        try:
            choice = input("\n输入章节编号 (0=全部, q=退出): ").strip()
            if choice.lower() == 'q':
                return None
            
            idx = int(choice)
            if idx == 0:
                return -1  # 表示全部
            elif 1 <= idx <= len(chapters):
                return idx - 1
            else:
                print("无效的编号，请重新输入")
        except ValueError:
            print("请输入有效的数字")


def view_single_chapter(filepath: str):
    """查看单个章节"""
    chapter = load_chapter_from_json(filepath)
    if not chapter:
        print(f"错误: 无法加载章节文件: {filepath}")
        return
    
    title = f"{format_chapter_number(chapter.chapter_number)} {chapter.chapter_title}"
    print_separator(title)
    
    # 直接打印格式化后的内容
    content = format_chapter_content(chapter)
    print(content)
    
    print_separator()
    print(f"字数统计: {chapter.total_words}字")


def view_all_chapters(project_name: str):
    """查看所有章节"""
    chapters = list_chapters(project_name)
    
    for i, (filepath, title, _) in enumerate(chapters):
        chapter = load_chapter_from_json(filepath)
        if not chapter:
            continue
        
        print_separator(title)
        content = format_chapter_content(chapter)
        print(content)
        
        # 如果不是最后一章，询问是否继续
        if i < len(chapters) - 1:
            choice = input("\n按回车继续查看下一章，输入 q 退出: ").strip()
            if choice.lower() == 'q':
                break
    
    print_separator()
    print("已查看完所有章节")


def interactive_mode():
    """交互式模式主循环"""
    print("=" * 50)
    print("      小说章节查看工具")
    print("      内容可直接复制到 Word")
    print("=" * 50)
    
    while True:
        # 选择项目
        project = select_project()
        if not project:
            print("\n再见！")
            break
        
        while True:
            # 选择章节
            chapter_idx = select_chapter(project)
            if chapter_idx is None:
                break  # 返回项目选择
            
            chapters = list_chapters(project)
            
            if chapter_idx == -1:
                # 查看全部章节
                view_all_chapters(project)
            else:
                # 查看单个章节
                filepath = chapters[chapter_idx][0]
                view_single_chapter(filepath)
            
            # 询问是否继续
            choice = input("\n按回车选择其他章节，输入 b 返回项目选择，输入 q 退出: ").strip()
            if choice.lower() == 'q':
                print("\n再见！")
                return
            elif choice.lower() == 'b':
                break


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="交互式章节查看工具 - 将小说章节输出到控制台便于复制",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 交互式模式
  %(prog)s demo_001           # 直接指定项目进入章节选择
  %(prog)s demo_001 1         # 直接查看 demo_001 的第1章
  %(prog)s demo_001 0         # 查看 demo_001 的所有章节
        """
    )
    parser.add_argument("project", nargs="?", help="项目名称")
    parser.add_argument("chapter", nargs="?", type=int, help="章节编号 (0=全部)")
    
    args = parser.parse_args()
    
    if args.project is None:
        # 完全交互式模式
        interactive_mode()
    elif args.chapter is None:
        # 指定项目，交互选择章节
        print("=" * 50)
        print("      小说章节查看工具")
        print("      内容可直接复制到 Word")
        print("=" * 50)
        
        chapters = list_chapters(args.project)
        if not chapters:
            print(f"错误: 项目 {args.project} 不存在或没有章节")
            sys.exit(1)
        
        while True:
            chapter_idx = select_chapter(args.project)
            if chapter_idx is None:
                print("\n再见！")
                break
            
            if chapter_idx == -1:
                view_all_chapters(args.project)
            else:
                filepath = chapters[chapter_idx][0]
                view_single_chapter(filepath)
            
            choice = input("\n按回车选择其他章节，输入 q 退出: ").strip()
            if choice.lower() == 'q':
                print("\n再见！")
                break
    else:
        # 直接指定项目和章节
        chapters = list_chapters(args.project)
        if not chapters:
            print(f"错误: 项目 {args.project} 不存在或没有章节")
            sys.exit(1)
        
        if args.chapter == 0:
            # 查看全部
            view_all_chapters(args.project)
        elif 1 <= args.chapter <= len(chapters):
            filepath = chapters[args.chapter - 1][0]
            view_single_chapter(filepath)
        else:
            print(f"错误: 章节编号 {args.chapter} 无效，有效范围: 1-{len(chapters)}")
            sys.exit(1)


if __name__ == "__main__":
    main()

