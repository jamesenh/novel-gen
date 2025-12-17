"""
场景级工具模块
提供 scene.generate / scene.delete / scene.merge_to_chapter 等细粒度工具

核心功能：
- scene.generate: 生成单个场景
- scene.delete: 删除场景（破坏性）
- scene.merge_to_chapter: 将场景合并到章节

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from typing import Optional, List
from datetime import datetime

from novelgen.tools.registry import Tool, ToolCategory, ConfirmLevel, ToolResult
from novelgen.models import (
    WorldSetting, CharactersConfig, ChapterPlan, ScenePlan,
    GeneratedChapter, GeneratedScene
)
from novelgen.runtime.gate import (
    check_pending_revision_gate,
    PendingRevisionGateError
)


def create_scene_tools(project_dir: str, project_id: str) -> list[Tool]:
    """创建场景级工具集
    
    Args:
        project_dir: 项目目录路径
        project_id: 项目ID
        
    Returns:
        工具列表
    """
    chapters_dir = os.path.join(project_dir, "chapters")
    scenes_dir = os.path.join(project_dir, "scenes")
    
    def _ensure_dirs():
        """确保目录存在"""
        os.makedirs(chapters_dir, exist_ok=True)
        os.makedirs(scenes_dir, exist_ok=True)
    
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
    
    def _load_chapter_plan(chapter_num: int) -> Optional[ChapterPlan]:
        """加载章节计划"""
        plan_file = os.path.join(chapters_dir, f"chapter_{chapter_num:03d}_plan.json")
        if not os.path.exists(plan_file):
            return None
        with open(plan_file, 'r', encoding='utf-8') as f:
            return ChapterPlan(**json.load(f))
    
    def _load_chapter(chapter_num: int) -> Optional[GeneratedChapter]:
        """加载章节"""
        chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num:03d}.json")
        if not os.path.exists(chapter_file):
            return None
        with open(chapter_file, 'r', encoding='utf-8') as f:
            return GeneratedChapter(**json.load(f))
    
    def _get_scene_file(chapter_num: int, scene_num: int) -> str:
        """获取场景文件路径"""
        return os.path.join(scenes_dir, f"chapter_{chapter_num:03d}_scene_{scene_num:02d}.json")
    
    def scene_generate(
        chapter_number: int,
        scene_number: Optional[int] = None,
        force: bool = False
    ) -> ToolResult:
        """生成单个场景
        
        Args:
            chapter_number: 章节编号
            scene_number: 场景编号（None = 生成该章节所有缺失场景）
            force: 是否强制覆盖已存在的场景
            
        Returns:
            生成结果的 ToolResult
        """
        try:
            _ensure_dirs()
            
            # Pending revision 闸门检查
            # 开发者: jamesenh, 开发时间: 2025-12-16
            try:
                check_pending_revision_gate(project_dir, chapter_number)
            except PendingRevisionGateError as gate_error:
                return ToolResult(
                    tool_name="scene.generate",
                    success=False,
                    error=str(gate_error),
                    data=gate_error.to_dict()
                )
            
            # 加载前置依赖
            world = _load_world()
            characters = _load_characters()
            plan = _load_chapter_plan(chapter_number)
            
            if world is None or characters is None:
                return ToolResult(
                    tool_name="scene.generate",
                    success=False,
                    error="缺失前置依赖（世界观或角色）"
                )
            
            if plan is None:
                return ToolResult(
                    tool_name="scene.generate",
                    success=False,
                    error=f"第 {chapter_number} 章计划不存在"
                )
            
            # 确定要生成的场景
            if scene_number is not None:
                # 指定单个场景
                scene_plans = [sp for sp in plan.scenes if sp.scene_number == scene_number]
                if not scene_plans:
                    return ToolResult(
                        tool_name="scene.generate",
                        success=False,
                        error=f"第 {chapter_number} 章场景 {scene_number} 不在计划中"
                    )
            else:
                # 所有场景
                scene_plans = plan.scenes
            
            # 过滤已存在的（如果不是 force）
            scenes_to_generate = []
            skipped = []
            
            for sp in scene_plans:
                scene_file = _get_scene_file(chapter_number, sp.scene_number)
                if os.path.exists(scene_file) and not force:
                    skipped.append(sp.scene_number)
                else:
                    scenes_to_generate.append(sp)
            
            if not scenes_to_generate:
                return ToolResult(
                    tool_name="scene.generate",
                    success=True,
                    message=f"所有场景已存在（跳过 {len(skipped)} 个）",
                    data={"skipped": skipped, "generated": []}
                )
            
            # 生成场景
            from novelgen.chains.scene_text_chain import generate_scene_text
            
            generated = []
            failed = []
            previous_summary = ""
            
            for sp in scenes_to_generate:
                try:
                    print(f"📝 生成第 {chapter_number} 章场景 {sp.scene_number}...")
                    
                    scene = generate_scene_text(
                        scene_plan=sp,
                        world_setting=world,
                        characters=characters,
                        previous_summary=previous_summary,
                        chapter_context="",
                        scene_memory_context=None,
                        verbose=False
                    )
                    
                    # 保存场景文件
                    scene_file = _get_scene_file(chapter_number, sp.scene_number)
                    with open(scene_file, 'w', encoding='utf-8') as f:
                        json.dump(scene.model_dump(), f, ensure_ascii=False, indent=2)
                    
                    generated.append(sp.scene_number)
                    previous_summary = scene.content[:200] + "..." if len(scene.content) > 200 else scene.content
                    
                except Exception as e:
                    failed.append({"scene": sp.scene_number, "error": str(e)})
            
            return ToolResult(
                tool_name="scene.generate",
                success=len(failed) == 0,
                message=f"生成 {len(generated)} 个场景",
                data={
                    "chapter": chapter_number,
                    "generated": generated,
                    "skipped": skipped,
                    "failed": failed
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="scene.generate",
                success=False,
                error=str(e)
            )
    
    def scene_delete(
        chapter_number: int,
        scene_number: Optional[int] = None
    ) -> ToolResult:
        """删除场景（破坏性操作）
        
        Args:
            chapter_number: 章节编号
            scene_number: 场景编号（None = 删除该章节所有场景）
            
        Returns:
            删除结果的 ToolResult
        """
        try:
            if not os.path.exists(scenes_dir):
                return ToolResult(
                    tool_name="scene.delete",
                    success=True,
                    message="没有可删除的场景",
                    data={"deleted": []}
                )
            
            deleted = []
            not_found = []
            
            if scene_number is not None:
                # 删除单个场景
                scene_file = _get_scene_file(chapter_number, scene_number)
                if os.path.exists(scene_file):
                    os.remove(scene_file)
                    deleted.append(scene_number)
                else:
                    not_found.append(scene_number)
            else:
                # 删除该章节所有场景
                prefix = f"chapter_{chapter_number:03d}_scene_"
                for f in os.listdir(scenes_dir):
                    if f.startswith(prefix) and f.endswith(".json"):
                        try:
                            scene_num = int(f.replace(prefix, "").replace(".json", ""))
                            os.remove(os.path.join(scenes_dir, f))
                            deleted.append(scene_num)
                        except (ValueError, OSError):
                            pass
            
            return ToolResult(
                tool_name="scene.delete",
                success=True,
                message=f"删除 {len(deleted)} 个场景",
                data={
                    "chapter": chapter_number,
                    "deleted": sorted(deleted),
                    "not_found": not_found
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="scene.delete",
                success=False,
                error=str(e)
            )
    
    def scene_merge_to_chapter(chapter_number: int) -> ToolResult:
        """将场景合并到章节
        
        将独立生成的场景文件合并为完整章节 JSON
        
        Args:
            chapter_number: 章节编号
            
        Returns:
            合并结果的 ToolResult
        """
        try:
            _ensure_dirs()
            
            # Pending revision 闸门检查
            # 开发者: jamesenh, 开发时间: 2025-12-16
            try:
                check_pending_revision_gate(project_dir, chapter_number)
            except PendingRevisionGateError as gate_error:
                return ToolResult(
                    tool_name="scene.merge_to_chapter",
                    success=False,
                    error=str(gate_error),
                    data=gate_error.to_dict()
                )
            
            # 加载章节计划
            plan = _load_chapter_plan(chapter_number)
            if plan is None:
                return ToolResult(
                    tool_name="scene.merge_to_chapter",
                    success=False,
                    error=f"第 {chapter_number} 章计划不存在"
                )
            
            # 查找所有场景文件
            scenes = []
            missing = []
            
            for sp in plan.scenes:
                scene_file = _get_scene_file(chapter_number, sp.scene_number)
                if os.path.exists(scene_file):
                    with open(scene_file, 'r', encoding='utf-8') as f:
                        scene = GeneratedScene(**json.load(f))
                        scenes.append(scene)
                else:
                    missing.append(sp.scene_number)
            
            if missing:
                return ToolResult(
                    tool_name="scene.merge_to_chapter",
                    success=False,
                    error=f"缺失场景: {missing}",
                    data={"missing_scenes": missing}
                )
            
            if not scenes:
                return ToolResult(
                    tool_name="scene.merge_to_chapter",
                    success=False,
                    error="没有可合并的场景"
                )
            
            # 按场景编号排序
            scenes.sort(key=lambda s: s.scene_number)
            
            # 创建章节
            total_words = sum(s.word_count for s in scenes)
            chapter = GeneratedChapter(
                chapter_number=chapter_number,
                chapter_title=plan.chapter_title,
                scenes=scenes,
                total_words=total_words
            )
            
            # 保存章节
            chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_number:03d}.json")
            with open(chapter_file, 'w', encoding='utf-8') as f:
                json.dump(chapter.model_dump(), f, ensure_ascii=False, indent=2)
            
            return ToolResult(
                tool_name="scene.merge_to_chapter",
                success=True,
                message=f"第 {chapter_number} 章合并完成，共 {len(scenes)} 个场景，{total_words:,} 字",
                data={
                    "chapter_number": chapter_number,
                    "scene_count": len(scenes),
                    "total_words": total_words,
                    "output_file": chapter_file
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="scene.merge_to_chapter",
                success=False,
                error=str(e)
            )
    
    # 创建工具定义
    tools = [
        Tool(
            name="scene.generate",
            category=ToolCategory.FINE_GRAINED,
            description="生成单个场景（支持 force 覆盖）",
            confirm_level=ConfirmLevel.NORMAL,
            handler=scene_generate
        ),
        Tool(
            name="scene.delete",
            category=ToolCategory.FINE_GRAINED,
            description="删除场景（破坏性操作）",
            confirm_level=ConfirmLevel.DESTRUCTIVE,
            handler=scene_delete
        ),
        Tool(
            name="scene.merge_to_chapter",
            category=ToolCategory.FINE_GRAINED,
            description="将场景合并到章节",
            confirm_level=ConfirmLevel.NORMAL,
            handler=scene_merge_to_chapter
        ),
    ]
    
    return tools
