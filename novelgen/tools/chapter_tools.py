"""
章节工具模块
提供 chapter.plan.generate / chapter.text.generate 等细粒度工具

核心特性：
- 支持 ChapterScope 精确范围执行
- 支持 missing_only 模式（只生成缺失的）
- 支持 force 模式（强制覆盖）
- 章节正文默认 sequential=true，阻止跳章生成

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult
from novelgen.models import (
    WorldSetting, ThemeConflict, CharactersConfig, Outline,
    ChapterPlan, ChapterSummary, GeneratedChapter, GeneratedScene,
    ChapterMemoryEntry, SceneMemoryContext
)
from novelgen.agent.intent_parser import ChapterScope
from novelgen.runtime.gate import (
    check_pending_revision_gate_for_range,
    PendingRevisionGateError
)


def create_chapter_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建章节工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    chapters_dir = os.path.join(project_dir, "chapters")
    
    def _ensure_chapters_dir():
        """确保 chapters 目录存在"""
        os.makedirs(chapters_dir, exist_ok=True)
    
    def _load_outline() -> Optional[Outline]:
        """加载大纲"""
        outline_file = os.path.join(project_dir, "outline.json")
        if not os.path.exists(outline_file):
            return None
        with open(outline_file, 'r', encoding='utf-8') as f:
            return Outline(**json.load(f))
    
    def _load_world() -> Optional[WorldSetting]:
        """加载世界观"""
        world_file = os.path.join(project_dir, "world.json")
        if not os.path.exists(world_file):
            return None
        with open(world_file, 'r', encoding='utf-8') as f:
            return WorldSetting(**json.load(f))
    
    def _load_characters() -> Optional[CharactersConfig]:
        """加载角色"""
        char_file = os.path.join(project_dir, "characters.json")
        if not os.path.exists(char_file):
            return None
        with open(char_file, 'r', encoding='utf-8') as f:
            return CharactersConfig(**json.load(f))
    
    def _get_chapter_plan_path(chapter_num: int) -> str:
        """获取章节计划文件路径"""
        return os.path.join(chapters_dir, f"chapter_{chapter_num:03d}_plan.json")
    
    def _get_chapter_text_path(chapter_num: int) -> str:
        """获取章节正文文件路径"""
        return os.path.join(chapters_dir, f"chapter_{chapter_num:03d}.json")
    
    def _plan_exists(chapter_num: int) -> bool:
        """检查章节计划是否存在"""
        return os.path.exists(_get_chapter_plan_path(chapter_num))
    
    def _text_exists(chapter_num: int) -> bool:
        """检查章节正文是否存在"""
        return os.path.exists(_get_chapter_text_path(chapter_num))
    
    def _parse_chapter_scope(
        chapter_scope: Optional[ChapterScope] = None,
        chapter_numbers: Optional[List[int]] = None,
        outline: Optional[Outline] = None
    ) -> List[int]:
        """解析章节范围为章节编号列表
        
        优先级：chapter_numbers > chapter_scope > 全部（从 outline）
        
        Args:
            chapter_scope: 章节范围对象
            chapter_numbers: 显式章节编号列表
            outline: 大纲（用于获取全部章节）
            
        Returns:
            章节编号列表
        """
        if chapter_numbers is not None:
            return sorted(chapter_numbers)
        
        if chapter_scope is not None:
            return list(range(chapter_scope.start, chapter_scope.end + 1))
        
        # 默认返回大纲中的所有章节
        if outline is not None:
            return [ch.chapter_number for ch in outline.chapters]
        
        return []
    
    def generate_chapter_plan(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None,
        force: bool = False,
        missing_only: bool = True
    ) -> ToolResult:
        """生成章节计划
        
        Args:
            chapter_scope_start: 章节范围起始（与 chapter_scope_end 配合使用）
            chapter_scope_end: 章节范围结束
            chapter_numbers: 显式章节编号列表（优先级高于 scope）
            force: 是否强制覆盖已存在的计划
            missing_only: 是否只生成缺失的计划（默认 True）
            
        Returns:
            生成结果的 ToolResult
        """
        try:
            _ensure_chapters_dir()
            
            # 加载前置依赖
            outline = _load_outline()
            if outline is None:
                return ToolResult(
                    tool_name="chapter.plan.generate",
                    success=False,
                    error="大纲不存在，请先生成大纲",
                    data={"missing_deps": ["outline"]}
                )
            
            world = _load_world()
            characters = _load_characters()
            
            if world is None or characters is None:
                missing = []
                if world is None:
                    missing.append("world")
                if characters is None:
                    missing.append("characters")
                return ToolResult(
                    tool_name="chapter.plan.generate",
                    success=False,
                    error=f"缺失前置依赖: {', '.join(missing)}",
                    data={"missing_deps": missing}
                )
            
            # 解析章节范围
            chapter_scope = None
            if chapter_scope_start is not None and chapter_scope_end is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_end)
            elif chapter_scope_start is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_start)
            
            target_chapters = _parse_chapter_scope(
                chapter_scope=chapter_scope,
                chapter_numbers=chapter_numbers,
                outline=outline
            )
            
            if not target_chapters:
                return ToolResult(
                    tool_name="chapter.plan.generate",
                    success=False,
                    error="未指定有效的章节范围"
                )
            
            # 验证章节范围在大纲内
            outline_chapters = {ch.chapter_number for ch in outline.chapters}
            invalid_chapters = [ch for ch in target_chapters if ch not in outline_chapters]
            if invalid_chapters:
                return ToolResult(
                    tool_name="chapter.plan.generate",
                    success=False,
                    error=f"章节 {invalid_chapters} 不在大纲中",
                    data={"invalid_chapters": invalid_chapters, "outline_chapters": sorted(outline_chapters)}
                )
            
            # 过滤已存在的（如果 missing_only=True 且 force=False）
            chapters_to_generate = []
            skipped = []
            
            for ch_num in target_chapters:
                if _plan_exists(ch_num) and not force:
                    if missing_only:
                        skipped.append(ch_num)
                        continue
                chapters_to_generate.append(ch_num)
            
            if not chapters_to_generate:
                return ToolResult(
                    tool_name="chapter.plan.generate",
                    success=True,
                    message=f"所有章节计划已存在（跳过 {len(skipped)} 章）",
                    data={"skipped": skipped, "generated": [], "skipped_reason": "already_exists"}
                )
            
            # 生成章节计划
            from novelgen.chains.chapters_plan_chain import generate_chapter_plan as gen_plan
            
            generated = []
            failed = []
            
            for ch_num in chapters_to_generate:
                # 获取章节摘要
                chapter_summary = None
                for ch in outline.chapters:
                    if ch.chapter_number == ch_num:
                        chapter_summary = ch
                        break
                
                if chapter_summary is None:
                    failed.append({"chapter": ch_num, "error": "章节摘要不存在"})
                    continue
                
                try:
                    plan = gen_plan(
                        chapter_summary=chapter_summary,
                        world_setting=world,
                        characters=characters,
                        chapter_memory="",
                        chapter_dependencies="",
                        verbose=False
                    )
                    
                    # 保存计划
                    plan_path = _get_chapter_plan_path(ch_num)
                    with open(plan_path, 'w', encoding='utf-8') as f:
                        json.dump(plan.model_dump(), f, ensure_ascii=False, indent=2)
                    
                    generated.append(ch_num)
                except Exception as e:
                    failed.append({"chapter": ch_num, "error": str(e)})
            
            success_msg = f"生成 {len(generated)} 章计划"
            if skipped:
                success_msg += f"，跳过 {len(skipped)} 章"
            if failed:
                success_msg += f"，失败 {len(failed)} 章"
            
            return ToolResult(
                tool_name="chapter.plan.generate",
                success=len(failed) == 0,
                message=success_msg,
                data={
                    "generated": generated,
                    "skipped": skipped,
                    "failed": failed
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="chapter.plan.generate",
                success=False,
                error=str(e)
            )
    
    def generate_chapter_text(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None,
        force: bool = False,
        missing_only: bool = True,
        sequential: bool = True
    ) -> ToolResult:
        """生成章节正文
        
        Args:
            chapter_scope_start: 章节范围起始（与 chapter_scope_end 配合使用）
            chapter_scope_end: 章节范围结束
            chapter_numbers: 显式章节编号列表（优先级高于 scope）
            force: 是否强制覆盖已存在的正文
            missing_only: 是否只生成缺失的正文（默认 True）
            sequential: 是否强制顺序约束（默认 True，阻止跳章生成）
            
        Returns:
            生成结果的 ToolResult
        """
        try:
            _ensure_chapters_dir()
            
            # 加载前置依赖
            outline = _load_outline()
            if outline is None:
                return ToolResult(
                    tool_name="chapter.text.generate",
                    success=False,
                    error="大纲不存在，请先生成大纲",
                    data={"missing_deps": ["outline"]}
                )
            
            world = _load_world()
            characters = _load_characters()
            
            if world is None or characters is None:
                missing = []
                if world is None:
                    missing.append("world")
                if characters is None:
                    missing.append("characters")
                return ToolResult(
                    tool_name="chapter.text.generate",
                    success=False,
                    error=f"缺失前置依赖: {', '.join(missing)}",
                    data={"missing_deps": missing}
                )
            
            # 解析章节范围
            chapter_scope = None
            if chapter_scope_start is not None and chapter_scope_end is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_end)
            elif chapter_scope_start is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_start)
            
            target_chapters = _parse_chapter_scope(
                chapter_scope=chapter_scope,
                chapter_numbers=chapter_numbers,
                outline=outline
            )
            
            if not target_chapters:
                return ToolResult(
                    tool_name="chapter.text.generate",
                    success=False,
                    error="未指定有效的章节范围"
                )
            
            # 验证章节计划存在
            missing_plans = [ch for ch in target_chapters if not _plan_exists(ch)]
            if missing_plans:
                return ToolResult(
                    tool_name="chapter.text.generate",
                    success=False,
                    error=f"章节 {missing_plans} 缺少计划，请先生成章节计划",
                    data={"missing_plans": missing_plans}
                )
            
            # Pending revision 闸门检查
            # 开发者: jamesenh, 开发时间: 2025-12-16
            try:
                check_pending_revision_gate_for_range(
                    project_dir=project_dir,
                    start_chapter=min(target_chapters),
                    end_chapter=max(target_chapters)
                )
            except PendingRevisionGateError as gate_error:
                return ToolResult(
                    tool_name="chapter.text.generate",
                    success=False,
                    error=str(gate_error),
                    data=gate_error.to_dict()
                )
            
            # 顺序约束检查：检查请求范围之前的章节是否都已完成
            if sequential:
                min_target = min(target_chapters)
                if min_target > 1:
                    blocked_by = []
                    for ch_num in range(1, min_target):
                        if not _text_exists(ch_num):
                            blocked_by.append(ch_num)
                    
                    if blocked_by:
                        return ToolResult(
                            tool_name="chapter.text.generate",
                            success=False,
                            error=f"顺序约束：第 {blocked_by} 章正文缺失，无法跳过生成",
                            data={
                                "blocked_by_missing": blocked_by,
                                "sequential": True,
                                "suggestion": f"请先生成第 1-{blocked_by[-1]} 章正文，或设置 sequential=false（不推荐）"
                            }
                        )
            
            # 过滤已存在的（如果 missing_only=True 且 force=False）
            chapters_to_generate = []
            skipped = []
            
            for ch_num in target_chapters:
                if _text_exists(ch_num) and not force:
                    if missing_only:
                        skipped.append(ch_num)
                        continue
                chapters_to_generate.append(ch_num)
            
            if not chapters_to_generate:
                return ToolResult(
                    tool_name="chapter.text.generate",
                    success=True,
                    message=f"所有章节正文已存在（跳过 {len(skipped)} 章）",
                    data={"skipped": skipped, "generated": [], "skipped_reason": "already_exists"}
                )
            
            # 按顺序生成章节正文
            from novelgen.chains.scene_text_chain import generate_scene_text
            
            generated = []
            failed = []
            total_words = 0
            
            for ch_num in sorted(chapters_to_generate):
                # 加载章节计划
                plan_path = _get_chapter_plan_path(ch_num)
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan = ChapterPlan(**json.load(f))
                
                try:
                    print(f"📝 正在生成第 {ch_num} 章：{plan.chapter_title}")
                    
                    generated_scenes = []
                    previous_summary = ""
                    
                    for scene_plan in plan.scenes:
                        print(f"    生成场景 {scene_plan.scene_number}...")
                        
                        scene = generate_scene_text(
                            scene_plan=scene_plan,
                            world_setting=world,
                            characters=characters,
                            previous_summary=previous_summary,
                            chapter_context="",
                            scene_memory_context=None,
                            verbose=False
                        )
                        generated_scenes.append(scene)
                        
                        # 更新前文摘要
                        previous_summary = scene.content[:200] + "..." if len(scene.content) > 200 else scene.content
                    
                    # 组装章节
                    chapter = GeneratedChapter(
                        chapter_number=ch_num,
                        chapter_title=plan.chapter_title,
                        scenes=generated_scenes,
                        total_words=sum(s.word_count for s in generated_scenes)
                    )
                    
                    # 保存章节
                    chapter_path = _get_chapter_text_path(ch_num)
                    with open(chapter_path, 'w', encoding='utf-8') as f:
                        json.dump(chapter.model_dump(), f, ensure_ascii=False, indent=2)
                    
                    generated.append(ch_num)
                    total_words += chapter.total_words
                    print(f"✅ 第 {ch_num} 章生成完成，共 {chapter.total_words} 字")
                    
                except Exception as e:
                    failed.append({"chapter": ch_num, "error": str(e)})
                    print(f"❌ 第 {ch_num} 章生成失败: {e}")
                    
                    # 顺序模式下，一个失败则停止后续生成
                    if sequential:
                        break
            
            success_msg = f"生成 {len(generated)} 章正文，共 {total_words:,} 字"
            if skipped:
                success_msg += f"，跳过 {len(skipped)} 章"
            if failed:
                success_msg += f"，失败 {len(failed)} 章"
            
            return ToolResult(
                tool_name="chapter.text.generate",
                success=len(failed) == 0,
                message=success_msg,
                data={
                    "generated": generated,
                    "skipped": skipped,
                    "failed": failed,
                    "total_words": total_words
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="chapter.text.generate",
                success=False,
                error=str(e)
            )
    
    def delete_chapter_plan(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None
    ) -> ToolResult:
        """删除章节计划（破坏性操作）
        
        Args:
            chapter_scope_start: 章节范围起始
            chapter_scope_end: 章节范围结束
            chapter_numbers: 显式章节编号列表
            
        Returns:
            删除结果的 ToolResult
        """
        try:
            _ensure_chapters_dir()
            
            # 解析章节范围
            chapter_scope = None
            if chapter_scope_start is not None and chapter_scope_end is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_end)
            elif chapter_scope_start is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_start)
            
            outline = _load_outline()
            target_chapters = _parse_chapter_scope(
                chapter_scope=chapter_scope,
                chapter_numbers=chapter_numbers,
                outline=outline
            )
            
            if not target_chapters:
                return ToolResult(
                    tool_name="chapter.plan.delete",
                    success=False,
                    error="未指定有效的章节范围"
                )
            
            deleted = []
            not_found = []
            
            for ch_num in target_chapters:
                plan_path = _get_chapter_plan_path(ch_num)
                if os.path.exists(plan_path):
                    os.remove(plan_path)
                    deleted.append(ch_num)
                else:
                    not_found.append(ch_num)
            
            return ToolResult(
                tool_name="chapter.plan.delete",
                success=True,
                message=f"删除 {len(deleted)} 个章节计划",
                data={"deleted": deleted, "not_found": not_found}
            )
        except Exception as e:
            return ToolResult(
                tool_name="chapter.plan.delete",
                success=False,
                error=str(e)
            )
    
    def delete_chapter_text(
        chapter_scope_start: Optional[int] = None,
        chapter_scope_end: Optional[int] = None,
        chapter_numbers: Optional[List[int]] = None
    ) -> ToolResult:
        """删除章节正文（破坏性操作）
        
        Args:
            chapter_scope_start: 章节范围起始
            chapter_scope_end: 章节范围结束
            chapter_numbers: 显式章节编号列表
            
        Returns:
            删除结果的 ToolResult
        """
        try:
            _ensure_chapters_dir()
            
            # 解析章节范围
            chapter_scope = None
            if chapter_scope_start is not None and chapter_scope_end is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_end)
            elif chapter_scope_start is not None:
                chapter_scope = ChapterScope(start=chapter_scope_start, end=chapter_scope_start)
            
            outline = _load_outline()
            target_chapters = _parse_chapter_scope(
                chapter_scope=chapter_scope,
                chapter_numbers=chapter_numbers,
                outline=outline
            )
            
            if not target_chapters:
                return ToolResult(
                    tool_name="chapter.text.delete",
                    success=False,
                    error="未指定有效的章节范围"
                )
            
            deleted = []
            not_found = []
            
            for ch_num in target_chapters:
                text_path = _get_chapter_text_path(ch_num)
                if os.path.exists(text_path):
                    os.remove(text_path)
                    deleted.append(ch_num)
                else:
                    not_found.append(ch_num)
            
            return ToolResult(
                tool_name="chapter.text.delete",
                success=True,
                message=f"删除 {len(deleted)} 个章节正文",
                data={"deleted": deleted, "not_found": not_found}
            )
        except Exception as e:
            return ToolResult(
                tool_name="chapter.text.delete",
                success=False,
                error=str(e)
            )
    
    def ensure_all_plans(force_missing_only: bool = True) -> ToolResult:
        """确保所有章节计划存在（语义糖）
        
        等价于 chapter.plan.generate(missing_only=True)
        
        Args:
            force_missing_only: 是否只生成缺失的（默认 True）
            
        Returns:
            生成结果的 ToolResult
        """
        return generate_chapter_plan(
            chapter_scope_start=None,
            chapter_scope_end=None,
            chapter_numbers=None,
            force=False,
            missing_only=force_missing_only
        )
    
    def ensure_all_texts(force_missing_only: bool = True) -> ToolResult:
        """确保所有章节正文存在（语义糖）
        
        等价于 chapter.text.generate(missing_only=True)
        
        Args:
            force_missing_only: 是否只生成缺失的（默认 True）
            
        Returns:
            生成结果的 ToolResult
        """
        return generate_chapter_text(
            chapter_scope_start=None,
            chapter_scope_end=None,
            chapter_numbers=None,
            force=False,
            missing_only=force_missing_only,
            sequential=True
        )
    
    # 创建工具定义
    tools = [
        Tool(
            name="chapter.plan.generate",
            category=ToolCategory.FINE_GRAINED,
            description="生成章节计划（支持章节范围/missing_only/force）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=generate_chapter_plan
        ),
        Tool(
            name="chapter.text.generate",
            category=ToolCategory.FINE_GRAINED,
            description="生成章节正文（支持章节范围/missing_only/force/sequential）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=generate_chapter_text
        ),
        Tool(
            name="chapter.plan.delete",
            category=ToolCategory.FINE_GRAINED,
            description="删除章节计划（破坏性操作）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            handler=delete_chapter_plan
        ),
        Tool(
            name="chapter.text.delete",
            category=ToolCategory.FINE_GRAINED,
            description="删除章节正文（破坏性操作）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            handler=delete_chapter_text
        ),
        Tool(
            name="chapter.plan.ensure_all",
            category=ToolCategory.FINE_GRAINED,
            description="确保所有章节计划存在（语义糖）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=ensure_all_plans
        ),
        Tool(
            name="chapter.text.ensure_all",
            category=ToolCategory.FINE_GRAINED,
            description="确保所有章节正文存在（语义糖）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=ensure_all_texts
        ),
    ]
    
    return tools
