"""
大纲工具模块
提供 outline.generate / outline.extend 等细粒度工具

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, Dict, Any

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult
from novelgen.models import WorldSetting, ThemeConflict, CharactersConfig, Outline


def create_outline_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建大纲工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    
    def _load_prereqs() -> tuple:
        """加载前置依赖
        
        Returns:
            (world, theme_conflict, characters) 元组
        """
        world_file = os.path.join(project_dir, "world.json")
        theme_file = os.path.join(project_dir, "theme_conflict.json")
        char_file = os.path.join(project_dir, "characters.json")
        
        world = None
        theme_conflict = None
        characters = None
        
        if os.path.exists(world_file):
            with open(world_file, 'r', encoding='utf-8') as f:
                world = WorldSetting(**json.load(f))
        
        if os.path.exists(theme_file):
            with open(theme_file, 'r', encoding='utf-8') as f:
                theme_conflict = ThemeConflict(**json.load(f))
        
        if os.path.exists(char_file):
            with open(char_file, 'r', encoding='utf-8') as f:
                characters = CharactersConfig(**json.load(f))
        
        return world, theme_conflict, characters
    
    def generate_outline(
        num_chapters: Optional[int] = None,
        initial_chapters: Optional[int] = None,
        max_chapters: Optional[int] = None,
        force: bool = False
    ) -> ToolResult:
        """生成大纲
        
        Args:
            num_chapters: 固定章节数量（与 initial_chapters/max_chapters 互斥）
            initial_chapters: 初始章节数量（动态模式）
            max_chapters: 最大章节数量（动态模式）
            force: 是否强制覆盖已存在的大纲
            
        Returns:
            生成结果的 ToolResult
        """
        try:
            outline_file = os.path.join(project_dir, "outline.json")
            
            # 检查是否已存在
            if os.path.exists(outline_file) and not force:
                with open(outline_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                existing_count = len(existing.get("chapters", []))
                return ToolResult(
                    tool_name="outline.generate",
                    success=True,
                    message=f"大纲已存在（{existing_count} 章），使用 force=true 强制覆盖",
                    data={"exists": True, "chapter_count": existing_count, "skipped": True}
                )
            
            # 加载前置依赖
            world, theme_conflict, characters = _load_prereqs()
            
            missing = []
            if world is None:
                missing.append("world")
            if theme_conflict is None:
                missing.append("theme_conflict")
            if characters is None:
                missing.append("characters")
            
            if missing:
                return ToolResult(
                    tool_name="outline.generate",
                    success=False,
                    error=f"缺失前置依赖: {', '.join(missing)}",
                    data={"missing_deps": missing}
                )
            
            # 确定章节数量
            settings_file = os.path.join(project_dir, "settings.json")
            if num_chapters is None and initial_chapters is None:
                # 从 settings.json 读取
                if os.path.exists(settings_file):
                    with open(settings_file, 'r', encoding='utf-8') as f:
                        settings_data = json.load(f)
                    initial_chapters = settings_data.get("initial_chapters", 5)
                    max_chapters = settings_data.get("max_chapters", 50)
                else:
                    initial_chapters = 5
                    max_chapters = 50
            
            # 调用大纲生成链
            from novelgen.chains.outline_chain import generate_outline as gen_outline, generate_initial_outline
            
            if num_chapters is not None:
                # 固定模式
                outline = gen_outline(
                    world_setting=world,
                    theme_conflict=theme_conflict,
                    characters=characters,
                    num_chapters=num_chapters,
                    verbose=False
                )
                outline.is_complete = True
                outline.current_phase = "complete"
            else:
                # 动态模式
                outline = generate_initial_outline(
                    world_setting=world,
                    theme_conflict=theme_conflict,
                    characters=characters,
                    initial_chapters=initial_chapters,
                    verbose=False
                )
            
            # 保存大纲
            with open(outline_file, 'w', encoding='utf-8') as f:
                json.dump(outline.model_dump(), f, ensure_ascii=False, indent=2)
            
            chapter_count = len(outline.chapters)
            
            return ToolResult(
                tool_name="outline.generate",
                success=True,
                message=f"大纲生成成功，共 {chapter_count} 章",
                data={
                    "chapter_count": chapter_count,
                    "is_complete": outline.is_complete,
                    "current_phase": outline.current_phase,
                    "file": outline_file
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="outline.generate",
                success=False,
                error=str(e)
            )
    
    def extend_outline(
        additional_chapters: int,
        force: bool = False
    ) -> ToolResult:
        """扩展大纲
        
        Args:
            additional_chapters: 要添加的章节数量
            force: 是否强制扩展（即使大纲已标记为完成）
            
        Returns:
            扩展结果的 ToolResult
        """
        try:
            outline_file = os.path.join(project_dir, "outline.json")
            
            # 检查大纲是否存在
            if not os.path.exists(outline_file):
                return ToolResult(
                    tool_name="outline.extend",
                    success=False,
                    error="大纲不存在，请先使用 outline.generate 生成大纲"
                )
            
            # 加载现有大纲
            with open(outline_file, 'r', encoding='utf-8') as f:
                outline_data = json.load(f)
            existing_outline = Outline(**outline_data)
            
            # 检查是否已完成
            if existing_outline.is_complete and not force:
                return ToolResult(
                    tool_name="outline.extend",
                    success=True,
                    message="大纲已标记为完成，使用 force=true 强制扩展",
                    data={"is_complete": True, "chapter_count": len(existing_outline.chapters), "skipped": True}
                )
            
            # 加载前置依赖
            world, theme_conflict, characters = _load_prereqs()
            
            if theme_conflict is None:
                return ToolResult(
                    tool_name="outline.extend",
                    success=False,
                    error="缺失 theme_conflict，无法扩展大纲"
                )
            
            # 读取设置以获取 max_chapters
            settings_file = os.path.join(project_dir, "settings.json")
            max_chapters = 50
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                max_chapters = settings_data.get("max_chapters", 50)
            
            # 检查是否超出限制
            current_count = len(existing_outline.chapters)
            if current_count + additional_chapters > max_chapters:
                allowed_add = max_chapters - current_count
                if allowed_add <= 0:
                    return ToolResult(
                        tool_name="outline.extend",
                        success=False,
                        error=f"已达到最大章节数限制 ({max_chapters} 章)",
                        data={"current_count": current_count, "max_chapters": max_chapters}
                    )
                additional_chapters = allowed_add
            
            # 加载章节记忆
            chapter_memories = []
            memory_file = os.path.join(project_dir, "chapter_memory.json")
            if os.path.exists(memory_file):
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                from novelgen.models import ChapterMemoryEntry
                chapter_memories = [ChapterMemoryEntry(**m) for m in memory_data]
            
            # 构建模拟的评估结果
            from novelgen.models import StoryProgressEvaluation
            evaluation = StoryProgressEvaluation(
                evaluation_result="continue",
                current_chapter=current_count,
                remaining_chapters=max_chapters - current_count,
                main_conflict_progress=0.5,
                recommendation="继续发展剧情"
            )
            
            # 调用扩展链
            from novelgen.chains.outline_chain import extend_outline as ext_outline
            
            extended_outline = ext_outline(
                existing_outline=existing_outline,
                evaluation=evaluation,
                chapter_memories=chapter_memories,
                remaining_chapters=additional_chapters,
                verbose=False
            )
            
            # 保存扩展后的大纲
            with open(outline_file, 'w', encoding='utf-8') as f:
                json.dump(extended_outline.model_dump(), f, ensure_ascii=False, indent=2)
            
            new_count = len(extended_outline.chapters)
            added = new_count - current_count
            
            return ToolResult(
                tool_name="outline.extend",
                success=True,
                message=f"大纲扩展成功，新增 {added} 章（共 {new_count} 章）",
                data={
                    "previous_count": current_count,
                    "added_count": added,
                    "total_count": new_count,
                    "is_complete": extended_outline.is_complete,
                    "current_phase": extended_outline.current_phase
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="outline.extend",
                success=False,
                error=str(e)
            )
    
    def trim_outline(max_chapters: int) -> ToolResult:
        """裁剪大纲到指定章节数（破坏性操作）
        
        Args:
            max_chapters: 保留的最大章节数
            
        Returns:
            裁剪结果的 ToolResult
        """
        try:
            outline_file = os.path.join(project_dir, "outline.json")
            
            if not os.path.exists(outline_file):
                return ToolResult(
                    tool_name="outline.trim",
                    success=False,
                    error="大纲不存在"
                )
            
            # 加载大纲
            with open(outline_file, 'r', encoding='utf-8') as f:
                outline_data = json.load(f)
            existing_outline = Outline(**outline_data)
            
            current_count = len(existing_outline.chapters)
            
            if max_chapters >= current_count:
                return ToolResult(
                    tool_name="outline.trim",
                    success=True,
                    message=f"无需裁剪（当前 {current_count} 章，目标 {max_chapters} 章）",
                    data={"current_count": current_count, "trimmed": False}
                )
            
            # 裁剪章节
            trimmed_chapters = existing_outline.chapters[:max_chapters]
            removed_count = current_count - max_chapters
            
            # 更新大纲
            existing_outline.chapters = trimmed_chapters
            
            # 保存
            with open(outline_file, 'w', encoding='utf-8') as f:
                json.dump(existing_outline.model_dump(), f, ensure_ascii=False, indent=2)
            
            return ToolResult(
                tool_name="outline.trim",
                success=True,
                message=f"大纲已裁剪，移除 {removed_count} 章（剩余 {max_chapters} 章）",
                data={
                    "previous_count": current_count,
                    "removed_count": removed_count,
                    "current_count": max_chapters,
                    "trimmed": True
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="outline.trim",
                success=False,
                error=str(e)
            )
    
    def reindex_outline() -> ToolResult:
        """重新索引大纲章节编号（破坏性操作）
        
        将章节编号重新从 1 开始连续编号，常用于删除中间章节后的清理
        
        Returns:
            重索引结果的 ToolResult
        """
        try:
            outline_file = os.path.join(project_dir, "outline.json")
            
            if not os.path.exists(outline_file):
                return ToolResult(
                    tool_name="outline.reindex",
                    success=False,
                    error="大纲不存在"
                )
            
            # 加载大纲
            with open(outline_file, 'r', encoding='utf-8') as f:
                outline_data = json.load(f)
            existing_outline = Outline(**outline_data)
            
            # 记录旧编号
            old_numbers = [ch.chapter_number for ch in existing_outline.chapters]
            
            # 重新编号
            renumbered = []
            for i, chapter in enumerate(existing_outline.chapters, start=1):
                chapter.chapter_number = i
                renumbered.append({"old": old_numbers[i-1], "new": i})
            
            # 保存
            with open(outline_file, 'w', encoding='utf-8') as f:
                json.dump(existing_outline.model_dump(), f, ensure_ascii=False, indent=2)
            
            # 检查是否有变化
            changed = any(r["old"] != r["new"] for r in renumbered)
            
            return ToolResult(
                tool_name="outline.reindex",
                success=True,
                message=f"大纲重索引完成（共 {len(renumbered)} 章）",
                data={
                    "chapter_count": len(renumbered),
                    "renumbered": renumbered if changed else [],
                    "changed": changed
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="outline.reindex",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="outline.generate",
            category=ToolCategory.FINE_GRAINED,
            description="生成大纲（支持固定/动态章节模式）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=generate_outline
        ),
        Tool(
            name="outline.extend",
            category=ToolCategory.FINE_GRAINED,
            description="扩展现有大纲（添加新章节）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=extend_outline
        ),
        Tool(
            name="outline.trim",
            category=ToolCategory.FINE_GRAINED,
            description="裁剪大纲到指定章节数（破坏性操作）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            handler=trim_outline
        ),
        Tool(
            name="outline.reindex",
            category=ToolCategory.FINE_GRAINED,
            description="重新索引大纲章节编号（破坏性操作）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            handler=reindex_outline
        ),
    ]
    
    return tools
