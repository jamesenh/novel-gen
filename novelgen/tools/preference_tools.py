"""
偏好管理工具模块
提供 set/list/forget 等偏好操作（使用 Mem0 User Memory）

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""
import os
from typing import Optional, List

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult


def create_preference_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建偏好管理工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    
    # 项目隔离的用户ID
    user_id = f"author_{project_id}"
    
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
    
    def set_preference(content: str, preference_type: str = "writing_style") -> ToolResult:
        """设置偏好
        
        Args:
            content: 偏好内容（自然语言描述）
            preference_type: 偏好类型（默认 writing_style）
        """
        try:
            mem0 = _get_mem0_manager()
            if mem0 is None:
                return ToolResult(
                    tool_name="preference.set",
                    success=False,
                    error="Mem0 未启用，请设置 MEM0_ENABLED=true"
                )
            
            # 使用 Mem0 的 add_user_preference 方法添加用户偏好
            success = mem0.add_user_preference(
                preference_type=preference_type,
                content=content,
                source="manual"
            )
            
            if success:
                return ToolResult(
                    tool_name="preference.set",
                    success=True,
                    message=f"偏好已保存: {content[:50]}..."
                )
            else:
                return ToolResult(
                    tool_name="preference.set",
                    success=False,
                    error="偏好保存失败"
                )
        except Exception as e:
            return ToolResult(
                tool_name="preference.set",
                success=False,
                error=str(e)
            )
    
    def list_preferences(limit: int = 10) -> ToolResult:
        """列出偏好
        
        Args:
            limit: 返回数量限制
        """
        try:
            mem0 = _get_mem0_manager()
            if mem0 is None:
                return ToolResult(
                    tool_name="preference.list",
                    success=False,
                    error="Mem0 未启用"
                )
            
            # 使用 search_user_preferences 获取偏好
            preferences = mem0.search_user_preferences(limit=limit)
            
            return ToolResult(
                tool_name="preference.list",
                success=True,
                message=f"找到 {len(preferences)} 条偏好",
                data={"preferences": preferences}
            )
        except Exception as e:
            return ToolResult(
                tool_name="preference.list",
                success=False,
                error=str(e)
            )
    
    def forget_preference(preference_id: Optional[str] = None, keyword: Optional[str] = None) -> ToolResult:
        """删除偏好
        
        Args:
            preference_id: 偏好ID（精确删除）
            keyword: 关键词（模糊匹配删除）
        """
        try:
            mem0 = _get_mem0_manager()
            if mem0 is None:
                return ToolResult(
                    tool_name="preference.forget",
                    success=False,
                    error="Mem0 未启用"
                )
            
            if preference_id:
                # 精确删除（使用 Mem0 的 delete 方法）
                try:
                    mem0.client.delete(memory_id=preference_id)
                    return ToolResult(
                        tool_name="preference.forget",
                        success=True,
                        message=f"已删除偏好: {preference_id}"
                    )
                except Exception as e:
                    return ToolResult(
                        tool_name="preference.forget",
                        success=False,
                        error=f"删除失败: {e}"
                    )
            elif keyword:
                # 模糊匹配删除：先搜索再删除
                prefs = mem0.search_user_preferences(query=keyword, limit=100)
                deleted_count = 0
                for pref in prefs:
                    if isinstance(pref, dict) and keyword.lower() in str(pref).lower():
                        pref_id = pref.get("id")
                        if pref_id:
                            try:
                                mem0.client.delete(memory_id=pref_id)
                                deleted_count += 1
                            except Exception:
                                pass
                
                return ToolResult(
                    tool_name="preference.forget",
                    success=True,
                    message=f"已删除 {deleted_count} 条包含 '{keyword}' 的偏好"
                )
            else:
                return ToolResult(
                    tool_name="preference.forget",
                    success=False,
                    error="请指定 preference_id 或 keyword"
                )
        except Exception as e:
            return ToolResult(
                tool_name="preference.forget",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="preference.set",
            category=ToolCategory.PREFERENCE,
            description="设置写作偏好（如风格、语气、人物塑造偏好等）",
            confirm_level=ConfirmLevel.NONE,
            slash_command="/setpref",
            handler=set_preference
        ),
        Tool(
            name="preference.list",
            category=ToolCategory.PREFERENCE,
            description="列出当前项目的所有写作偏好",
            confirm_level=ConfirmLevel.NONE,
            slash_command="/prefs",
            handler=list_preferences
        ),
        Tool(
            name="preference.forget",
            category=ToolCategory.PREFERENCE,
            description="删除指定的写作偏好",
            confirm_level=ConfirmLevel.NORMAL,
            slash_command="/forget",
            handler=forget_preference
        ),
    ]
    
    return tools
