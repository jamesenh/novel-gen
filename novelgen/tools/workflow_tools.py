"""
工作流工具模块
提供 run/resume/status/rollback/export 等工作流操作

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""
import os
from typing import Optional, Dict, Any

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult


def create_workflow_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建工作流工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    
    def get_status() -> ToolResult:
        """获取项目状态
        
        更新: 2025-12-16 - 返回与工作流节点名一致的 completed_steps 格式
        """
        from novelgen.runtime.orchestrator import NovelOrchestrator
        
        try:
            orchestrator = NovelOrchestrator(project_name=project_id, verbose=False)
            state = orchestrator.get_project_state()
            orchestrator.cleanup()
            
            # 构建摘要信息
            steps = state.get("steps", {})
            chapters = state.get("chapters", {})
            
            # 将步骤名映射为工作流节点名（用于目标型生成的依赖检查）
            # 例如：world -> world_creation, theme_conflict -> theme_conflict_creation
            step_to_node_map = {
                "world": "world_creation",
                "theme_conflict": "theme_conflict_creation",
                "characters": "character_creation",
                "outline": "outline_creation",
            }
            
            completed_steps = []
            for step_key, step_info in steps.items():
                if step_info.get("exists"):
                    node_name = step_to_node_map.get(step_key, step_key)
                    completed_steps.append(node_name)
            
            # 检查章节计划是否完整（所有章节都有计划）
            if chapters:
                all_have_plans = all(info.get("plan", False) for info in chapters.values())
                if all_have_plans and len(chapters) > 0:
                    completed_steps.append("chapter_planning")
            
            completed_chapters = [ch for ch, info in chapters.items() if info.get("complete")]
            in_progress_chapters = [ch for ch, info in chapters.items() if info.get("scenes") and not info.get("complete")]
            
            total_words = sum(info.get("word_count", 0) for info in chapters.values())
            
            summary = {
                "completed_steps": completed_steps,
                "total_chapters_planned": len(chapters),
                "completed_chapters": len(completed_chapters),
                "in_progress_chapters": len(in_progress_chapters),
                "total_words": total_words,
                "checkpoint_exists": state.get("checkpoint_exists", False),
                "can_resume": state.get("checkpoint_exists", False) or len(completed_chapters) > 0
            }
            
            return ToolResult(
                tool_name="workflow.status",
                success=True,
                message=f"已完成 {len(completed_chapters)} 章，共 {total_words:,} 字",
                data=summary
            )
        except Exception as e:
            return ToolResult(
                tool_name="workflow.status",
                success=False,
                error=str(e)
            )
    
    def run_workflow(
        stop_at: Optional[str] = None,
        verbose: bool = False
    ) -> ToolResult:
        """运行工作流"""
        from novelgen.runtime.orchestrator import NovelOrchestrator
        
        try:
            orchestrator = NovelOrchestrator(
                project_name=project_id,
                verbose=verbose,
                show_prompt=False
            )
            
            final_state = orchestrator.run_workflow(stop_at=stop_at)
            orchestrator.export_all_chapters()
            orchestrator.cleanup()
            
            current_step = final_state.get('current_step', '未知')
            completed_steps = final_state.get('completed_steps', [])
            
            return ToolResult(
                tool_name="workflow.run",
                success=True,
                message=f"工作流执行完成，当前步骤: {current_step}",
                data={
                    "current_step": current_step,
                    "completed_steps": completed_steps
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="workflow.run",
                success=False,
                error=str(e)
            )
    
    def resume_workflow(verbose: bool = False) -> ToolResult:
        """恢复工作流"""
        from novelgen.runtime.orchestrator import NovelOrchestrator
        
        try:
            orchestrator = NovelOrchestrator(
                project_name=project_id,
                verbose=verbose,
                show_prompt=False
            )
            
            final_state = orchestrator.resume_workflow()
            orchestrator.export_all_chapters()
            orchestrator.cleanup()
            
            if hasattr(final_state, 'current_step'):
                current_step = final_state.current_step
            elif isinstance(final_state, dict):
                current_step = final_state.get('current_step', '未知')
            else:
                current_step = '未知'
            
            return ToolResult(
                tool_name="workflow.resume",
                success=True,
                message=f"工作流恢复完成，当前步骤: {current_step}",
                data={"current_step": current_step}
            )
        except Exception as e:
            return ToolResult(
                tool_name="workflow.resume",
                success=False,
                error=str(e)
            )
    
    def rollback_to_chapter(chapter_number: int) -> ToolResult:
        """回滚到指定章节"""
        from novelgen.runtime.orchestrator import NovelOrchestrator
        
        try:
            orchestrator = NovelOrchestrator(project_name=project_id, verbose=False)
            result = orchestrator.rollback_to_chapter(chapter_number)
            orchestrator.cleanup()
            
            return ToolResult(
                tool_name="workflow.rollback",
                success=True,
                message=f"已回滚到第 {chapter_number} 章之前",
                data=result
            )
        except Exception as e:
            return ToolResult(
                tool_name="workflow.rollback",
                success=False,
                error=str(e)
            )
    
    def export_novel(output_path: Optional[str] = None) -> ToolResult:
        """导出小说"""
        from novelgen.runtime.orchestrator import NovelOrchestrator
        
        try:
            orchestrator = NovelOrchestrator(project_name=project_id, verbose=False)
            orchestrator.export_all_chapters(output_path=output_path)
            orchestrator.cleanup()
            
            default_output = os.path.join(project_dir, f"{project_id}_full.txt")
            actual_output = output_path or default_output
            
            return ToolResult(
                tool_name="workflow.export",
                success=True,
                message=f"小说已导出到: {actual_output}",
                data={"output_path": actual_output}
            )
        except Exception as e:
            return ToolResult(
                tool_name="workflow.export",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="workflow.status",
            category=ToolCategory.WORKFLOW,
            description="获取项目当前状态和进度",
            confirm_level=ConfirmLevel.NONE,
            slash_command="/status",
            handler=get_status
        ),
        Tool(
            name="workflow.run",
            category=ToolCategory.WORKFLOW,
            description="运行小说生成工作流",
            confirm_level=ConfirmLevel.NORMAL,
            slash_command="/run",
            handler=run_workflow
        ),
        Tool(
            name="workflow.resume",
            category=ToolCategory.WORKFLOW,
            description="从检查点恢复工作流",
            confirm_level=ConfirmLevel.NORMAL,
            slash_command="/resume",
            handler=resume_workflow
        ),
        Tool(
            name="workflow.rollback",
            category=ToolCategory.WORKFLOW,
            description="回滚到指定章节之前",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            slash_command="/rollback",
            handler=rollback_to_chapter
        ),
        Tool(
            name="workflow.export",
            category=ToolCategory.WORKFLOW,
            description="导出小说为文本文件",
            confirm_level=ConfirmLevel.NONE,
            slash_command="/export",
            handler=export_novel
        ),
    ]
    
    return tools
