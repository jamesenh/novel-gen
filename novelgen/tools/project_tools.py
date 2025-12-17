"""
项目工具模块
提供 project.status / project.validate_prereqs / project.list_artifacts 等细粒度工具

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, List, Dict, Any

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult


def create_project_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建项目工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    
    def get_status(detail: bool = False) -> ToolResult:
        """获取项目状态
        
        Args:
            detail: 是否返回详细信息
            
        Returns:
            包含项目状态的 ToolResult
        """
        try:
            # 检查各阶段文件是否存在
            steps = {
                "world": {
                    "exists": os.path.exists(os.path.join(project_dir, "world.json")),
                    "file": "world.json",
                    "node": "world_creation"
                },
                "theme_conflict": {
                    "exists": os.path.exists(os.path.join(project_dir, "theme_conflict.json")),
                    "file": "theme_conflict.json",
                    "node": "theme_conflict_creation"
                },
                "characters": {
                    "exists": os.path.exists(os.path.join(project_dir, "characters.json")),
                    "file": "characters.json",
                    "node": "character_creation"
                },
                "outline": {
                    "exists": os.path.exists(os.path.join(project_dir, "outline.json")),
                    "file": "outline.json",
                    "node": "outline_creation"
                }
            }
            
            # 从 outline.json 获取章节数量
            outline_file = os.path.join(project_dir, "outline.json")
            total_chapters = 0
            if os.path.exists(outline_file):
                with open(outline_file, 'r', encoding='utf-8') as f:
                    outline_data = json.load(f)
                    total_chapters = len(outline_data.get("chapters", []))
            
            # 扫描章节目录
            chapters_dir = os.path.join(project_dir, "chapters")
            chapters = {}
            plans_count = 0
            completed_count = 0
            total_words = 0
            
            if os.path.exists(chapters_dir):
                for filename in os.listdir(chapters_dir):
                    # 章节计划
                    if filename.endswith("_plan.json"):
                        try:
                            ch_num = int(filename.split("_")[1])
                            plans_count += 1
                            if ch_num not in chapters:
                                chapters[ch_num] = {"plan": True, "complete": False, "word_count": 0}
                            else:
                                chapters[ch_num]["plan"] = True
                        except (IndexError, ValueError):
                            pass
                    # 完整章节
                    elif filename.startswith("chapter_") and filename.endswith(".json") and "_plan" not in filename:
                        try:
                            ch_num = int(filename.split("_")[1].replace(".json", ""))
                            chapter_file = os.path.join(chapters_dir, filename)
                            with open(chapter_file, 'r', encoding='utf-8') as f:
                                chapter_data = json.load(f)
                                word_count = chapter_data.get("total_words", 0)
                            
                            completed_count += 1
                            total_words += word_count
                            
                            if ch_num not in chapters:
                                chapters[ch_num] = {"plan": False, "complete": True, "word_count": word_count}
                            else:
                                chapters[ch_num]["complete"] = True
                                chapters[ch_num]["word_count"] = word_count
                        except (IndexError, ValueError, json.JSONDecodeError):
                            pass
            
            # 构建 completed_steps 列表（兼容现有格式）
            completed_steps = []
            for step_key, step_info in steps.items():
                if step_info["exists"]:
                    completed_steps.append(step_info["node"])
            
            # 检查章节计划是否完整
            if plans_count > 0 and plans_count >= total_chapters:
                completed_steps.append("chapter_planning")
            
            summary = {
                "project_id": project_id,
                "steps": steps,
                "completed_steps": completed_steps,
                "total_chapters_planned": total_chapters,
                "plans_count": plans_count,
                "completed_chapters": completed_count,
                "total_words": total_words,
                "chapters": chapters if detail else {}
            }
            
            return ToolResult(
                tool_name="project.status",
                success=True,
                message=f"已完成 {completed_count} 章，共 {total_words:,} 字",
                data=summary
            )
        except Exception as e:
            return ToolResult(
                tool_name="project.status",
                success=False,
                error=str(e)
            )
    
    def validate_prereqs(target: str) -> ToolResult:
        """验证目标生成的前置条件
        
        Args:
            target: 目标类型 (world/theme_conflict/characters/outline/chapter_plan/chapter_text)
            
        Returns:
            包含缺失前置的 ToolResult
        """
        try:
            # 定义各目标的前置依赖
            prereqs = {
                "world": [],
                "theme_conflict": ["world"],
                "characters": ["world", "theme_conflict"],
                "outline": ["world", "theme_conflict", "characters"],
                "chapter_plan": ["world", "theme_conflict", "characters", "outline"],
                "chapter_text": ["world", "theme_conflict", "characters", "outline", "chapter_plan"]
            }
            
            # 文件映射
            file_map = {
                "world": "world.json",
                "theme_conflict": "theme_conflict.json",
                "characters": "characters.json",
                "outline": "outline.json",
                "chapter_plan": None  # 需要特殊处理
            }
            
            if target not in prereqs:
                return ToolResult(
                    tool_name="project.validate_prereqs",
                    success=False,
                    error=f"无效的目标: {target}，有效值: {list(prereqs.keys())}"
                )
            
            missing = []
            for dep in prereqs[target]:
                if dep == "chapter_plan":
                    # 检查是否有任何章节计划
                    chapters_dir = os.path.join(project_dir, "chapters")
                    if not os.path.exists(chapters_dir):
                        missing.append(dep)
                    else:
                        has_plan = any(f.endswith("_plan.json") for f in os.listdir(chapters_dir))
                        if not has_plan:
                            missing.append(dep)
                else:
                    filepath = os.path.join(project_dir, file_map[dep])
                    if not os.path.exists(filepath):
                        missing.append(dep)
            
            if missing:
                return ToolResult(
                    tool_name="project.validate_prereqs",
                    success=True,
                    message=f"缺失前置: {', '.join(missing)}",
                    data={"target": target, "missing_deps": missing, "satisfied": False}
                )
            else:
                return ToolResult(
                    tool_name="project.validate_prereqs",
                    success=True,
                    message="所有前置条件已满足",
                    data={"target": target, "missing_deps": [], "satisfied": True}
                )
        except Exception as e:
            return ToolResult(
                tool_name="project.validate_prereqs",
                success=False,
                error=str(e)
            )
    
    def list_artifacts(
        kind: str = "all",
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None
    ) -> ToolResult:
        """列出项目产物
        
        Args:
            kind: 产物类型 (all/plan/text/outline)
            chapter_scope_start: 章节范围起始（可选）
            chapter_scope_end: 章节范围结束（可选）
            
        Returns:
            包含产物列表的 ToolResult
        """
        try:
            artifacts = {
                "world": None,
                "theme_conflict": None,
                "characters": None,
                "outline": None,
                "plans": [],
                "chapters": []
            }
            
            # 检查基础产物
            for key in ["world", "theme_conflict", "characters", "outline"]:
                filepath = os.path.join(project_dir, f"{key}.json")
                if os.path.exists(filepath):
                    artifacts[key] = filepath
            
            # 扫描章节产物
            chapters_dir = os.path.join(project_dir, "chapters")
            if os.path.exists(chapters_dir):
                for filename in os.listdir(chapters_dir):
                    filepath = os.path.join(chapters_dir, filename)
                    
                    # 解析章节号
                    try:
                        if filename.endswith("_plan.json"):
                            ch_num = int(filename.split("_")[1])
                            file_type = "plan"
                        elif filename.startswith("chapter_") and filename.endswith(".json"):
                            ch_num = int(filename.split("_")[1].replace(".json", ""))
                            file_type = "text"
                        else:
                            continue
                        
                        # 过滤章节范围
                        if chapter_scope_start is not None and ch_num < chapter_scope_start:
                            continue
                        if chapter_scope_end is not None and ch_num > chapter_scope_end:
                            continue
                        
                        # 过滤产物类型
                        if kind == "plan" and file_type != "plan":
                            continue
                        if kind == "text" and file_type != "text":
                            continue
                        
                        if file_type == "plan":
                            artifacts["plans"].append({"chapter": ch_num, "file": filepath})
                        else:
                            artifacts["chapters"].append({"chapter": ch_num, "file": filepath})
                    except (IndexError, ValueError):
                        continue
            
            # 排序
            artifacts["plans"].sort(key=lambda x: x["chapter"])
            artifacts["chapters"].sort(key=lambda x: x["chapter"])
            
            # 构建消息
            plan_nums = [p["chapter"] for p in artifacts["plans"]]
            chapter_nums = [c["chapter"] for c in artifacts["chapters"]]
            
            return ToolResult(
                tool_name="project.list_artifacts",
                success=True,
                message=f"计划: {len(plan_nums)} 个, 章节: {len(chapter_nums)} 个",
                data={
                    "kind": kind,
                    "scope": {"start": chapter_scope_start, "end": chapter_scope_end},
                    "artifacts": artifacts,
                    "plan_chapters": plan_nums,
                    "text_chapters": chapter_nums
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="project.list_artifacts",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="project.status",
            category=ToolCategory.FINE_GRAINED,
            description="获取项目当前状态和进度（细粒度版本）",
            confirm_level=ConfirmLevel.NONE,
            handler=get_status
        ),
        Tool(
            name="project.validate_prereqs",
            category=ToolCategory.FINE_GRAINED,
            description="验证目标生成的前置条件是否满足",
            confirm_level=ConfirmLevel.NONE,
            handler=validate_prereqs
        ),
        Tool(
            name="project.list_artifacts",
            category=ToolCategory.FINE_GRAINED,
            description="列出项目产物（按类型和章节范围过滤）",
            confirm_level=ConfirmLevel.NONE,
            handler=list_artifacts
        ),
    ]
    
    return tools
