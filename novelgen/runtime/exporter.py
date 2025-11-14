"""
小说文本导出模块
将JSON格式的章节数据转换为标准txt格式
"""
import os
import json
from pathlib import Path
from typing import Optional
from novelgen.models import GeneratedChapter, GeneratedScene


def format_chapter_number(chapter_number: int) -> str:
    """
    格式化章节编号
    
    Args:
        chapter_number: 章节编号
        
    Returns:
        格式化后的章节编号字符串，如"第一章"
    """
    chinese_numbers = {
        1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
        6: "六", 7: "七", 8: "八", 9: "九", 10: "十"
    }
    
    if chapter_number <= 10:
        return f"第{chinese_numbers[chapter_number]}章"
    elif chapter_number < 20:
        if chapter_number == 10:
            return "第十章"
        else:
            return f"第十{chinese_numbers[chapter_number - 10]}章"
    elif chapter_number % 10 == 0:
        return f"第{chinese_numbers[chapter_number // 10]}十章"
    else:
        tens = chapter_number // 10
        ones = chapter_number % 10
        return f"第{chinese_numbers[tens]}十{chinese_numbers[ones]}章"


def export_chapter_to_txt(chapter: GeneratedChapter, output_path: str):
    """
    将章节导出为txt文件
    
    格式规范：
    - 章节标题单独一行：第X章 标题
    - 空一行
    - 场景内容（保持原有分段）
    - 场景之间空两行
    
    Args:
        chapter: GeneratedChapter对象
        output_path: 输出文件路径
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
    
    # 写入文件
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✓ 章节已导出: {output_path}")
    print(f"  章节: {chapter_title}")
    print(f"  总字数: {chapter.total_words}")


def export_all_chapters_to_txt(project_dir: str, output_path: str):
    """
    将项目中所有章节合并导出为一个txt文件
    
    格式规范：
    - 按章节编号顺序排列
    - 章节之间空三行
    - 每章内部格式与单章导出相同
    
    Args:
        project_dir: 项目目录路径
        output_path: 输出文件路径
    """
    chapters_dir = os.path.join(project_dir, "chapters")
    
    if not os.path.exists(chapters_dir):
        print(f"✗ 错误: 章节目录不存在: {chapters_dir}")
        return
    
    # 查找所有章节JSON文件（排除计划文件）
    chapter_files = []
    for filename in os.listdir(chapters_dir):
        if filename.startswith("chapter_") and filename.endswith(".json") and "_plan" not in filename:
            chapter_files.append(filename)
    
    if not chapter_files:
        print(f"✗ 错误: 未找到任何章节文件")
        return
    
    # 按章节编号排序
    chapter_files.sort()
    
    lines = []
    total_chapters = 0
    total_words = 0
    
    # 处理每个章节
    for i, filename in enumerate(chapter_files):
        filepath = os.path.join(chapters_dir, filename)
        
        # 读取JSON文件
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
            
            chapter = GeneratedChapter(**chapter_data)
            
            # 章节标题
            chapter_title = f"{format_chapter_number(chapter.chapter_number)} {chapter.chapter_title}"
            lines.append(chapter_title)
            lines.append("")  # 标题后空一行
            
            # 场景内容
            for j, scene in enumerate(chapter.scenes):
                lines.append(scene.content)
                
                # 场景之间空两行（最后一个场景不需要）
                if j < len(chapter.scenes) - 1:
                    lines.append("")
                    lines.append("")
            
            # 章节之间空三行（最后一章不需要）
            if i < len(chapter_files) - 1:
                lines.append("")
                lines.append("")
                lines.append("")
            
            total_chapters += 1
            total_words += chapter.total_words
            
        except Exception as e:
            print(f"✗ 警告: 处理章节文件失败 {filename}: {e}")
            continue
    
    # 写入文件
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✓ 全书已导出: {output_path}")
    print(f"  总章节数: {total_chapters}")
    print(f"  总字数: {total_words}")


def load_chapter_from_json(filepath: str) -> Optional[GeneratedChapter]:
    """
    从JSON文件加载章节数据
    
    Args:
        filepath: JSON文件路径
        
    Returns:
        GeneratedChapter对象，如果加载失败返回None
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            chapter_data = json.load(f)
        return GeneratedChapter(**chapter_data)
    except Exception as e:
        print(f"✗ 加载章节失败 {filepath}: {e}")
        return None

