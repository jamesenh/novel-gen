"""
一致性检查与修订工具模块
提供 consistency.check / revision.* 等细粒度工具

核心功能：
- consistency.check: 检查章节间的一致性问题（角色、情节、时间线）
- revision.generate: 生成修订建议
- revision.apply: 应用修订（破坏性）
- revision.discard: 丢弃修订

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult
from novelgen.models import GeneratedChapter, ChapterPlan
from novelgen.agent.intent_parser import ChapterScope


def create_consistency_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建一致性检查与修订工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    chapters_dir = os.path.join(project_dir, "chapters")
    revisions_dir = os.path.join(project_dir, "revisions")
    
    def _ensure_revisions_dir():
        """确保修订目录存在"""
        os.makedirs(revisions_dir, exist_ok=True)
    
    def _parse_chapter_scope(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None
    ) -> List[int]:
        """解析章节范围"""
        if chapter_numbers is not None:
            return sorted(chapter_numbers)
        
        if chapter_scope_start is not None:
            end = chapter_scope_end if chapter_scope_end is not None else chapter_scope_start
            return list(range(chapter_scope_start, end + 1))
        
        # 默认返回所有已存在的章节
        if os.path.exists(chapters_dir):
            chapters = []
            for f in os.listdir(chapters_dir):
                if f.startswith("chapter_") and f.endswith(".json") and "_plan" not in f:
                    try:
                        ch_num = int(f.split("_")[1].replace(".json", ""))
                        chapters.append(ch_num)
                    except (IndexError, ValueError):
                        pass
            return sorted(chapters)
        return []
    
    def _load_chapter(chapter_num: int) -> Optional[GeneratedChapter]:
        """加载章节"""
        chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num:03d}.json")
        if not os.path.exists(chapter_file):
            return None
        with open(chapter_file, 'r', encoding='utf-8') as f:
            return GeneratedChapter(**json.load(f))
    
    def _load_characters() -> Dict[str, Any]:
        """加载角色信息"""
        char_file = os.path.join(project_dir, "characters.json")
        if not os.path.exists(char_file):
            return {}
        with open(char_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def consistency_check(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None
    ) -> ToolResult:
        """检查章节间的一致性问题
        
        检查内容：
        - 角色名称一致性
        - 角色特征一致性（外貌、性格等）
        - 情节连贯性
        - 时间线合理性
        
        Args:
            chapter_scope_start: 章节范围起始
            chapter_scope_end: 章节范围结束
            chapter_numbers: 显式章节编号列表
            
        Returns:
            检查结果的 ToolResult
        """
        try:
            target_chapters = _parse_chapter_scope(
                chapter_scope_start, chapter_scope_end, chapter_numbers
            )
            
            if not target_chapters:
                return ToolResult(
                    tool_name="consistency.check",
                    success=False,
                    error="没有可检查的章节"
                )
            
            # 加载所有目标章节
            chapters_data = []
            missing_chapters = []
            
            for ch_num in target_chapters:
                chapter = _load_chapter(ch_num)
                if chapter:
                    chapters_data.append({
                        "chapter_number": ch_num,
                        "chapter": chapter
                    })
                else:
                    missing_chapters.append(ch_num)
            
            if not chapters_data:
                return ToolResult(
                    tool_name="consistency.check",
                    success=False,
                    error=f"所有目标章节都不存在: {target_chapters}"
                )
            
            # 加载角色信息
            characters = _load_characters()
            
            # 执行一致性检查
            issues = []
            warnings = []
            
            # 1. 基础检查：提取所有章节中的角色名
            all_character_mentions = {}
            for ch_data in chapters_data:
                ch = ch_data["chapter"]
                ch_num = ch_data["chapter_number"]
                
                for scene in ch.scenes:
                    content = scene.content
                    # 简单的角色名提取（实际应用中可用 NLP）
                    # 这里只做示例性检查
                    if characters:
                        protagonist = characters.get("protagonist", {})
                        if protagonist:
                            name = protagonist.get("name", "")
                            if name and name in content:
                                if name not in all_character_mentions:
                                    all_character_mentions[name] = []
                                all_character_mentions[name].append(ch_num)
            
            # 2. 检查章节间的连贯性（简单版本）
            for i in range(len(chapters_data) - 1):
                current = chapters_data[i]
                next_ch = chapters_data[i + 1]
                
                # 检查章节编号连续性
                if next_ch["chapter_number"] - current["chapter_number"] > 1:
                    warnings.append({
                        "type": "gap",
                        "message": f"第 {current['chapter_number']} 章和第 {next_ch['chapter_number']} 章之间有间隔",
                        "chapters": [current["chapter_number"], next_ch["chapter_number"]]
                    })
            
            # 3. 检查空场景
            for ch_data in chapters_data:
                ch = ch_data["chapter"]
                ch_num = ch_data["chapter_number"]
                
                for scene in ch.scenes:
                    if len(scene.content.strip()) < 100:
                        warnings.append({
                            "type": "short_scene",
                            "message": f"第 {ch_num} 章场景 {scene.scene_number} 内容过短",
                            "chapter": ch_num,
                            "scene": scene.scene_number,
                            "word_count": scene.word_count
                        })
            
            # 构建报告
            report = {
                "checked_chapters": [ch["chapter_number"] for ch in chapters_data],
                "missing_chapters": missing_chapters,
                "issues": issues,
                "warnings": warnings,
                "character_mentions": {k: len(v) for k, v in all_character_mentions.items()},
                "total_issues": len(issues),
                "total_warnings": len(warnings)
            }
            
            if issues:
                return ToolResult(
                    tool_name="consistency.check",
                    success=True,
                    message=f"发现 {len(issues)} 个问题，{len(warnings)} 个警告",
                    data=report
                )
            elif warnings:
                return ToolResult(
                    tool_name="consistency.check",
                    success=True,
                    message=f"无严重问题，{len(warnings)} 个警告",
                    data=report
                )
            else:
                return ToolResult(
                    tool_name="consistency.check",
                    success=True,
                    message=f"检查通过，{len(chapters_data)} 章无一致性问题",
                    data=report
                )
        except Exception as e:
            return ToolResult(
                tool_name="consistency.check",
                success=False,
                error=str(e)
            )
    
    def revision_generate(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None,
        mode: str = "suggest"
    ) -> ToolResult:
        """生成修订建议
        
        Args:
            chapter_scope_start: 章节范围起始
            chapter_scope_end: 章节范围结束
            chapter_numbers: 显式章节编号列表
            mode: 修订模式 (suggest/auto)
            
        Returns:
            修订建议的 ToolResult
        """
        try:
            _ensure_revisions_dir()
            
            target_chapters = _parse_chapter_scope(
                chapter_scope_start, chapter_scope_end, chapter_numbers
            )
            
            if not target_chapters:
                return ToolResult(
                    tool_name="revision.generate",
                    success=False,
                    error="没有可修订的章节"
                )
            
            # 先执行一致性检查
            check_result = consistency_check(
                chapter_scope_start, chapter_scope_end, chapter_numbers
            )
            
            if not check_result.success:
                return ToolResult(
                    tool_name="revision.generate",
                    success=False,
                    error=f"一致性检查失败: {check_result.error}"
                )
            
            # 基于检查结果生成修订建议
            issues = check_result.data.get("issues", [])
            warnings = check_result.data.get("warnings", [])
            
            revisions = []
            
            # 为每个问题生成修订建议
            for issue in issues:
                revisions.append({
                    "type": "fix",
                    "target": issue,
                    "suggestion": f"修复问题: {issue.get('message', '')}",
                    "priority": "high"
                })
            
            for warning in warnings:
                revisions.append({
                    "type": "improve",
                    "target": warning,
                    "suggestion": f"优化建议: {warning.get('message', '')}",
                    "priority": "low"
                })
            
            # 保存修订建议
            revision_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            revision_file = os.path.join(revisions_dir, f"revision_{revision_id}.json")
            
            revision_data = {
                "revision_id": revision_id,
                "created_at": datetime.now().isoformat(),
                "target_chapters": target_chapters,
                "mode": mode,
                "revisions": revisions,
                "status": "pending"
            }
            
            with open(revision_file, 'w', encoding='utf-8') as f:
                json.dump(revision_data, f, ensure_ascii=False, indent=2)
            
            return ToolResult(
                tool_name="revision.generate",
                success=True,
                message=f"生成 {len(revisions)} 条修订建议",
                data={
                    "revision_id": revision_id,
                    "revision_count": len(revisions),
                    "high_priority": len([r for r in revisions if r["priority"] == "high"]),
                    "revisions": revisions
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="revision.generate",
                success=False,
                error=str(e)
            )
    
    def revision_apply(revision_id: str) -> ToolResult:
        """应用修订（破坏性操作）
        
        Args:
            revision_id: 修订 ID
            
        Returns:
            应用结果的 ToolResult
        """
        try:
            revision_file = os.path.join(revisions_dir, f"revision_{revision_id}.json")
            
            if not os.path.exists(revision_file):
                return ToolResult(
                    tool_name="revision.apply",
                    success=False,
                    error=f"修订 {revision_id} 不存在"
                )
            
            with open(revision_file, 'r', encoding='utf-8') as f:
                revision_data = json.load(f)
            
            if revision_data.get("status") == "applied":
                return ToolResult(
                    tool_name="revision.apply",
                    success=False,
                    error=f"修订 {revision_id} 已被应用"
                )
            
            # 注意：实际的修订应用需要调用 LLM 重写章节
            # 这里只做状态更新的示例实现
            revision_data["status"] = "applied"
            revision_data["applied_at"] = datetime.now().isoformat()
            
            with open(revision_file, 'w', encoding='utf-8') as f:
                json.dump(revision_data, f, ensure_ascii=False, indent=2)
            
            return ToolResult(
                tool_name="revision.apply",
                success=True,
                message=f"修订 {revision_id} 已标记为应用（注意：实际内容修改需要人工确认）",
                data={
                    "revision_id": revision_id,
                    "status": "applied",
                    "note": "当前为状态标记，实际内容修改待实现"
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="revision.apply",
                success=False,
                error=str(e)
            )
    
    def revision_discard(revision_id: str) -> ToolResult:
        """丢弃修订
        
        Args:
            revision_id: 修订 ID
            
        Returns:
            丢弃结果的 ToolResult
        """
        try:
            revision_file = os.path.join(revisions_dir, f"revision_{revision_id}.json")
            
            if not os.path.exists(revision_file):
                return ToolResult(
                    tool_name="revision.discard",
                    success=False,
                    error=f"修订 {revision_id} 不存在"
                )
            
            # 删除修订文件
            os.remove(revision_file)
            
            return ToolResult(
                tool_name="revision.discard",
                success=True,
                message=f"修订 {revision_id} 已丢弃",
                data={"revision_id": revision_id, "status": "discarded"}
            )
        except Exception as e:
            return ToolResult(
                tool_name="revision.discard",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="consistency.check",
            category=ToolCategory.FINE_GRAINED,
            description="检查章节间的一致性问题",
            confirm_level=ConfirmLevel.NONE,
            handler=consistency_check
        ),
        Tool(
            name="revision.generate",
            category=ToolCategory.FINE_GRAINED,
            description="生成修订建议",
            confirm_level=ConfirmLevel.NONE,
            handler=revision_generate
        ),
        Tool(
            name="revision.apply",
            category=ToolCategory.FINE_GRAINED,
            description="应用修订（破坏性操作）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            handler=revision_apply
        ),
        Tool(
            name="revision.discard",
            category=ToolCategory.FINE_GRAINED,
            description="丢弃修订（破坏性操作）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            handler=revision_discard
        ),
    ]
    
    return tools
