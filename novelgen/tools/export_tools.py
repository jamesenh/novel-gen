"""
导出工具模块
提供 export.chapter / export.all 等细粒度导出工具

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, List
from datetime import datetime

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult
from novelgen.models import GeneratedChapter
from novelgen.runtime.exporter import export_chapter_to_txt, export_all_chapters_to_txt


def create_export_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建导出工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    chapters_dir = os.path.join(project_dir, "chapters")
    
    def export_chapter(
        chapter_number: int,
        output_path: Optional[str] = None
    ) -> ToolResult:
        """导出单个章节为 txt 文件
        
        Args:
            chapter_number: 章节编号
            output_path: 输出路径（可选，默认保存到 chapters/chapter_XXX.txt）
            
        Returns:
            导出结果的 ToolResult
        """
        try:
            # 检查章节是否存在
            chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")
            if not os.path.exists(chapter_file):
                return ToolResult(
                    tool_name="export.chapter",
                    success=False,
                    error=f"第 {chapter_number} 章不存在"
                )
            
            # 加载章节数据
            with open(chapter_file, 'r', encoding='utf-8') as f:
                chapter = GeneratedChapter(**json.load(f))
            
            # 确定输出路径
            if output_path is None:
                output_path = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.txt")
            
            # 导出
            export_chapter_to_txt(chapter, output_path)
            
            return ToolResult(
                tool_name="export.chapter",
                success=True,
                message=f"第 {chapter_number} 章已导出",
                data={
                    "chapter_number": chapter_number,
                    "output_path": output_path,
                    "word_count": chapter.total_words
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="export.chapter",
                success=False,
                error=str(e)
            )
    
    def export_all(output_path: Optional[str] = None) -> ToolResult:
        """导出所有章节为单个 txt 文件
        
        Args:
            output_path: 输出路径（可选，默认保存到 {project_id}_full.txt）
            
        Returns:
            导出结果的 ToolResult
        """
        try:
            # 检查是否有章节
            if not os.path.exists(chapters_dir):
                return ToolResult(
                    tool_name="export.all",
                    success=False,
                    error="没有可导出的章节"
                )
            
            # 统计章节数
            chapter_files = [f for f in os.listdir(chapters_dir) 
                           if f.startswith("chapter_") and f.endswith(".json") 
                           and "_plan" not in f]
            
            if not chapter_files:
                return ToolResult(
                    tool_name="export.all",
                    success=False,
                    error="没有可导出的章节"
                )
            
            # 确定输出路径
            if output_path is None:
                output_path = os.path.join(project_dir, f"{project_id}_full.txt")
            
            # 导出
            export_all_chapters_to_txt(project_dir, output_path)
            
            # 统计总字数
            total_words = 0
            chapter_count = len(chapter_files)
            for cf in chapter_files:
                try:
                    with open(os.path.join(chapters_dir, cf), 'r', encoding='utf-8') as f:
                        ch = json.load(f)
                        total_words += ch.get("total_words", 0)
                except:
                    pass
            
            return ToolResult(
                tool_name="export.all",
                success=True,
                message=f"已导出 {chapter_count} 章，共 {total_words:,} 字",
                data={
                    "output_path": output_path,
                    "chapter_count": chapter_count,
                    "total_words": total_words
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="export.all",
                success=False,
                error=str(e)
            )

    def export_range(
        chapter_start: int,
        chapter_end: int,
        output_dir: Optional[str] = None
    ) -> ToolResult:
        """导出章节范围内的多个章节为 txt 文件
        
        Args:
            chapter_start: 起始章节编号（包含）
            chapter_end: 结束章节编号（包含）
            output_dir: 输出目录（可选，默认 chapters/）
            
        Returns:
            导出结果的 ToolResult
        """
        try:
            if chapter_start <= 0 or chapter_end <= 0:
                return ToolResult(
                    tool_name="export.range",
                    success=False,
                    error="章节编号必须为正整数"
                )
            if chapter_start > chapter_end:
                return ToolResult(
                    tool_name="export.range",
                    success=False,
                    error=f"章节范围无效: {chapter_start}-{chapter_end}"
                )
            
            target_dir = output_dir or chapters_dir
            os.makedirs(target_dir, exist_ok=True)
            
            missing = []
            output_paths: List[str] = []
            total_words = 0
            exported = 0
            
            for chapter_number in range(chapter_start, chapter_end + 1):
                chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")
                if not os.path.exists(chapter_file):
                    missing.append(chapter_number)
                    continue
                
                with open(chapter_file, 'r', encoding='utf-8') as f:
                    chapter = GeneratedChapter(**json.load(f))
                
                out_path = os.path.join(target_dir, f"chapter_{chapter_number:03d}.txt")
                export_chapter_to_txt(chapter, out_path)
                
                output_paths.append(out_path)
                total_words += chapter.total_words
                exported += 1
            
            if missing:
                return ToolResult(
                    tool_name="export.range",
                    success=False,
                    error=f"以下章节不存在，未导出: {missing}"
                )
            
            return ToolResult(
                tool_name="export.range",
                success=True,
                message=f"已导出 {exported} 章，共 {total_words:,} 字",
                data={
                    "chapter_start": chapter_start,
                    "chapter_end": chapter_end,
                    "chapter_count": exported,
                    "total_words": total_words,
                    "output_paths": output_paths
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="export.range",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="export.chapter",
            category=ToolCategory.FINE_GRAINED,
            description="导出单个章节为 txt 文件",
            confirm_level=ConfirmLevel.NONE,
            handler=export_chapter
        ),
        Tool(
            name="export.range",
            category=ToolCategory.FINE_GRAINED,
            description="导出多个章节为 txt 文件（按范围）",
            confirm_level=ConfirmLevel.NONE,
            handler=export_range
        ),
        Tool(
            name="export.all",
            category=ToolCategory.FINE_GRAINED,
            description="导出所有章节为单个 txt 文件",
            confirm_level=ConfirmLevel.NONE,
            handler=export_all
        ),
    ]
    
    return tools
