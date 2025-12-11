"""
导出服务

封装章节导出逻辑，支持 TXT/Markdown/JSON 三种格式。

开发者: jamesenh
日期: 2025-12-08
"""
import json
import os
from typing import Optional

from novelgen.models import GeneratedChapter
from novelgen.runtime.exporter import (
    export_all_chapters_to_txt,
    export_chapter_to_txt,
    load_chapter_from_json,
)

PROJECTS_ROOT = os.getenv("NOVELGEN_PROJECTS_DIR", "projects")


def _chapters_dir(project_name: str) -> str:
    return os.path.join(PROJECTS_ROOT, project_name, "chapters")


def export_full_txt(project_name: str) -> str:
    """导出全书 TXT，返回文件路径"""
    project_dir = os.path.join(PROJECTS_ROOT, project_name)
    output_path = os.path.join(project_dir, f"{project_name}_full.txt")
    export_all_chapters_to_txt(project_dir, output_path)
    return output_path


def export_chapter_txt(project_name: str, chapter_num: int) -> str:
    """导出单章 TXT，返回文件路径"""
    chapter_path = os.path.join(_chapters_dir(project_name), f"chapter_{chapter_num:03d}.json")
    chapter = load_chapter_from_json(chapter_path)
    if chapter is None:
        raise FileNotFoundError(f"章节 {chapter_num} 不存在")
    output_path = os.path.join(_chapters_dir(project_name), f"chapter_{chapter_num:03d}.txt")
    export_chapter_to_txt(chapter, output_path)
    return output_path


def export_markdown(project_name: str, chapter_num: Optional[int] = None) -> str:
    """导出 Markdown，返回文件路径"""
    chapters = _load_chapters(project_name)
    if chapter_num is not None:
        chapters = [c for c in chapters if c.chapter_number == chapter_num]
        if not chapters:
            raise FileNotFoundError(f"章节 {chapter_num} 不存在")

    lines = []
    for chapter in chapters:
        lines.append(f"# 第{chapter.chapter_number}章 {chapter.chapter_title}")
        lines.append("")
        for scene in chapter.scenes:
            lines.append(f"## 场景 {scene.scene_number}")
            lines.append("")
            lines.append(scene.content)
            lines.append("")
        lines.append("---")
        lines.append("")

    project_dir = os.path.join(PROJECTS_ROOT, project_name)
    filename = f"{project_name}_chapter_{chapter_num:03d}.md" if chapter_num else f"{project_name}_full.md"
    output_path = os.path.join(project_dir, filename)
    os.makedirs(project_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path


def export_json(project_name: str, chapter_num: Optional[int] = None) -> str:
    """导出结构化 JSON，返回文件路径"""
    chapters = _load_chapters(project_name)
    if chapter_num is not None:
        chapters = [c for c in chapters if c.chapter_number == chapter_num]
        if not chapters:
            raise FileNotFoundError(f"章节 {chapter_num} 不存在")

    payload = [c.model_dump() for c in chapters]
    project_dir = os.path.join(PROJECTS_ROOT, project_name)
    filename = f"{project_name}_chapter_{chapter_num:03d}.json" if chapter_num else f"{project_name}_full.json"
    output_path = os.path.join(project_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path


def _load_chapters(project_name: str):
    """加载所有已生成章节"""
    chapters = []
    for file in sorted(os.listdir(_chapters_dir(project_name))):
        if not file.startswith("chapter_") or not file.endswith(".json") or "_plan" in file:
            continue
        path = os.path.join(_chapters_dir(project_name), file)
        chapter = load_chapter_from_json(path)
        if chapter:
            chapters.append(chapter)
    return chapters


