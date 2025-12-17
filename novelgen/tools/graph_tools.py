"""
图谱查询工具模块
提供 whois/relations/events 等图谱查询操作

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""
from typing import Optional, List

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult


def create_graph_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建图谱查询工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    
    def _get_store():
        """获取 KuzuStore"""
        from novelgen.config import ProjectConfig
        from novelgen.graph.kuzu_store import KuzuStore
        
        config = ProjectConfig(project_dir=project_dir)
        if not config.graph_enabled:
            return None
        
        store = KuzuStore(config.get_graph_dir(), read_only=True)
        if not store.is_available:
            return None
        
        if not store.connect():
            return None
        
        return store
    
    def whois(name: str) -> ToolResult:
        """查询角色信息
        
        Args:
            name: 角色名称
        """
        try:
            store = _get_store()
            if store is None:
                return ToolResult(
                    tool_name="graph.whois",
                    success=False,
                    error="图谱功能不可用"
                )
            
            try:
                char = store.get_character(name)
                
                if char is None:
                    # 尝试模糊匹配
                    all_chars = store.get_all_characters()
                    similar = [c["name"] for c in all_chars if name in c["name"]]
                    
                    return ToolResult(
                        tool_name="graph.whois",
                        success=False,
                        error=f"未找到角色: {name}",
                        data={"similar_names": similar}
                    )
                
                return ToolResult(
                    tool_name="graph.whois",
                    success=True,
                    message=f"找到角色: {char['name']} ({char['role']})",
                    data={"character": char}
                )
            finally:
                store.close()
                
        except Exception as e:
            return ToolResult(
                tool_name="graph.whois",
                success=False,
                error=str(e)
            )
    
    def get_relations(name: str, with_name: Optional[str] = None) -> ToolResult:
        """查询角色关系
        
        Args:
            name: 角色名称
            with_name: 可选，查询与指定角色的关系
        """
        try:
            store = _get_store()
            if store is None:
                return ToolResult(
                    tool_name="graph.relations",
                    success=False,
                    error="图谱功能不可用"
                )
            
            try:
                relations = store.get_relations(name, with_name)
                
                if not relations:
                    if with_name:
                        return ToolResult(
                            tool_name="graph.relations",
                            success=True,
                            message=f"未找到 {name} 与 {with_name} 之间的直接关系",
                            data={"relations": []}
                        )
                    else:
                        return ToolResult(
                            tool_name="graph.relations",
                            success=True,
                            message=f"未找到 {name} 的任何关系",
                            data={"relations": []}
                        )
                
                return ToolResult(
                    tool_name="graph.relations",
                    success=True,
                    message=f"找到 {len(relations)} 条关系",
                    data={"relations": relations}
                )
            finally:
                store.close()
                
        except Exception as e:
            return ToolResult(
                tool_name="graph.relations",
                success=False,
                error=str(e)
            )
    
    def get_events(
        character_name: Optional[str] = None,
        chapter_number: Optional[int] = None
    ) -> ToolResult:
        """查询事件
        
        Args:
            character_name: 可选，按角色过滤
            chapter_number: 可选，按章节过滤
        """
        try:
            store = _get_store()
            if store is None:
                return ToolResult(
                    tool_name="graph.events",
                    success=False,
                    error="图谱功能不可用"
                )
            
            try:
                events = store.get_events(
                    character_name=character_name,
                    chapter_number=chapter_number
                )
                
                if not events:
                    return ToolResult(
                        tool_name="graph.events",
                        success=True,
                        message="未找到符合条件的事件",
                        data={"events": []}
                    )
                
                return ToolResult(
                    tool_name="graph.events",
                    success=True,
                    message=f"找到 {len(events)} 条事件",
                    data={"events": events}
                )
            finally:
                store.close()
                
        except Exception as e:
            return ToolResult(
                tool_name="graph.events",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="graph.whois",
            category=ToolCategory.GRAPH,
            description="查询角色详细信息（背景、性格、能力等）",
            confirm_level=ConfirmLevel.NONE,
            slash_command="/whois",
            handler=whois
        ),
        Tool(
            name="graph.relations",
            category=ToolCategory.GRAPH,
            description="查询角色之间的关系",
            confirm_level=ConfirmLevel.NONE,
            slash_command="/relations",
            handler=get_relations
        ),
        Tool(
            name="graph.events",
            category=ToolCategory.GRAPH,
            description="查询角色参与的事件或章节事件",
            confirm_level=ConfirmLevel.NONE,
            slash_command="/events",
            handler=get_events
        ),
    ]
    
    return tools
