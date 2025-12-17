"""
设置工具模块
提供 settings.get / settings.update 等细粒度工具

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, Dict, Any

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult
from novelgen.models import Settings


def create_settings_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建设置工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    settings_file = os.path.join(project_dir, "settings.json")
    
    def get_settings() -> ToolResult:
        """获取当前项目设置
        
        Returns:
            包含设置信息的 ToolResult
        """
        try:
            if not os.path.exists(settings_file):
                return ToolResult(
                    tool_name="settings.get",
                    success=False,
                    error=f"settings.json 不存在: {settings_file}"
                )
            
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            # 解析为 Settings 模型以确保格式正确
            settings = Settings(**settings_data)
            
            # 返回关键配置信息
            return ToolResult(
                tool_name="settings.get",
                success=True,
                message=f"项目: {settings.project_name}",
                data={
                    "project_name": settings.project_name,
                    "author": settings.author,
                    "llm_model": settings.llm_model,
                    "temperature": settings.temperature,
                    "initial_chapters": settings.initial_chapters,
                    "max_chapters": settings.max_chapters,
                    "world_description": settings.world_description[:100] + "..." if len(settings.world_description) > 100 else settings.world_description,
                    "theme_description": settings.theme_description[:100] + "..." if settings.theme_description and len(settings.theme_description) > 100 else settings.theme_description
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="settings.get",
                success=False,
                error=str(e)
            )
    
    def update_settings(
        patch: Dict[str, Any],
        persist: bool = True
    ) -> ToolResult:
        """更新项目设置
        
        Args:
            patch: 要更新的字段（支持: initial_chapters, max_chapters, temperature, theme_description）
            persist: 是否持久化到文件（默认 True）
            
        Returns:
            更新结果的 ToolResult
        """
        try:
            if not os.path.exists(settings_file):
                return ToolResult(
                    tool_name="settings.update",
                    success=False,
                    error=f"settings.json 不存在: {settings_file}"
                )
            
            # 读取现有设置
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            # 允许更新的字段（安全白名单）
            allowed_fields = {
                "initial_chapters",
                "max_chapters",
                "temperature",
                "theme_description",
                "world_description"
            }
            
            # 验证并应用更新
            updated_fields = []
            for key, value in patch.items():
                if key not in allowed_fields:
                    return ToolResult(
                        tool_name="settings.update",
                        success=False,
                        error=f"不允许更新字段: {key}，允许的字段: {list(allowed_fields)}"
                    )
                
                old_value = settings_data.get(key)
                settings_data[key] = value
                updated_fields.append(f"{key}: {old_value} -> {value}")
            
            # 验证更新后的设置
            try:
                settings = Settings(**settings_data)
            except Exception as e:
                return ToolResult(
                    tool_name="settings.update",
                    success=False,
                    error=f"设置验证失败: {e}"
                )
            
            # 持久化
            if persist:
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
            
            return ToolResult(
                tool_name="settings.update",
                success=True,
                message=f"已更新 {len(updated_fields)} 个字段",
                data={
                    "updated_fields": updated_fields,
                    "persisted": persist,
                    "current_settings": {
                        "initial_chapters": settings.initial_chapters,
                        "max_chapters": settings.max_chapters,
                        "temperature": settings.temperature
                    }
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="settings.update",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="settings.get",
            category=ToolCategory.FINE_GRAINED,
            description="获取当前项目设置",
            confirm_level=ConfirmLevel.NONE,
            handler=get_settings
        ),
        Tool(
            name="settings.update",
            category=ToolCategory.FINE_GRAINED,
            description="更新项目设置（支持 initial_chapters, max_chapters, temperature 等）",
            confirm_level=ConfirmLevel.NORMAL,  # 需要确认
            handler=update_settings
        ),
    ]
    
    return tools
