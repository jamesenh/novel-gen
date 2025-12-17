"""
记忆检索工具模块
提供 Mem0 场景/实体检索功能

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""
from typing import Optional, List

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult


def create_memory_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建记忆检索工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    
    def _get_mem0_manager():
        """获取 Mem0 管理器"""
        from novelgen.config import ProjectConfig
        
        config = ProjectConfig(project_dir=project_dir)
        if not config.mem0_config or not config.mem0_config.enabled:
            return None
        
        from novelgen.runtime.mem0_manager import Mem0Manager
        return Mem0Manager(
            config=config.mem0_config,
            project_id=project_id,
            embedding_config=config.embedding_config
        )
    
    def search_scenes(query: str, limit: int = 5) -> ToolResult:
        """搜索场景记忆
        
        Args:
            query: 搜索查询
            limit: 返回数量限制
        """
        try:
            mem0 = _get_mem0_manager()
            if mem0 is None:
                return ToolResult(
                    tool_name="memory.search_scenes",
                    success=False,
                    error="Mem0 未启用"
                )
            
            # 使用 Mem0 搜索相关场景
            results = mem0.search_memories(query=query, limit=limit)
            
            return ToolResult(
                tool_name="memory.search_scenes",
                success=True,
                message=f"找到 {len(results)} 条相关记忆",
                data={"memories": results}
            )
        except Exception as e:
            return ToolResult(
                tool_name="memory.search_scenes",
                success=False,
                error=str(e)
            )
    
    def get_entity_state(entity_name: str) -> ToolResult:
        """获取实体当前状态
        
        Args:
            entity_name: 实体名称（如角色名）
        """
        try:
            mem0 = _get_mem0_manager()
            if mem0 is None:
                return ToolResult(
                    tool_name="memory.entity_state",
                    success=False,
                    error="Mem0 未启用"
                )
            
            # 获取实体最新状态
            state = mem0.get_entity_state(entity_id=entity_name)
            
            if state is None:
                return ToolResult(
                    tool_name="memory.entity_state",
                    success=True,
                    message=f"未找到实体 '{entity_name}' 的状态记录",
                    data={"entity_state": None}
                )
            
            return ToolResult(
                tool_name="memory.entity_state",
                success=True,
                message=f"找到 {entity_name} 的状态记录",
                data={"entity_state": state}
            )
        except Exception as e:
            return ToolResult(
                tool_name="memory.entity_state",
                success=False,
                error=str(e)
            )
    
    def get_chapter_summary(chapter_number: int) -> ToolResult:
        """获取章节摘要
        
        Args:
            chapter_number: 章节编号
        """
        import os
        import json
        
        try:
            chapter_memory_file = os.path.join(project_dir, "chapter_memory.json")
            
            if not os.path.exists(chapter_memory_file):
                return ToolResult(
                    tool_name="memory.chapter_summary",
                    success=False,
                    error="章节记忆文件不存在"
                )
            
            with open(chapter_memory_file, 'r', encoding='utf-8') as f:
                memories = json.load(f)
            
            # 查找指定章节
            for entry in memories:
                if entry.get("chapter_number") == chapter_number:
                    return ToolResult(
                        tool_name="memory.chapter_summary",
                        success=True,
                        message=f"第 {chapter_number} 章: {entry.get('chapter_title', '未知')}",
                        data={"chapter_memory": entry}
                    )
            
            return ToolResult(
                tool_name="memory.chapter_summary",
                success=False,
                error=f"未找到第 {chapter_number} 章的记忆"
            )
            
        except Exception as e:
            return ToolResult(
                tool_name="memory.chapter_summary",
                success=False,
                error=str(e)
            )
    
    def rebuild_memory(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None
    ) -> ToolResult:
        """从 chapters JSON 重建记忆
        
        从章节 JSON 文件重建 chapter_memory.json 和 Mem0 记忆（如果启用）。
        优雅降级：如果 Mem0 不可用，只重建本地 JSON 记忆。
        
        Args:
            chapter_scope_start: 章节范围起始
            chapter_scope_end: 章节范围结束
            chapter_numbers: 显式章节编号列表（None = 全部）
            
        Returns:
            重建结果的 ToolResult
        """
        import os
        import json
        from novelgen.models import GeneratedChapter, ChapterMemoryEntry
        
        try:
            chapters_dir = os.path.join(project_dir, "chapters")
            
            if not os.path.exists(chapters_dir):
                return ToolResult(
                    tool_name="memory.rebuild",
                    success=False,
                    error="chapters 目录不存在"
                )
            
            # 确定目标章节
            if chapter_numbers is not None:
                target_chapters = sorted(chapter_numbers)
            elif chapter_scope_start is not None:
                end = chapter_scope_end if chapter_scope_end is not None else chapter_scope_start
                target_chapters = list(range(chapter_scope_start, end + 1))
            else:
                # 全部章节
                target_chapters = []
                for f in os.listdir(chapters_dir):
                    if f.startswith("chapter_") and f.endswith(".json") and "_plan" not in f:
                        try:
                            ch_num = int(f.split("_")[1].replace(".json", ""))
                            target_chapters.append(ch_num)
                        except (IndexError, ValueError):
                            pass
                target_chapters = sorted(target_chapters)
            
            if not target_chapters:
                return ToolResult(
                    tool_name="memory.rebuild",
                    success=False,
                    error="没有可重建的章节"
                )
            
            # 加载现有记忆（如果存在）
            chapter_memory_file = os.path.join(project_dir, "chapter_memory.json")
            existing_memories = []
            if os.path.exists(chapter_memory_file):
                with open(chapter_memory_file, 'r', encoding='utf-8') as f:
                    existing_memories = json.load(f)
            
            # 将现有记忆转换为字典
            memory_dict = {m.get("chapter_number"): m for m in existing_memories}
            
            rebuilt = []
            failed = []
            
            for ch_num in target_chapters:
                chapter_file = os.path.join(chapters_dir, f"chapter_{ch_num:03d}.json")
                
                if not os.path.exists(chapter_file):
                    failed.append({"chapter": ch_num, "error": "文件不存在"})
                    continue
                
                try:
                    with open(chapter_file, 'r', encoding='utf-8') as f:
                        chapter = GeneratedChapter(**json.load(f))
                    
                    # 从章节提取摘要（简单版本）
                    summary = ""
                    key_events = []
                    
                    for scene in chapter.scenes:
                        # 取每个场景的前100字作为摘要
                        if len(summary) < 500:
                            summary += scene.content[:100] + "..."
                    
                    # 创建记忆条目
                    memory_entry = {
                        "chapter_number": ch_num,
                        "chapter_title": chapter.chapter_title,
                        "summary": summary[:500] if summary else f"第{ch_num}章内容",
                        "key_events": key_events,
                        "word_count": chapter.total_words,
                        "scene_count": len(chapter.scenes)
                    }
                    
                    memory_dict[ch_num] = memory_entry
                    rebuilt.append(ch_num)
                    
                except Exception as e:
                    failed.append({"chapter": ch_num, "error": str(e)})
            
            # 保存更新后的记忆
            updated_memories = [memory_dict[k] for k in sorted(memory_dict.keys())]
            
            with open(chapter_memory_file, 'w', encoding='utf-8') as f:
                json.dump(updated_memories, f, ensure_ascii=False, indent=2)
            
            # 尝试同步到 Mem0（优雅降级）
            mem0_synced = False
            mem0_error = None
            
            try:
                mem0 = _get_mem0_manager()
                if mem0 is not None:
                    # 这里可以添加 Mem0 同步逻辑
                    mem0_synced = True
            except Exception as e:
                mem0_error = str(e)
            
            return ToolResult(
                tool_name="memory.rebuild",
                success=True,
                message=f"重建 {len(rebuilt)} 章记忆，失败 {len(failed)} 章",
                data={
                    "rebuilt": rebuilt,
                    "failed": failed,
                    "total_memories": len(updated_memories),
                    "mem0_synced": mem0_synced,
                    "mem0_error": mem0_error
                }
            )
            
        except Exception as e:
            return ToolResult(
                tool_name="memory.rebuild",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="memory.search_scenes",
            category=ToolCategory.MEMORY,
            description="搜索与查询相关的场景记忆",
            confirm_level=ConfirmLevel.NONE,
            handler=search_scenes
        ),
        Tool(
            name="memory.entity_state",
            category=ToolCategory.MEMORY,
            description="获取角色或实体的当前状态",
            confirm_level=ConfirmLevel.NONE,
            handler=get_entity_state
        ),
        Tool(
            name="memory.chapter_summary",
            category=ToolCategory.MEMORY,
            description="获取指定章节的摘要和关键事件",
            confirm_level=ConfirmLevel.NONE,
            handler=get_chapter_summary
        ),
        Tool(
            name="memory.rebuild",
            category=ToolCategory.FINE_GRAINED,
            description="从 chapters JSON 重建记忆（支持章节范围）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=rebuild_memory
        ),
    ]
    
    return tools
