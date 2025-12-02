# 开发者: jamesenh, 开发时间: 2025-11-17
# 更新: 2025-11-25 - 简化记忆层架构，移除 SQLite 和独立 VectorStore，统一使用 Mem0
# 更新: 2025-11-30 - 添加 cleanup 方法和退出调试日志

"""
编排器
协调整个小说生成流程，使用 Mem0 作为唯一的记忆存储层
"""
import os
import json
import time
import threading
from typing import Optional, Union, List, Dict, Any

# 调试模式开关
DEBUG_EXIT = os.getenv("NOVELGEN_DEBUG", "0") == "1"


def _debug_log(msg: str):
    """输出调试日志（仅在 DEBUG_EXIT=True 时）"""
    if DEBUG_EXIT:
        timestamp = time.strftime("%H:%M:%S")
        thread_name = threading.current_thread().name
        print(f"[{timestamp}][{thread_name}] 🔍 [orchestrator] {msg}")

from novelgen.models import (
    WorldSetting, ThemeConflict, CharactersConfig,
    Outline, ChapterPlan, GeneratedChapter, GeneratedScene,
    ChapterSummary, ChapterMemoryEntry, ConsistencyReport, RevisionStatus,
    EntityStateSnapshot, StoryMemoryChunk, SceneMemoryContext
)
from novelgen.config import ProjectConfig
from novelgen.chains.world_chain import generate_world
from novelgen.chains.theme_conflict_chain import generate_theme_conflict
from novelgen.chains.characters_chain import generate_characters
from novelgen.chains.outline_chain import generate_outline
from novelgen.chains.chapters_plan_chain import generate_chapter_plan
from novelgen.chains.scene_text_chain import generate_scene_text
from novelgen.runtime.exporter import export_chapter_to_txt, export_all_chapters_to_txt
from novelgen.runtime.summary import summarize_scene, summarize_scenes
from novelgen.runtime.memory import generate_chapter_memory_entry
from novelgen.runtime.consistency import run_consistency_check
from novelgen.chains.chapter_revision_chain import revise_chapter
from novelgen.runtime.workflow import (
    create_novel_generation_workflow, 
    get_default_recursion_limit,
    get_estimated_nodes_per_chapter
)
from novelgen.runtime.mem0_manager import Mem0Manager, is_shutdown_requested
from novelgen.models import NovelGenerationState
from datetime import datetime
from typing import Dict as TypingDict


class NovelOrchestrator:
    """小说生成编排器
    
    使用 Mem0 作为唯一的记忆层，不再支持 SQLite 和独立 VectorStore 的降级模式
    """

    def __init__(self, project_name: str, base_dir: str = "projects", verbose: bool = False, show_prompt: bool = True):
        """初始化编排器

        Args:
            project_name: 项目名称
            base_dir: 项目基础目录
            verbose: 是否启用详细日志（显示提示词、响应时间、token使用情况）
            show_prompt: verbose 模式下是否显示完整提示词（默认 True）

        Raises:
            RuntimeError: 如果 Mem0 未启用或初始化失败
        """
        self.project_name = project_name
        self.project_dir = os.path.join(base_dir, project_name)
        self.config = ProjectConfig(project_dir=self.project_dir)
        self.verbose = verbose
        self.show_prompt = show_prompt

        # 创建项目目录
        os.makedirs(self.project_dir, exist_ok=True)
        os.makedirs(self.config.chapters_dir, exist_ok=True)

        # 初始化 Mem0 管理器（作为唯一的记忆层）
        self.mem0_manager: Optional[Mem0Manager] = None
        
        # 检查 Mem0 配置
        if not hasattr(self.config, 'mem0_config') or not self.config.mem0_config:
            raise RuntimeError(
                "Mem0 配置未设置。请设置环境变量 MEM0_ENABLED=true 并配置相关参数。"
            )
        
        if not self.config.mem0_config.enabled:
            raise RuntimeError(
                "Mem0 未启用。请设置环境变量 MEM0_ENABLED=true。"
            )
        
        # 初始化 Mem0
        try:
            from novelgen.runtime.mem0_manager import Mem0Manager, Mem0InitializationError
            self.mem0_manager = Mem0Manager(
                config=self.config.mem0_config,
                project_id=project_name,
                embedding_config=self.config.embedding_config
            )
            health = self.mem0_manager.health_check()
            if health["status"] == "healthy":
                print(f"✅ Mem0 记忆层已启用: {health['message']}")
            else:
                raise RuntimeError(f"Mem0 健康检查失败: {health['message']}")
        except Exception as e:
            raise RuntimeError(f"Mem0 初始化失败: {e}") from e
        
        # 初始化 LangGraph 工作流（使用 SQLite 持久化检查点）
        self.workflow = create_novel_generation_workflow(project_dir=self.project_dir)
        self._workflow_state: Optional[NovelGenerationState] = None
        print("✅ LangGraph 工作流已初始化（SQLite 持久化）")

    def save_json(self, data, filepath: str):
        """保存JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            if hasattr(data, 'model_dump'):
                json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def load_json(self, filepath: str, model_class=None):
        """加载JSON文件"""
        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if model_class:
            return model_class(**data)
        return data

    def _load_chapter_memory_entries(self) -> List[ChapterMemoryEntry]:
        """读取章节记忆文件"""
        if not os.path.exists(self.config.chapter_memory_file):
            return []

        try:
            with open(self.config.chapter_memory_file, 'r', encoding='utf-8') as f:
                raw_entries = json.load(f)
        except json.JSONDecodeError as exc:
            print(f"⚠️ 章节记忆文件解析失败，将忽略：{exc}")
            return []

        entries = []
        for item in raw_entries:
            try:
                entries.append(ChapterMemoryEntry(**item))
            except Exception as exc:
                print(f"⚠️ 章节记忆记录无效，已跳过: {exc}")
        return entries

    def _save_chapter_memory_entries(self, entries: List[ChapterMemoryEntry]):
        """将章节记忆列表写回磁盘"""
        serializable = [entry.model_dump() for entry in entries]
        self.save_json(serializable, self.config.chapter_memory_file)

    def _append_chapter_memory_entry(self, entry: ChapterMemoryEntry):
        """追加或替换某章节的记忆记录"""
        entries = self._load_chapter_memory_entries()
        entries = [e for e in entries if e.chapter_number != entry.chapter_number]
        entries.append(entry)
        entries.sort(key=lambda e: e.chapter_number)
        self._save_chapter_memory_entries(entries)

    def _get_recent_chapter_memory(self, chapter_number: int, limit: Optional[int] = None) -> List[ChapterMemoryEntry]:
        """
        按章节编号过滤并返回最近的记忆条目

        Args:
            chapter_number: 当前章节编号
            limit: 需要的历史条目数量
        """
        entries = [
            entry for entry in self._load_chapter_memory_entries()
            if entry.chapter_number < chapter_number
        ]
        entries.sort(key=lambda e: e.chapter_number, reverse=True)
        if limit is not None:
            entries = entries[:limit]
        return list(reversed(entries))

    def _format_memory_entries(self, entries: List[ChapterMemoryEntry]) -> str:
        """将记忆条目列表序列化为JSON字符串"""
        if not entries:
            return "[]"
        payload = [entry.model_dump() for entry in entries]
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _build_chapter_context_payload(self, chapter_number: int) -> str:
        """根据章节编号构建用于提示词的上下文载荷"""
        recent_entries = self._get_recent_chapter_memory(
            chapter_number,
            limit=self.config.memory_context_chapters
        )
        return self._format_memory_entries(recent_entries)

    def _get_chapter_summary(self, chapter_number: int) -> Optional[ChapterSummary]:
        """从大纲中获取指定章节的摘要"""
        outline = self.load_json(self.config.outline_file, Outline)
        if not outline:
            return None
        for chapter in outline.chapters:
            if chapter.chapter_number == chapter_number:
                return chapter
        return None

    def _ensure_chapter_dependencies_met(self, chapter_summary: ChapterSummary):
        """校验章节依赖的逻辑有效性（step5阶段）"""
        if not chapter_summary or not chapter_summary.dependencies:
            return

        # step5阶段只验证逻辑有效性，不验证实际满足情况
        for dep in chapter_summary.dependencies:
            if dep.chapter_number is None:
                continue
            if dep.chapter_number >= chapter_summary.chapter_number:
                raise ValueError(
                    f"章节{chapter_summary.chapter_number}依赖无效：不能依赖未来章节{dep.chapter_number}"
                )

    def _ensure_chapter_dependencies_actually_met(self, chapter_summary: ChapterSummary):
        """校验章节依赖是否已经由既有章节内容满足（step6开始前）"""
        if not chapter_summary or not chapter_summary.dependencies:
            return

        # 检查已完成的章节内容文件（使用实际保存的章节JSON文件）
        existing = set()
        for i in range(1, chapter_summary.chapter_number):
            content_file = os.path.join(
                self.config.chapters_dir,
                f"chapter_{i:03d}.json"
            )
            if os.path.exists(content_file):
                existing.add(i)
        
        unmet = []
        for dep in chapter_summary.dependencies:
            if dep.chapter_number is None or dep.chapter_number <= 0:
                continue
            if dep.chapter_number not in existing:
                unmet.append(f"章节{dep.chapter_number} - {dep.description}")

        if unmet:
            raise ValueError(
                f"章节{chapter_summary.chapter_number}尚未满足以下依赖：{'; '.join(unmet)}"
            )

    def _build_consistency_context(self, chapter_number: int, chapter_summary: Optional[ChapterSummary]) -> str:
        """组合一致性检测所需的上下文（大纲+记忆）"""
        recent_entries = self._get_recent_chapter_memory(
            chapter_number,
            limit=self.config.memory_context_chapters
        )
        payload = {
            "outline_summary": chapter_summary.model_dump() if chapter_summary else {},
            "recent_memory": [entry.model_dump() for entry in recent_entries]
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _record_consistency_report(self, report: ConsistencyReport):
        """将一致性检测结果附加到项目报告文件"""
        data = []
        if os.path.exists(self.config.consistency_report_file):
            try:
                with open(self.config.consistency_report_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []

        data.append(report.model_dump())
        with open(self.config.consistency_report_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _handle_revision_stage(self, report: ConsistencyReport, chapter: GeneratedChapter):
        """
        根据 revision_policy 处理章节修订阶段

        Args:
            report: 一致性检测结果
            chapter: 原始章节对象

        Returns:
            修订后的章节（如果 auto_apply），或原始章节（其他情况）
        """
        chapter_number = chapter.chapter_number
        
        # 检查是否有可自动修复的问题（基于 fix_instructions 是否存在）
        actionable = [
            issue for issue in report.issues
            if issue.fix_instructions and issue.fix_instructions.strip()
        ]
        if not actionable:
            return chapter

        revision_notes = "\n".join(
            f"- {issue.issue_type}: {issue.fix_instructions}"
            for issue in actionable
        )

        policy = self.config.revision_policy
        
        if policy == "none":
            # 保持当前行为：不做任何修订
            return chapter
        
        elif policy == "auto_apply":
            # 自动应用模式：直接修订并更新 JSON
            print(f"🔧 [auto_apply] 正在对第{chapter_number}章进行自动修订，修复{len(actionable)}个问题...")
            try:
                revised_chapter = revise_chapter(
                    original_chapter=chapter,
                    revision_notes=revision_notes,
                    verbose=self.verbose,
                    llm_config=self.config.revision_chain_config.llm_config
                )
                
                # 保存修订后的章节 JSON
                chapter_file = os.path.join(
                    self.config.chapters_dir,
                    f"chapter_{chapter_number:03d}.json"
                )
                self.save_json(revised_chapter, chapter_file)
                print(f"✅ 第{chapter_number}章修订完成，已更新章节 JSON")
                
                # 可选：导出可读文本供审阅
                revised_text = self._collect_chapter_text(revised_chapter)
                revision_txt_file = os.path.join(
                    self.config.chapters_dir,
                    f"chapter_{chapter_number:03d}_revised.txt"
                )
                with open(revision_txt_file, 'w', encoding='utf-8') as f:
                    f.write(revised_text)
                print(f"📄 修订文本已导出至：{revision_txt_file}")
                
                # 保存实体状态到 Mem0
                print(f"💾 正在更新第{chapter_number}章的实体状态到 Mem0...")
                self._save_entity_state("chapter_text", f"chapter_{chapter_number}_text", 
                                       json.dumps(revised_chapter.model_dump(), ensure_ascii=False)[:500],
                                       chapter_number)
                
                # 重新生成场景摘要和聚合摘要
                print(f"📝 正在重新生成第{chapter_number}章的摘要...")
                scene_summaries = []
                for scene in revised_chapter.scenes:
                    scene_summary = self._summarize_scene_safe(scene)
                    scene_summaries.append(f"场景{scene.scene_number}: {scene_summary}")
                
                aggregated_summary = self._summarize_chapter_safe(revised_chapter.scenes)
                
                # 重新生成并更新章节记忆
                print(f"🧠 正在重新生成第{chapter_number}章的记忆条目...")
                try:
                    chapter_summary = self._get_chapter_summary(chapter_number)
                    memory_entry = generate_chapter_memory_entry(
                        chapter=revised_chapter,
                        outline_summary=chapter_summary,
                        scene_summaries=scene_summaries,
                        aggregated_summary=aggregated_summary,
                        verbose=self.verbose,
                        llm_config=self.config.chapter_memory_chain_config.llm_config
                    )
                    self._append_chapter_memory_entry(memory_entry)
                    print(f"✅ 第{chapter_number}章记忆条目已更新")
                except Exception as mem_exc:
                    print(f"⚠️ 更新章节记忆失败：{mem_exc}")
                
                # 更新场景内容到 Mem0
                print(f"🔄 正在更新第{chapter_number}章的场景内容到 Mem0...")
                try:
                    # 先删除该章节的旧记忆
                    self._delete_chapter_memory(chapter_number)
                    # 添加修订后的新场景内容
                    for scene in revised_chapter.scenes:
                        self._save_scene_content(
                            scene.content, 
                            chapter_number, 
                            scene.scene_number
                        )
                    print(f"✅ 第{chapter_number}章场景内容已更新到 Mem0")
                except Exception as vec_exc:
                    print(f"⚠️ 更新场景内容到 Mem0 失败：{vec_exc}")
                
                return revised_chapter
                
            except Exception as exc:
                print(f"⚠️ 自动修订失败：{exc}，保持原章节")
                return chapter
        
        elif policy == "manual_confirm":
            # 人工确认模式：生成修订候选，标记为 pending
            print(f"📝 [manual_confirm] 正在生成第{chapter_number}章修订候选...")
            try:
                revised_chapter = revise_chapter(
                    original_chapter=chapter,
                    revision_notes=revision_notes,
                    verbose=self.verbose,
                    llm_config=self.config.revision_chain_config.llm_config
                )
                
                # 创建修订状态记录
                revision_status = RevisionStatus(
                    chapter_number=chapter_number,
                    status="pending",
                    revision_notes=revision_notes,
                    issues=actionable,
                    revised_chapter=revised_chapter,
                    created_at=datetime.now().isoformat()
                )
                
                # 保存修订状态文件
                revision_status_file = os.path.join(
                    self.config.chapters_dir,
                    f"chapter_{chapter_number:03d}_revision.json"
                )
                self.save_json(revision_status, revision_status_file)
                print(f"✅ 第{chapter_number}章修订候选已生成，状态：pending")
                print(f"⏸️  请审核修订候选后调用 apply_revision 应用修订")
                
                # 可选：导出可读文本便于人工对比
                revised_text = self._collect_chapter_text(revised_chapter)
                revision_txt_file = os.path.join(
                    self.config.chapters_dir,
                    f"chapter_{chapter_number:03d}_revised.txt"
                )
                with open(revision_txt_file, 'w', encoding='utf-8') as f:
                    f.write(revised_text)
                print(f"📄 修订候选文本已导出至：{revision_txt_file}")
                
                return chapter  # 返回原始章节，不修改 JSON
                
            except Exception as exc:
                print(f"⚠️ 生成修订候选失败：{exc}")
                return chapter
        
        return chapter

    def _collect_chapter_text(self, chapter: GeneratedChapter) -> str:
        """将章节场景拼接成纯文本，供一致性检测使用"""
        return "\n\n".join(
            [f"场景 {scene.scene_number}:\n{scene.content}" for scene in chapter.scenes]
        )

    def _initial_previous_summary(self, chapter_number: int, chapter_context: str) -> str:
        """构造章节第一个场景所需的初始前文概要"""
        if chapter_context and chapter_context != "[]":
            return f"本章开篇。请承接以下章节上下文与悬念：{chapter_context[:800]}"
        return f"第{chapter_number}章开篇：本章第一个场景需要结合章节计划启动剧情。"

    def _summarize_scene_safe(self, scene: GeneratedScene) -> str:
        """
        调用摘要链生成场景摘要，若失败则使用片段
        """
        try:
            return summarize_scene(scene)
        except Exception as exc:
            fallback = scene.content[:120]
            return f"摘要失败({exc})，改用片段：{fallback}"

    def _summarize_chapter_safe(self, scenes: List[GeneratedScene]) -> str:
        """对整章场景生成汇总摘要，遇到异常时提供片段拼接"""
        try:
            return summarize_scenes(scenes)
        except Exception as exc:
            snippets = [scene.content[:80] for scene in scenes]
            return f"自动总结失败({exc})。片段汇总：{' '.join(snippets)}"

    def _save_entity_state(self, entity_type: str, entity_id: str, state_description: str, 
                          chapter_index: Optional[int] = None, scene_index: Optional[int] = None,
                          story_timeline: Optional[str] = None):
        """保存实体状态到 Mem0"""
        try:
            self.mem0_manager.add_entity_state(
                entity_id=entity_id,
                entity_type=entity_type,
                state_description=state_description,
                chapter_index=chapter_index,
                scene_index=scene_index,
                story_timeline=story_timeline,
            )
        except Exception as e:
            print(f"⚠️ 保存实体状态到 Mem0 失败: {e}")
    
    def _save_scene_content(self, content: str, chapter_index: int, scene_index: int, 
                           content_type: str = "scene"):
        """保存场景内容到 Mem0"""
        try:
            chunks = self.mem0_manager.add_scene_content(
                content=content,
                chapter_index=chapter_index,
                scene_index=scene_index,
                content_type=content_type
            )
            if chunks:
                print(f"    已将场景{scene_index}内容保存到 Mem0（{len(chunks)}个块）")
        except Exception as e:
            print(f"⚠️ 保存场景内容到 Mem0 失败: {e}")
    
    def _delete_chapter_memory(self, chapter_index: int):
        """删除指定章节的所有场景记忆"""
        try:
            self.mem0_manager.delete_chapter_memory(chapter_index)
            print(f"已删除第{chapter_index}章的场景记忆")
        except Exception as e:
            print(f"⚠️ 删除章节记忆失败: {e}")
    
    def _get_or_create_workflow_state(self) -> NovelGenerationState:
        """获取或创建工作流状态

        从项目目录加载已存在的 JSON 文件，并根据文件存在性推断 completed_steps。
        这样在重新运行时，工作流能够正确跳过已完成的步骤。

        更新: 2025-11-27 - 添加 completed_steps 推断逻辑，修复检查点恢复问题
        """
        if self._workflow_state is None:
            # 从 JSON 文件加载现有数据
            from novelgen.models import Settings

            # 从 settings.json 文件加载配置
            settings_file = os.path.join(self.project_dir, "settings.json")
            settings = self.load_json(settings_file, Settings)
            if settings is None:
                raise ValueError(f"settings.json 不存在或加载失败: {settings_file}")

            world = self.load_json(self.config.world_file, WorldSetting)
            theme_conflict = self.load_json(self.config.theme_conflict_file, ThemeConflict)
            characters = self.load_json(self.config.characters_file, CharactersConfig)
            outline = self.load_json(self.config.outline_file, Outline)

            # 加载章节计划和生成的章节
            chapters_plan = {}
            chapters = {}
            if outline:
                for ch_summary in outline.chapters:
                    num = ch_summary.chapter_number
                    plan_file = os.path.join(self.config.chapters_dir, f"chapter_{num:03d}_plan.json")
                    if os.path.exists(plan_file):
                        chapters_plan[num] = self.load_json(plan_file, ChapterPlan)

                    chapter_file = os.path.join(self.config.chapters_dir, f"chapter_{num:03d}.json")
                    if os.path.exists(chapter_file):
                        chapters[num] = self.load_json(chapter_file, GeneratedChapter)

            # 加载章节记忆
            chapter_memories = self._load_chapter_memory_entries()

            # 根据已存在的文件推断 completed_steps
            # 这是检查点恢复的关键：确保重新运行时能正确跳过已完成的步骤
            completed_steps = self._infer_completed_steps(
                settings=settings,
                world=world,
                theme_conflict=theme_conflict,
                characters=characters,
                outline=outline,
                chapters_plan=chapters_plan,
                chapters=chapters
            )

            if completed_steps:
                print(f"📋 检测到已完成的步骤: {', '.join(completed_steps)}")

            # 获取递归限制配置
            recursion_limit = get_default_recursion_limit()
            
            self._workflow_state = NovelGenerationState(
                project_name=self.project_name,
                project_dir=self.project_dir,
                settings=settings,
                world=world,
                theme_conflict=theme_conflict,
                characters=characters,
                outline=outline,
                chapters_plan=chapters_plan,
                chapters=chapters,
                chapter_memories=chapter_memories,
                completed_steps=completed_steps,
                verbose=self.verbose,  # 传递 verbose 参数到工作流状态
                show_prompt=self.show_prompt,  # 传递 show_prompt 参数到工作流状态
                # 递归限制预估机制相关字段
                recursion_limit=recursion_limit,
                node_execution_count=0,  # 初始化为 0
                should_stop_early=False
                # 注意：mem0_manager 不放入状态，因为它无法被 msgpack 序列化
                # 在 orchestrator 级别通过 self.mem0_manager 管理
            )

        return self._workflow_state

    def _infer_completed_steps(
        self,
        settings,
        world,
        theme_conflict,
        characters,
        outline,
        chapters_plan: dict,
        chapters: dict
    ) -> list:
        """根据已存在的数据推断 completed_steps 列表

        遵循工作流的执行顺序：
        1. load_settings
        2. world_creation
        3. theme_conflict_creation
        4. character_creation
        5. outline_creation
        6. chapter_planning
        7. init_chapter_loop
        8. chapter_generation_N (每个章节)
        9. consistency_check_N (每个章节)

        Args:
            settings: 项目配置
            world: 世界观设定
            theme_conflict: 主题冲突
            characters: 角色配置
            outline: 大纲
            chapters_plan: 章节计划字典
            chapters: 已生成章节字典

        Returns:
            推断出的已完成步骤列表
        """
        completed_steps = []

        # 按照工作流顺序推断
        if settings is not None:
            completed_steps.append("load_settings")

        if world is not None:
            completed_steps.append("world_creation")

        if theme_conflict is not None:
            completed_steps.append("theme_conflict_creation")

        if characters is not None:
            completed_steps.append("character_creation")

        if outline is not None:
            completed_steps.append("outline_creation")

        # 检查章节计划是否完整（所有章节都有计划）
        if outline and chapters_plan:
            expected_chapters = {ch.chapter_number for ch in outline.chapters}
            existing_plans = set(chapters_plan.keys())
            if expected_chapters <= existing_plans:
                completed_steps.append("chapter_planning")
                completed_steps.append("init_chapter_loop")

        # 推断已完成的章节生成和一致性检查
        for chapter_num in sorted(chapters.keys()):
            chapter = chapters[chapter_num]
            # 检查章节是否有实际内容（至少有一个场景）
            if chapter.scenes and len(chapter.scenes) > 0:
                completed_steps.append(f"chapter_generation_{chapter_num}")
                # 假设生成后都做了一致性检查
                completed_steps.append(f"consistency_check_{chapter_num}")

        return completed_steps
    
    def run_workflow(self, stop_at: Optional[str] = None) -> NovelGenerationState:
        """"运行完整工作流
        
        Args:
            stop_at: 可选的停止节点名称（如 "world_creation", "outline_creation" 等）
        
        Returns:
            最终的工作流状态
        """
        print("🚀 开始运行 LangGraph 工作流...")
        
        # 获取初始状态
        initial_state = self._get_or_create_workflow_state()
        
        # 配置工作流执行
        # 更新: 2025-11-30 - 从状态中读取 recursion_limit 并传入 config
        recursion_limit = initial_state.recursion_limit if initial_state else get_default_recursion_limit()
        config = {
            "configurable": {"thread_id": self.project_name},
            "recursion_limit": recursion_limit
        }
        print(f"   递归限制: {recursion_limit}, 每章预估节点数: {get_estimated_nodes_per_chapter()}")
        
        # 运行工作流
        final_state = None
        interrupted = False
        for state in self.workflow.stream(initial_state, config):
            # 检查是否收到停止信号
            if is_shutdown_requested():
                print("⏹️ 收到停止信号，工作流中断")
                interrupted = True
                break
            
            # state 是一个字典，包含节点名称和对应的状态更新
            for node_name, node_output in state.items():
                print(f"  ✓ 节点 '{node_name}' 执行完成")
                final_state = node_output
                
                # 如果指定了停止节点，检查是否到达
                if stop_at and node_name == stop_at:
                    print(f"⏸️  已到达停止节点 '{stop_at}'，工作流暂停")
                    self._workflow_state = final_state
                    return final_state
        
        if interrupted:
            print("⏹️ 工作流已被用户中断")
            self._workflow_state = final_state
            raise KeyboardInterrupt("用户中断工作流")
        
        print("✅ LangGraph 工作流执行完成")
        self._workflow_state = final_state
        return final_state
    
    def resume_workflow(self, checkpoint_id: Optional[str] = None) -> NovelGenerationState:
        """从检查点恢复工作流
        
        修复: 2025-11-30 - 在恢复前同步文件系统状态，确保场景文件能正确合并为章节
        
        Args:
            checkpoint_id: 检查点 ID（可选，默认使用最新检查点）
        
        Returns:
            恢复后的工作流状态
        """
        print(f"🔄 从检查点恢复工作流...")
        
        # 关键修复：先检查并合并未完成的章节（从场景文件）
        # 这处理了场景都生成了但章节文件未保存的情况
        self._merge_incomplete_chapters_from_scenes()
        
        # 配置工作流执行
        # 更新: 2025-11-30 - 从状态中读取 recursion_limit 并传入 config
        recursion_limit = get_default_recursion_limit()
        config = {
            "configurable": {"thread_id": self.project_name},
            "recursion_limit": recursion_limit
        }
        print(f"   递归限制: {recursion_limit}")
        
        # 获取检查点历史
        checkpoints = list(self.workflow.get_state_history(config))
        if not checkpoints:
            print("⚠️ 未找到检查点，将从头开始运行")
            return self.run_workflow()
        
        print(f"📋 找到 {len(checkpoints)} 个检查点")
        
        # 使用最新的检查点恢复
        latest_checkpoint = checkpoints[0]
        print(f"  恢复检查点: {latest_checkpoint.config['configurable']['thread_id']}")
        
        # 关键修复：从文件系统加载最新状态，与检查点状态同步
        # 这确保了在中断后新生成的文件（如场景文件）能被正确识别
        file_state = self._get_or_create_workflow_state()
        
        # 获取检查点中的状态
        checkpoint_state = latest_checkpoint.values
        
        # 同步文件系统状态到检查点（文件系统状态优先，因为它反映实际生成的内容）
        state_updates = self._sync_file_state_to_checkpoint(file_state, checkpoint_state)
        
        if state_updates:
            print(f"📂 同步文件系统状态: {list(state_updates.keys())}")
            # 使用 update_state 更新检查点状态
            self.workflow.update_state(config, state_updates)
        
        # 从检查点继续执行
        final_state = None
        interrupted = False
        for state in self.workflow.stream(None, config):
            # 检查是否收到停止信号
            if is_shutdown_requested():
                print("⏹️ 收到停止信号，工作流中断")
                interrupted = True
                break
            
            for node_name, node_output in state.items():
                print(f"  ✓ 节点 '{node_name}' 执行完成")
                final_state = node_output
        
        if interrupted:
            print("⏹️ 工作流已被用户中断")
            self._workflow_state = final_state
            raise KeyboardInterrupt("用户中断工作流")
        
        # 检查是否真的完成了所有工作
        # 如果 final_state 是 None（工作流认为已经结束），需要检查是否有未完成的章节
        if final_state is None:
            print("⚠️ 检查点显示工作流已结束，检查是否有未完成的章节...")
            incomplete_chapters = self._check_incomplete_chapters()
            
            if incomplete_chapters:
                print(f"🔍 发现 {len(incomplete_chapters)} 个未完成的章节: {incomplete_chapters}")
                print("📝 检查点状态已损坏，将重新运行工作流（跳过已完成章节）...")
                
                # 重置检查点，使用文件系统状态重新开始
                # 先合并已有的场景文件
                self._merge_incomplete_chapters_from_scenes()
                
                # 重新获取状态并运行
                return self.run_workflow()
            else:
                print("✅ 所有章节已完成")
                # 返回文件系统状态
                final_state = self._get_or_create_workflow_state()
        
        print("✅ 工作流恢复执行完成")
        self._workflow_state = final_state
        return final_state
    
    def _check_incomplete_chapters(self) -> List[int]:
        """检查有哪些章节未完成
        
        根据文件系统状态检测：
        1. 章节计划存在但章节JSON不存在
        2. 场景文件数量少于计划的场景数
        
        Returns:
            未完成的章节编号列表
        """
        import os
        import json
        
        chapters_dir = os.path.join(self.project_dir, "chapters")
        if not os.path.exists(chapters_dir):
            return []
        
        incomplete = []
        
        # 扫描所有章节计划
        for filename in os.listdir(chapters_dir):
            if not filename.endswith("_plan.json"):
                continue
            
            # 提取章节号
            try:
                ch_num = int(filename.split("_")[1])
            except (IndexError, ValueError):
                continue
            
            # 检查章节JSON是否存在
            chapter_file = os.path.join(chapters_dir, f"chapter_{ch_num:03d}.json")
            if not os.path.exists(chapter_file):
                # 章节JSON不存在，检查场景文件
                plan_file = os.path.join(chapters_dir, filename)
                try:
                    with open(plan_file, 'r', encoding='utf-8') as f:
                        plan_data = json.load(f)
                    expected_scenes = len(plan_data.get("scenes", []))
                except Exception:
                    expected_scenes = 0
                
                # 统计已有的场景文件
                scene_files = [f for f in os.listdir(chapters_dir) 
                              if f.startswith(f"scene_{ch_num:03d}_") and f.endswith(".json")]
                actual_scenes = len(scene_files)
                
                if actual_scenes < expected_scenes:
                    incomplete.append(ch_num)
                    print(f"    第{ch_num}章: {actual_scenes}/{expected_scenes} 场景")
        
        return sorted(incomplete)
    
    def _sync_file_state_to_checkpoint(
        self, 
        file_state: NovelGenerationState, 
        checkpoint_state: dict
    ) -> dict:
        """同步文件系统状态到检查点状态
        
        比较文件系统状态和检查点状态，返回需要更新的字段。
        文件系统状态优先，因为它反映实际生成的内容。
        
        关键场景：
        - 场景文件已生成但 chapter_XXX.json 未保存
        - 中断后文件系统有新内容但检查点未更新
        
        Args:
            file_state: 从文件系统加载的状态
            checkpoint_state: 检查点中的状态
            
        Returns:
            需要更新的状态字段字典
        """
        updates = {}
        
        # 同步 chapters：确保已生成的章节被识别
        file_chapters = file_state.chapters or {}
        checkpoint_chapters = checkpoint_state.get("chapters", {}) or {}
        
        # 检查是否有文件系统中存在但检查点中缺失的章节
        for chapter_num, chapter in file_chapters.items():
            if chapter_num not in checkpoint_chapters:
                if "chapters" not in updates:
                    updates["chapters"] = dict(checkpoint_chapters)
                updates["chapters"][chapter_num] = chapter
                print(f"  📖 发现新章节: 第 {chapter_num} 章")
        
        # 同步 chapters_plan：确保已生成的章节计划被识别
        file_plans = file_state.chapters_plan or {}
        checkpoint_plans = checkpoint_state.get("chapters_plan", {}) or {}
        
        for plan_num, plan in file_plans.items():
            if plan_num not in checkpoint_plans:
                if "chapters_plan" not in updates:
                    updates["chapters_plan"] = dict(checkpoint_plans)
                updates["chapters_plan"][plan_num] = plan
                print(f"  📋 发现新章节计划: 第 {plan_num} 章")
        
        # 同步基础数据（world, theme_conflict, characters, outline）
        # 如果文件存在但检查点中为空
        if file_state.world and not checkpoint_state.get("world"):
            updates["world"] = file_state.world
            print(f"  🌍 同步世界观")
        
        if file_state.theme_conflict and not checkpoint_state.get("theme_conflict"):
            updates["theme_conflict"] = file_state.theme_conflict
            print(f"  🎭 同步主题冲突")
        
        if file_state.characters and not checkpoint_state.get("characters"):
            updates["characters"] = file_state.characters
            print(f"  👥 同步角色配置")
        
        if file_state.outline and not checkpoint_state.get("outline"):
            updates["outline"] = file_state.outline
            print(f"  📑 同步大纲")
        
        # 同步 completed_steps：基于文件状态更新已完成步骤
        file_completed = set(file_state.completed_steps or [])
        checkpoint_completed = set(checkpoint_state.get("completed_steps", []) or [])
        
        new_completed = file_completed - checkpoint_completed
        if new_completed:
            updates["completed_steps"] = list(file_completed | checkpoint_completed)
            print(f"  ✅ 同步已完成步骤: {new_completed}")
        
        return updates
    
    def _merge_incomplete_chapters_from_scenes(self) -> None:
        """检查并合并未完成的章节（从场景文件）
        
        遍历项目目录，查找存在场景文件但缺少章节文件的情况，
        自动合并场景为完整章节。
        
        这是一个额外的安全措施，确保即使检查点同步失败，
        场景文件也能被正确合并。
        
        开发者: jamesenh, 开发时间: 2025-11-30
        """
        import re
        
        if not os.path.exists(self.config.chapters_dir):
            return
        
        # 扫描场景文件，按章节分组
        scene_pattern = re.compile(r"scene_(\d{3})_(\d{3})\.json")
        scenes_by_chapter: Dict[int, List[int]] = {}
        
        for filename in os.listdir(self.config.chapters_dir):
            match = scene_pattern.match(filename)
            if match:
                chapter_num = int(match.group(1))
                scene_num = int(match.group(2))
                if chapter_num not in scenes_by_chapter:
                    scenes_by_chapter[chapter_num] = []
                scenes_by_chapter[chapter_num].append(scene_num)
        
        # 加载大纲以获取章节计划
        outline = self.load_json(self.config.outline_file, Outline)
        if not outline:
            return
        
        # 检查每个有场景文件的章节
        for chapter_num, scene_nums in scenes_by_chapter.items():
            chapter_file = os.path.join(
                self.config.chapters_dir, 
                f"chapter_{chapter_num:03d}.json"
            )
            
            # 如果章节文件已存在，跳过
            if os.path.exists(chapter_file):
                continue
            
            # 加载章节计划
            plan_file = os.path.join(
                self.config.chapters_dir,
                f"chapter_{chapter_num:03d}_plan.json"
            )
            if not os.path.exists(plan_file):
                continue
            
            plan = self.load_json(plan_file, ChapterPlan)
            if not plan:
                continue
            
            # 检查是否所有场景都已生成
            expected_scenes = {s.scene_number for s in plan.scenes}
            existing_scenes = set(scene_nums)
            
            if expected_scenes <= existing_scenes:
                # 所有场景都存在，合并为章节
                print(f"🔧 发现未合并的章节: 第 {chapter_num} 章，正在合并...")
                
                scenes = []
                for scene_plan in plan.scenes:
                    scene_file = os.path.join(
                        self.config.chapters_dir,
                        f"scene_{chapter_num:03d}_{scene_plan.scene_number:03d}.json"
                    )
                    scene = self.load_json(scene_file, GeneratedScene)
                    if scene:
                        scenes.append(scene)
                
                if scenes:
                    chapter = GeneratedChapter(
                        chapter_number=chapter_num,
                        chapter_title=plan.chapter_title,
                        scenes=scenes,
                        total_words=sum(s.word_count for s in scenes)
                    )
                    self.save_json(chapter, chapter_file)
                    print(f"  ✅ 第 {chapter_num} 章已合并: {chapter_file}")
    
    def close(self):
        """关闭资源（预留接口，Mem0 不需要显式关闭）"""
        pass

    # ==================== 状态查询和回滚方法 ====================
    # 开发者: jamesenh, 开发时间: 2025-11-30
    
    def get_project_state(self) -> Dict[str, Any]:
        """获取项目完整状态
        
        用于 CLI 展示项目当前进度和可回滚点
        
        Returns:
            包含以下结构的字典：
            {
                "steps": {
                    "world": {"exists": True, "file": "world.json"},
                    "theme_conflict": {"exists": True, "file": "theme_conflict.json"},
                    "characters": {"exists": True, "file": "characters.json"},
                    "outline": {"exists": True, "file": "outline.json", "chapters": 12},
                },
                "chapters": {
                    1: {"plan": True, "scenes": [1,2,3,4], "complete": True, "word_count": 3200},
                    2: {"plan": True, "scenes": [1,2,3], "complete": False},
                    3: {"plan": True, "scenes": [], "complete": False},
                },
                "checkpoint_exists": True
            }
        """
        import re
        
        state = {
            "steps": {},
            "chapters": {},
            "checkpoint_exists": False
        }
        
        # 检查基础步骤文件
        state["steps"]["world"] = {
            "exists": os.path.exists(self.config.world_file),
            "file": "world.json"
        }
        state["steps"]["theme_conflict"] = {
            "exists": os.path.exists(self.config.theme_conflict_file),
            "file": "theme_conflict.json"
        }
        state["steps"]["characters"] = {
            "exists": os.path.exists(self.config.characters_file),
            "file": "characters.json"
        }
        
        outline_exists = os.path.exists(self.config.outline_file)
        state["steps"]["outline"] = {
            "exists": outline_exists,
            "file": "outline.json",
            "chapters": 0
        }
        
        if outline_exists:
            outline = self.load_json(self.config.outline_file, Outline)
            if outline:
                state["steps"]["outline"]["chapters"] = len(outline.chapters)
        
        # 检查检查点数据库
        checkpoint_db = os.path.join(self.project_dir, "workflow_checkpoints.db")
        state["checkpoint_exists"] = os.path.exists(checkpoint_db)
        
        # 检查章节状态
        if os.path.exists(self.config.chapters_dir):
            # 收集所有章节计划
            plan_pattern = re.compile(r"chapter_(\d{3})_plan\.json")
            # 收集所有场景文件
            scene_pattern = re.compile(r"scene_(\d{3})_(\d{3})\.json")
            # 收集所有章节文件
            chapter_pattern = re.compile(r"chapter_(\d{3})\.json")
            
            plans = {}
            scenes_by_chapter: Dict[int, List[int]] = {}
            completed_chapters = {}
            
            for filename in os.listdir(self.config.chapters_dir):
                # 章节计划
                plan_match = plan_pattern.match(filename)
                if plan_match:
                    chapter_num = int(plan_match.group(1))
                    plan_file = os.path.join(self.config.chapters_dir, filename)
                    plan = self.load_json(plan_file, ChapterPlan)
                    if plan:
                        plans[chapter_num] = len(plan.scenes)
                    continue
                
                # 场景文件
                scene_match = scene_pattern.match(filename)
                if scene_match:
                    chapter_num = int(scene_match.group(1))
                    scene_num = int(scene_match.group(2))
                    if chapter_num not in scenes_by_chapter:
                        scenes_by_chapter[chapter_num] = []
                    scenes_by_chapter[chapter_num].append(scene_num)
                    continue
                
                # 完整章节文件
                chapter_match = chapter_pattern.match(filename)
                if chapter_match:
                    chapter_num = int(chapter_match.group(1))
                    chapter_file = os.path.join(self.config.chapters_dir, filename)
                    chapter = self.load_json(chapter_file, GeneratedChapter)
                    if chapter:
                        completed_chapters[chapter_num] = {
                            "word_count": chapter.total_words,
                            "scene_count": len(chapter.scenes)
                        }
            
            # 构建章节状态
            all_chapter_nums = set(plans.keys()) | set(scenes_by_chapter.keys()) | set(completed_chapters.keys())
            
            for ch_num in sorted(all_chapter_nums):
                chapter_state = {
                    "plan": ch_num in plans,
                    "plan_scenes": plans.get(ch_num, 0),
                    "scenes": sorted(scenes_by_chapter.get(ch_num, [])),
                    "complete": ch_num in completed_chapters,
                    "word_count": completed_chapters.get(ch_num, {}).get("word_count", 0)
                }
                state["chapters"][ch_num] = chapter_state
        
        return state
    
    def _delete_checkpoint_db(self) -> bool:
        """删除 LangGraph 检查点数据库
        
        删除后，下次运行时系统会从文件状态自动重建
        
        Returns:
            是否成功删除
        """
        checkpoint_db = os.path.join(self.project_dir, "workflow_checkpoints.db")
        if os.path.exists(checkpoint_db):
            try:
                os.remove(checkpoint_db)
                print(f"  🗑️ 已删除检查点数据库: {checkpoint_db}")
                return True
            except Exception as e:
                print(f"  ⚠️ 删除检查点数据库失败: {e}")
                return False
        return True
    
    def _update_chapter_memory_file(self, chapter_gte: int) -> int:
        """更新章节记忆文件，移除指定章节及之后的条目
        
        Args:
            chapter_gte: 移除章节号 >= 此值的条目
            
        Returns:
            移除的条目数量
        """
        entries = self._load_chapter_memory_entries()
        original_count = len(entries)
        
        filtered_entries = [e for e in entries if e.chapter_number < chapter_gte]
        removed_count = original_count - len(filtered_entries)
        
        if removed_count > 0:
            self._save_chapter_memory_entries(filtered_entries)
            print(f"  🗑️ 从章节记忆中移除 {removed_count} 条条目")
        
        return removed_count
    
    def _update_consistency_reports(self, chapter_gte: int) -> int:
        """更新一致性报告文件，移除指定章节及之后的条目
        
        Args:
            chapter_gte: 移除章节号 >= 此值的条目
            
        Returns:
            移除的条目数量
        """
        if not os.path.exists(self.config.consistency_report_file):
            return 0
        
        try:
            with open(self.config.consistency_report_file, 'r', encoding='utf-8') as f:
                reports = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return 0
        
        original_count = len(reports)
        filtered_reports = [r for r in reports if r.get("chapter_number", 0) < chapter_gte]
        removed_count = original_count - len(filtered_reports)
        
        if removed_count > 0:
            with open(self.config.consistency_report_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_reports, f, ensure_ascii=False, indent=2)
            print(f"  🗑️ 从一致性报告中移除 {removed_count} 条条目")
        
        return removed_count
    
    def rollback_to_step(self, step_name: str) -> Dict[str, Any]:
        """回滚到指定步骤之前
        
        步骤顺序: world -> theme_conflict -> characters -> outline -> chapters_plan
        
        Args:
            step_name: 要回滚到的步骤名称
            
        Returns:
            回滚结果：{"deleted_files": [...], "deleted_memories": int}
        """
        import shutil
        
        # 步骤顺序定义
        step_order = ["world", "theme_conflict", "characters", "outline", "chapters_plan"]
        
        if step_name not in step_order:
            raise ValueError(f"无效的步骤名称: {step_name}，有效值: {step_order}")
        
        step_index = step_order.index(step_name)
        steps_to_delete = step_order[step_index:]
        
        result = {
            "deleted_files": [],
            "deleted_memories": 0
        }
        
        print(f"🔄 回滚到步骤 '{step_name}' 之前...")
        
        # 删除各步骤对应的文件
        step_files = {
            "world": self.config.world_file,
            "theme_conflict": self.config.theme_conflict_file,
            "characters": self.config.characters_file,
            "outline": self.config.outline_file,
        }
        
        for step in steps_to_delete:
            if step in step_files:
                filepath = step_files[step]
                if os.path.exists(filepath):
                    os.remove(filepath)
                    result["deleted_files"].append(filepath)
                    print(f"  🗑️ 已删除: {filepath}")
        
        # 如果回滚到 outline 或更早，需要删除整个 chapters 目录
        if step_index <= step_order.index("outline"):
            if os.path.exists(self.config.chapters_dir):
                # 统计文件数量
                file_count = len([f for f in os.listdir(self.config.chapters_dir) if os.path.isfile(os.path.join(self.config.chapters_dir, f))])
                shutil.rmtree(self.config.chapters_dir)
                os.makedirs(self.config.chapters_dir, exist_ok=True)
                result["deleted_files"].append(f"chapters/* ({file_count} 文件)")
                print(f"  🗑️ 已清空 chapters 目录 ({file_count} 文件)")
            
            # 清理章节记忆
            self._update_chapter_memory_file(chapter_gte=1)
            
            # 清理一致性报告
            self._update_consistency_reports(chapter_gte=1)
            
            # 清理 Mem0 记忆
            if self.mem0_manager:
                try:
                    deleted = self.mem0_manager.delete_memories_by_filter(chapter_index_gte=1)
                    result["deleted_memories"] = deleted
                except Exception as e:
                    print(f"  ⚠️ 清理 Mem0 记忆失败: {e}")
        
        # 删除检查点数据库
        self._delete_checkpoint_db()
        
        print(f"✅ 回滚完成: 删除 {len(result['deleted_files'])} 个文件/目录，{result['deleted_memories']} 条记忆")
        return result
    
    def rollback_to_chapter(self, chapter_number: int) -> Dict[str, Any]:
        """回滚到指定章节开始之前
        
        删除指定章节及之后的所有章节和场景文件
        
        Args:
            chapter_number: 章节号（删除此章节及之后的所有内容）
            
        Returns:
            回滚结果：{"deleted_files": [...], "deleted_memories": int}
        """
        import re
        
        result = {
            "deleted_files": [],
            "deleted_memories": 0
        }
        
        print(f"🔄 回滚到第 {chapter_number} 章之前...")
        
        if not os.path.exists(self.config.chapters_dir):
            print("  ⚠️ chapters 目录不存在")
            return result
        
        # 定义文件匹配模式
        chapter_pattern = re.compile(r"chapter_(\d{3})(?:_plan)?\.json")
        scene_pattern = re.compile(r"scene_(\d{3})_(\d{3})\.json")
        revision_pattern = re.compile(r"chapter_(\d{3})_revision\.json")
        revised_txt_pattern = re.compile(r"chapter_(\d{3})_revised\.txt")
        
        files_to_delete = []
        
        for filename in os.listdir(self.config.chapters_dir):
            filepath = os.path.join(self.config.chapters_dir, filename)
            
            # 检查章节文件和计划文件
            chapter_match = chapter_pattern.match(filename)
            if chapter_match:
                ch_num = int(chapter_match.group(1))
                if ch_num >= chapter_number:
                    files_to_delete.append(filepath)
                continue
            
            # 检查场景文件
            scene_match = scene_pattern.match(filename)
            if scene_match:
                ch_num = int(scene_match.group(1))
                if ch_num >= chapter_number:
                    files_to_delete.append(filepath)
                continue
            
            # 检查修订文件
            revision_match = revision_pattern.match(filename)
            if revision_match:
                ch_num = int(revision_match.group(1))
                if ch_num >= chapter_number:
                    files_to_delete.append(filepath)
                continue
            
            # 检查修订文本文件
            revised_match = revised_txt_pattern.match(filename)
            if revised_match:
                ch_num = int(revised_match.group(1))
                if ch_num >= chapter_number:
                    files_to_delete.append(filepath)
        
        # 删除文件
        for filepath in files_to_delete:
            try:
                os.remove(filepath)
                result["deleted_files"].append(filepath)
                print(f"  🗑️ 已删除: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"  ⚠️ 删除失败 {filepath}: {e}")
        
        # 清理章节记忆
        self._update_chapter_memory_file(chapter_gte=chapter_number)
        
        # 清理一致性报告
        self._update_consistency_reports(chapter_gte=chapter_number)
        
        # 清理 Mem0 记忆
        if self.mem0_manager:
            try:
                deleted = self.mem0_manager.delete_memories_by_filter(chapter_index_gte=chapter_number)
                result["deleted_memories"] = deleted
            except Exception as e:
                print(f"  ⚠️ 清理 Mem0 记忆失败: {e}")
        
        # 删除检查点数据库
        self._delete_checkpoint_db()
        
        print(f"✅ 回滚完成: 删除 {len(result['deleted_files'])} 个文件，{result['deleted_memories']} 条记忆")
        return result
    
    def rollback_to_scene(self, chapter_number: int, scene_number: int) -> Dict[str, Any]:
        """回滚到指定场景开始之前
        
        删除指定章节中指定场景及之后的所有场景文件，
        同时删除章节合并文件和所有后续章节
        
        Args:
            chapter_number: 章节号
            scene_number: 场景号（删除此场景及之后的所有内容）
            
        Returns:
            回滚结果：{"deleted_files": [...], "deleted_memories": int}
        """
        import re
        
        result = {
            "deleted_files": [],
            "deleted_memories": 0
        }
        
        print(f"🔄 回滚到第 {chapter_number} 章第 {scene_number} 场景之前...")
        
        if not os.path.exists(self.config.chapters_dir):
            print("  ⚠️ chapters 目录不存在")
            return result
        
        # 定义文件匹配模式
        chapter_pattern = re.compile(r"chapter_(\d{3})\.json")
        chapter_plan_pattern = re.compile(r"chapter_(\d{3})_plan\.json")
        scene_pattern = re.compile(r"scene_(\d{3})_(\d{3})\.json")
        revision_pattern = re.compile(r"chapter_(\d{3})_revision\.json")
        
        files_to_delete = []
        
        for filename in os.listdir(self.config.chapters_dir):
            filepath = os.path.join(self.config.chapters_dir, filename)
            
            # 检查章节文件（合并后的完整章节）
            chapter_match = chapter_pattern.match(filename)
            if chapter_match:
                ch_num = int(chapter_match.group(1))
                # 删除当前章节及之后的章节文件
                if ch_num >= chapter_number:
                    files_to_delete.append(filepath)
                continue
            
            # 检查章节计划文件
            plan_match = chapter_plan_pattern.match(filename)
            if plan_match:
                ch_num = int(plan_match.group(1))
                # 只删除后续章节的计划，当前章节计划保留
                if ch_num > chapter_number:
                    files_to_delete.append(filepath)
                continue
            
            # 检查场景文件
            scene_match = scene_pattern.match(filename)
            if scene_match:
                ch_num = int(scene_match.group(1))
                sc_num = int(scene_match.group(2))
                
                # 删除后续章节的所有场景
                if ch_num > chapter_number:
                    files_to_delete.append(filepath)
                # 删除当前章节中 >= scene_number 的场景
                elif ch_num == chapter_number and sc_num >= scene_number:
                    files_to_delete.append(filepath)
                continue
            
            # 检查修订文件
            revision_match = revision_pattern.match(filename)
            if revision_match:
                ch_num = int(revision_match.group(1))
                if ch_num >= chapter_number:
                    files_to_delete.append(filepath)
        
        # 删除文件
        for filepath in files_to_delete:
            try:
                os.remove(filepath)
                result["deleted_files"].append(filepath)
                print(f"  🗑️ 已删除: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"  ⚠️ 删除失败 {filepath}: {e}")
        
        # 清理章节记忆（从当前章节开始清理）
        self._update_chapter_memory_file(chapter_gte=chapter_number)
        
        # 清理一致性报告
        self._update_consistency_reports(chapter_gte=chapter_number)
        
        # 清理 Mem0 记忆（精确到场景）
        if self.mem0_manager:
            try:
                deleted = self.mem0_manager.delete_memories_by_filter(
                    chapter_index_gte=chapter_number,
                    scene_index_gte=scene_number,
                    target_chapter_for_scene=chapter_number
                )
                result["deleted_memories"] = deleted
            except Exception as e:
                print(f"  ⚠️ 清理 Mem0 记忆失败: {e}")
        
        # 删除检查点数据库
        self._delete_checkpoint_db()
        
        print(f"✅ 回滚完成: 删除 {len(result['deleted_files'])} 个文件，{result['deleted_memories']} 条记忆")
        return result

    def _maybe_use_existing(self, filepath: str, model_class, force: bool, entity_name: str):
        """
        检查是否已有生成结果
        force 为 False 时，若存在合法 JSON 则直接复用
        """
        if force:
            return None

        if not os.path.exists(filepath):
            return None

        try:
            existing = self.load_json(filepath, model_class)
        except Exception as exc:
            print(f"⚠️ 已存在的{entity_name}无法解析，将重新生成。原因: {exc}")
            return None

        if existing:
            print(f"⏭️ 检测到{entity_name}已生成，跳过本次生成：{filepath}")
        return existing

    def step1_create_world(self, user_input: str, force: bool = False) -> WorldSetting:
        """
        步骤1: 创建世界观

        Args:
            user_input: 用户输入的世界设定描述

        Returns:
            WorldSetting对象
        """
        existing = self._maybe_use_existing(
            self.config.world_file, WorldSetting, force, "世界观"
        )
        if existing:
            return existing

        print("🌍 正在生成世界观...")
        world = generate_world(
            user_input,
            verbose=self.verbose,
            llm_config=self.config.world_chain_config.llm_config
        )
        self.save_json(world, self.config.world_file)
        print(f"✅ 世界观已保存: {self.config.world_file}")
        
        # 保存世界观状态到 Mem0
        self._save_entity_state("world", "main_world", 
                               f"世界名称：{world.world_name}，时代：{world.time_period}，社会制度：{world.social_system}")
        
        return world

    def step2_create_theme_conflict(self, user_input: str = "", force: bool = False) -> ThemeConflict:
        """
        步骤2: 创建主题冲突

        Args:
            user_input: 用户关于故事方向的描述

        Returns:
            ThemeConflict对象
        """
        existing = self._maybe_use_existing(
            self.config.theme_conflict_file, ThemeConflict, force, "主题冲突"
        )
        if existing:
            return existing

        print("📖 正在生成主题冲突...")
        world = self.load_json(self.config.world_file, WorldSetting)
        if not world:
            raise ValueError("世界观文件不存在，请先执行步骤1")

        theme_conflict = generate_theme_conflict(
            world,
            user_input,
            verbose=self.verbose,
            llm_config=self.config.theme_conflict_chain_config.llm_config
        )
        self.save_json(theme_conflict, self.config.theme_conflict_file)
        print(f"✅ 主题冲突已保存: {self.config.theme_conflict_file}")
        
        # 保存主题冲突状态到 Mem0
        self._save_entity_state("theme", "main_theme", 
                               f"核心主题：{theme_conflict.core_theme}，主要冲突：{theme_conflict.main_conflict}")
        
        return theme_conflict

    def step3_create_characters(self, force: bool = False) -> CharactersConfig:
        """
        步骤3: 创建角色

        Returns:
            CharactersConfig对象
        """
        existing = self._maybe_use_existing(
            self.config.characters_file, CharactersConfig, force, "角色设定"
        )
        if existing:
            return existing

        print("👥 正在生成角色...")
        world = self.load_json(self.config.world_file, WorldSetting)
        theme_conflict = self.load_json(self.config.theme_conflict_file, ThemeConflict)

        if not world or not theme_conflict:
            raise ValueError("世界观或主题冲突文件不存在，请先执行前置步骤")

        characters = generate_characters(
            world,
            theme_conflict,
            verbose=self.verbose,
            llm_config=self.config.characters_chain_config.llm_config
        )
        self.save_json(characters, self.config.characters_file)
        print(f"✅ 角色已保存: {self.config.characters_file}")
        
        # 初始化 Mem0 Agent Memory（为每个角色创建初始状态）
        print(f"💾 正在为角色初始化 Mem0 Agent Memory...")
        try:
            # 主角
            self.mem0_manager.add_entity_state(
                entity_id=characters.protagonist.name,
                entity_type="character",
                state_description=f"角色初始状态：{characters.protagonist.personality}。背景：{characters.protagonist.background}",
                chapter_index=0,
                story_timeline="故事开始",
            )
            # 反派
            if characters.antagonist:
                self.mem0_manager.add_entity_state(
                    entity_id=characters.antagonist.name,
                    entity_type="character",
                    state_description=f"角色初始状态：{characters.antagonist.personality}。背景：{characters.antagonist.background}",
                    chapter_index=0,
                    story_timeline="故事开始",
                )
            # 配角
            for character in characters.supporting_characters:
                self.mem0_manager.add_entity_state(
                    entity_id=character.name,
                    entity_type="character",
                    state_description=f"角色初始状态：{character.personality}。背景：{character.background}",
                    chapter_index=0,
                    story_timeline="故事开始",
                )
            print(f"✅ 已为 {1 + (1 if characters.antagonist else 0) + len(characters.supporting_characters)} 个角色初始化 Mem0 记忆")
        except Exception as e:
            print(f"⚠️ Mem0 角色初始化失败: {e}")
            raise
        
        return characters

    def step4_create_outline(self, num_chapters: int = 20, force: bool = False) -> Outline:
        """
        步骤4: 创建大纲

        Args:
            num_chapters: 预期章节数

        Returns:
            Outline对象
        """
        existing = self._maybe_use_existing(
            self.config.outline_file, Outline, force, "小说大纲"
        )
        if existing:
            return existing

        print("📋 正在生成大纲...")
        world = self.load_json(self.config.world_file, WorldSetting)
        theme_conflict = self.load_json(self.config.theme_conflict_file, ThemeConflict)
        characters = self.load_json(self.config.characters_file, CharactersConfig)

        if not all([world, theme_conflict, characters]):
            raise ValueError("缺少前置文件，请先执行前置步骤")

        # 类型断言,确保类型检查器知道这些变量不为None
        assert world is not None
        assert theme_conflict is not None
        assert characters is not None

        outline = generate_outline(
            world,
            theme_conflict,
            characters,
            num_chapters,
            verbose=self.verbose,
            llm_config=self.config.outline_chain_config.llm_config
        )
        self.save_json(outline, self.config.outline_file)
        print(f"✅ 大纲已保存: {self.config.outline_file}")
        
        # 保存大纲状态到 Mem0
        self._save_entity_state("outline", "main_outline", 
                               f"故事前提：{outline.story_premise[:200]}...")
        
        # 为每个章节保存状态
        for chapter in outline.chapters:
            self._save_entity_state("chapter_summary", f"chapter_{chapter.chapter_number}_summary", 
                                   f"第{chapter.chapter_number}章：{chapter.chapter_title} - {chapter.summary[:150]}...",
                                   chapter.chapter_number)
        
        return outline

    def step5_create_chapter_plan(self, chapter_number: Union[int, List[int], None] = None, force: bool = False) -> Union[ChapterPlan, List[ChapterPlan]]:
        """
        步骤5: 创建章节计划（支持单个或多个章节）

        Args:
            chapter_number: 章节编号或章节编号列表
            force: 是否强制重新生成，默认False

        Returns:
            单个ChapterPlan对象或ChapterPlan对象列表
        """
        # 统一处理为列表
        if chapter_number is None:
            chapter_numbers = None
        elif isinstance(chapter_number, int):
            chapter_numbers = [chapter_number]
        else:
            chapter_numbers = chapter_number

        # 加载共享数据
        world = self.load_json(self.config.world_file, WorldSetting)
        characters = self.load_json(self.config.characters_file, CharactersConfig)
        outline = self.load_json(self.config.outline_file, Outline)

        if not all([world, characters, outline]):
            raise ValueError("缺少前置文件，请先执行前置步骤")

        # 类型断言,确保类型检查器知道这些变量不为None
        assert world is not None
        assert characters is not None
        assert outline is not None

        if chapter_numbers is None:
            chapter_numbers = sorted(ch.chapter_number for ch in outline.chapters)

        results = []

        for num in chapter_numbers:
            plan_file = os.path.join(
                self.config.chapters_dir,
                f"chapter_{num:03d}_plan.json"
            )
            existing = self._maybe_use_existing(
                plan_file, ChapterPlan, force, f"第{num}章章节计划"
            )
            if existing:
                results.append(existing)
                continue

            print(f"📝 正在生成第{num}章的计划...")

            # 找到对应章节
            chapter_summary = None
            for ch in outline.chapters:
                if ch.chapter_number == num:
                    chapter_summary = ch
                    break

            if not chapter_summary:
                raise ValueError(f"章节{num}不存在于大纲中")

            self._ensure_chapter_dependencies_met(chapter_summary)

            dependency_payload = json.dumps(
                [dep.model_dump() for dep in chapter_summary.dependencies],
                ensure_ascii=False,
                indent=2
            ) if chapter_summary.dependencies else "[]"

            memory_payload = self._build_chapter_context_payload(num)

            chapter_plan = generate_chapter_plan(
                chapter_summary,
                world,
                characters,
                chapter_memory=memory_payload,
                chapter_dependencies=dependency_payload,
                verbose=self.verbose,
                llm_config=self.config.chapters_plan_chain_config.llm_config
            )

            # 保存章节计划
            self.save_json(chapter_plan, plan_file)
            print(f"✅ 第{num}章计划已保存: {plan_file}")
            
            # 保存章节计划状态到 Mem0
            self._save_entity_state("chapter_plan", f"chapter_{num}_plan", 
                                   f"第{num}章计划：{chapter_plan.chapter_title}，共{len(chapter_plan.scenes)}个场景",
                                   num)
            
            results.append(chapter_plan)

        # 根据输入类型返回结果
        return results[0] if isinstance(chapter_number, int) else results

    def step6_generate_chapter_text(self, chapter_number: int, force: bool = False) -> GeneratedChapter:
        """
        步骤6: 生成章节文本

        Args:
            chapter_number: 章节编号

        Returns:
            GeneratedChapter对象
        """
        text_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}.json"
        )

        if force:
            if os.path.exists(text_file):
                print(f"🔁 检测到第{chapter_number}章已有章节文本，将强制重新生成：{text_file}")
            else:
                print(f"🔁 将强制生成第{chapter_number}章的文本（无现有文件）：{text_file}")

        existing = self._maybe_use_existing(
            text_file, GeneratedChapter, force, f"第{chapter_number}章章节文本"
        )
        if existing:
            return existing

        print(f"✍️  正在生成第{chapter_number}章的文本...")
        world = self.load_json(self.config.world_file, WorldSetting)
        characters = self.load_json(self.config.characters_file, CharactersConfig)
        chapter_summary = self._get_chapter_summary(chapter_number)

        # step6开始前验证实际依赖满足情况
        if chapter_summary:
            self._ensure_chapter_dependencies_actually_met(chapter_summary)

        plan_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}_plan.json"
        )
        chapter_plan = self.load_json(plan_file, ChapterPlan)

        if not all([world, characters, chapter_plan]):
            raise ValueError("缺少前置文件，请先执行前置步骤")

        # 类型断言,确保类型检查器知道这些变量不为None
        assert world is not None
        assert characters is not None
        assert chapter_plan is not None

        # 生成各场景文本
        scenes = []
        chapter_context_payload = self._build_chapter_context_payload(chapter_number)
        previous_summary = self._initial_previous_summary(chapter_number, chapter_context_payload)
        scene_summaries = []

        for scene_plan in chapter_plan.scenes:
            print(f"  生成场景 {scene_plan.scene_number}...")

            # 检索场景记忆上下文
            scene_memory_context = None
            memory_file = os.path.join(
                self.project_dir,
                f"scene_{chapter_number}_{scene_plan.scene_number}_memory.json"
            )
            
            # 首先尝试加载已存在的记忆上下文
            if os.path.exists(memory_file):
                try:
                    raw_context = self.load_json(memory_file)
                    if isinstance(raw_context, dict):
                        scene_memory_context = SceneMemoryContext(**raw_context)
                        print(f"    📋 已加载场景{scene_plan.scene_number}的记忆上下文")
                except Exception as exc:
                    print(f"⚠️ 场景记忆上下文解析失败，将重新生成：{exc}")
            
            # 如果没有已存在的记忆上下文，则从 Mem0 检索生成
            if scene_memory_context is None:
                try:
                    print(f"    🧠 正在为场景{scene_plan.scene_number}检索记忆上下文...")
                    
                    # 从 Mem0 检索角色状态
                    entity_states = []
                    if scene_plan.characters:
                        entity_states = self.mem0_manager.get_entity_states_for_characters(
                            character_names=scene_plan.characters,
                            chapter_index=chapter_number,
                            scene_index=scene_plan.scene_number
                        )
                        print(f"    ✅ 已从 Mem0 检索到 {len(entity_states)} 个角色状态")
                    
                    # 从 Mem0 检索相关场景内容
                    relevant_memories = []
                    try:
                        # 使用场景目的作为查询
                        relevant_memories = self.mem0_manager.search_scene_content(
                            query=scene_plan.purpose,
                            chapter_index=None,  # 搜索所有章节
                            limit=5
                        )
                        print(f"    ✅ 已从 Mem0 检索到 {len(relevant_memories)} 个相关记忆")
                    except Exception as search_exc:
                        print(f"    ⚠️ Mem0 场景内容搜索失败: {search_exc}")
                    
                    # 构建场景记忆上下文
                    scene_memory_context = SceneMemoryContext(
                        project_id=self.project_name,
                        chapter_index=chapter_number,
                        scene_index=scene_plan.scene_number,
                        entity_states=entity_states,
                        relevant_memories=relevant_memories,
                        timeline_context=None,
                        retrieval_timestamp=datetime.now()
                    )
                    
                    # 保存记忆上下文到文件
                    try:
                        with open(memory_file, "w", encoding="utf-8") as f:
                            json.dump(scene_memory_context.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)
                        print(f"    📋 记忆上下文已保存: {memory_file}")
                    except Exception as save_exc:
                        print(f"    ⚠️ 保存记忆上下文失败: {save_exc}")
                    
                except Exception as exc:
                    print(f"⚠️ 场景记忆上下文生成失败，将忽略：{exc}")
                    scene_memory_context = None

            # 检索用户偏好（从 Mem0）并注入到 chapter_context
            user_preferences_text = ""
            try:
                preferences = self.mem0_manager.search_user_preferences(
                    query="写作风格和偏好",
                    limit=5
                )
                if preferences:
                    user_preferences_text = "\n\n【用户写作偏好】\n"
                    user_preferences_text += "以下是用户设定的写作偏好，请在生成时参考：\n"
                    for pref in preferences:
                        memory_content = pref.get('memory', '')
                        if memory_content:
                            user_preferences_text += f"- {memory_content}\n"
            except Exception as e:
                print(f"⚠️ 检索用户偏好失败: {e}")
            
            # 将用户偏好附加到 chapter_context
            enhanced_chapter_context = chapter_context_payload
            if user_preferences_text:
                enhanced_chapter_context = chapter_context_payload + user_preferences_text
            
            scene = generate_scene_text(
                scene_plan,
                world,
                characters,
                previous_summary,
                chapter_context=enhanced_chapter_context,
                scene_memory_context=scene_memory_context,
                verbose=self.verbose,
                llm_config=self.config.scene_text_chain_config.llm_config
            )
            scenes.append(scene)

            # 保存场景内容到 Mem0
            self._save_scene_content(scene.content, chapter_number, scene.scene_number)

            # 更新前文概要
            print(f"    📝 正在生成场景{scene.scene_number}摘要...")
            scene_summary = self._summarize_scene_safe(scene)
            scene_summaries.append(f"场景{scene.scene_number}: {scene_summary}")
            previous_summary = scene_summary
            print(f"    ✅ 场景{scene.scene_number}摘要生成完成")

        aggregated_summary = self._summarize_chapter_safe(scenes)
        print(f"📋 第{chapter_number}章聚合摘要生成完成")

        # 组装章节
        total_words = sum(scene.word_count for scene in scenes)
        chapter = GeneratedChapter(
            chapter_number=chapter_number,
            chapter_title=chapter_plan.chapter_title,
            scenes=scenes,
            total_words=total_words
        )

        # 保存章节文本
        self.save_json(chapter, text_file)
        print(f"✅ 章节文本已保存: {text_file}")
        
        # 保存章节状态到 Mem0
        self._save_entity_state("chapter_text", f"chapter_{chapter_number}_text", 
                               f"第{chapter_number}章完成：{chapter.chapter_title}，共{len(scenes)}个场景，{total_words}字",
                               chapter_number)

        # 更新章节记忆
        print(f"🧠 正在为第{chapter_number}章生成记忆条目...")
        try:
            memory_entry = generate_chapter_memory_entry(
                chapter=chapter,
                outline_summary=chapter_summary,
                scene_summaries=scene_summaries,
                aggregated_summary=aggregated_summary,
                verbose=self.verbose,
                llm_config=self.config.chapter_memory_chain_config.llm_config
            )
            self._append_chapter_memory_entry(memory_entry)
            print(f"✅ 第{chapter_number}章记忆条目已保存")
            
            # 更新角色状态到 Mem0（从 chapter_memory_entry 中提取，包含故事时间线）
            if memory_entry.character_states:
                print(f"💾 正在更新角色状态到 Mem0...")
                for character_name, state_description in memory_entry.character_states.items():
                    try:
                        self.mem0_manager.add_entity_state(
                            entity_id=character_name,
                            entity_type="character",
                            state_description=state_description,
                            chapter_index=chapter_number,
                            story_timeline=memory_entry.timeline_anchor,
                        )
                    except Exception as char_exc:
                        print(f"⚠️ 更新角色 {character_name} 状态失败: {char_exc}")
                print(f"✅ 已更新 {len(memory_entry.character_states)} 个角色状态到 Mem0")
            
        except Exception as exc:
            print(f"⚠️ 章节记忆生成失败：{exc}")

        # 一致性检测
        chapter_text = self._collect_chapter_text(chapter)
        context_payload = self._build_consistency_context(chapter_number, chapter_summary)
        print(f"🔍 正在对第{chapter_number}章进行一致性检测...")
        try:
            report = run_consistency_check(
                chapter_number=chapter_number,
                context_payload=context_payload,
                chapter_text=chapter_text,
                verbose=self.verbose,
                llm_config=self.config.consistency_chain_config.llm_config
            )
            self._record_consistency_report(report)
            
            # 输出一致性检测结果
            issue_count = len(report.issues)
            if issue_count == 0:
                print(f"✅ 第{chapter_number}章一致性检测通过，未发现问题")
            else:
                severity_summary = {}
                for issue in report.issues:
                    severity = issue.severity
                    severity_summary[severity] = severity_summary.get(severity, 0) + 1
                
                severity_info = ", ".join([f"{k}({v})" for k, v in severity_summary.items()])
                print(f"⚠️ 第{chapter_number}章一致性检测发现{issue_count}个问题: {severity_info}")
                
                # 显示包含修复建议的问题数量
                auto_fixable = sum(1 for issue in report.issues if issue.fix_instructions and issue.fix_instructions.strip())
                if auto_fixable > 0:
                    print(f"🔧 其中{auto_fixable}个问题包含修复建议")
            
            # 根据 revision_policy 处理修订阶段
            chapter = self._handle_revision_stage(report, chapter)
        except Exception as exc:
            print(f"⚠️ 一致性检测失败：{exc}")

        return chapter

    def _check_pending_revisions(self) -> List[int]:
        """
        检查是否有待确认的修订

        Returns:
            待确认章节编号列表
        """
        pending_chapters = []
        if not os.path.exists(self.config.chapters_dir):
            return pending_chapters

        for filename in os.listdir(self.config.chapters_dir):
            if filename.endswith("_revision.json"):
                filepath = os.path.join(self.config.chapters_dir, filename)
                try:
                    revision_status = self.load_json(filepath, RevisionStatus)
                    if revision_status and revision_status.status == "pending":
                        pending_chapters.append(revision_status.chapter_number)
                except Exception:
                    pass  # 忽略无法解析的文件
        
        return sorted(pending_chapters)

    def generate_all_chapters(self, chapter_numbers: Optional[List[int]] = None, force: bool = False):
        """生成所有章节"""
        outline = self.load_json(self.config.outline_file, Outline)
        if not outline:
            raise ValueError("大纲文件不存在，请先执行步骤4")

        if chapter_numbers is None:
            target_numbers = [ch.chapter_number for ch in outline.chapters]
        else:
            valid_numbers = {ch.chapter_number for ch in outline.chapters}
            for num in chapter_numbers:
                if num not in valid_numbers:
                    raise ValueError(f"章节{num}不存在于大纲中")
            target_numbers = sorted(chapter_numbers)

        total = len(target_numbers)
        for idx, num in enumerate(target_numbers, start=1):
            # 在 manual_confirm 模式下检查待确认修订
            if self.config.revision_policy == "manual_confirm":
                pending_revisions = self._check_pending_revisions()
                # 检查是否有编号小于当前章节的待确认修订
                blocking_revisions = [ch for ch in pending_revisions if ch < num]
                if blocking_revisions:
                    blocking_list = ", ".join(map(str, blocking_revisions))
                    raise RuntimeError(
                        f"⏸️ [manual_confirm] 无法继续生成第{num}章：存在待确认的修订章节 [{blocking_list}]。\n"
                        f"请先调用 apply_revision 处理这些章节的修订，或切换 revision_policy。"
                    )

            print(f"\n{'='*60}")
            print(f"[{idx}/{total}] 生成第{num}章")
            print(f"{'='*60}")
            try:
                self.step6_generate_chapter_text(chapter_number=num, force=force)
            except Exception as exc:
                print(f"✗ 第{num}章生成失败：{exc}")
                # 失败后继续生成下一章（可选，视业务需求而定）

    def apply_revision(self, chapter_number: int, rebuild_memory: bool = True):
        """
        应用待确认的修订（将修订候选应用到章节 JSON）

        Args:
            chapter_number: 章节编号
            rebuild_memory: 是否重建章节记忆
        """
        revision_status_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}_revision.json"
        )
        
        if not os.path.exists(revision_status_file):
            raise ValueError(f"第{chapter_number}章没有待确认的修订")
        
        # 读取修订状态
        revision_status = self.load_json(revision_status_file, RevisionStatus)
        if not revision_status:
            raise ValueError(f"无法解析第{chapter_number}章的修订状态文件")
        
        if revision_status.status != "pending":
            print(f"⚠️ 第{chapter_number}章修订状态为 {revision_status.status}，非 pending 状态")
            return
        
        if not revision_status.revised_chapter:
            raise ValueError(f"第{chapter_number}章修订状态中缺少 revised_chapter")
        
        print(f"📝 正在应用第{chapter_number}章的修订...")
        
        # 将修订候选覆盖到章节 JSON
        chapter_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}.json"
        )
        self.save_json(revision_status.revised_chapter, chapter_file)
        print(f"✅ 第{chapter_number}章修订已应用到 chapter JSON")
        
        # 更新修订状态为 accepted
        revision_status.status = "accepted"
        revision_status.decision_at = datetime.now().isoformat()
        self.save_json(revision_status, revision_status_file)
        print(f"✅ 修订状态已更新为 accepted")
        
        # 可选：重建章节记忆
        if rebuild_memory:
            try:
                print(f"🧠 正在重建第{chapter_number}章的记忆条目...")
                # 读取大纲和角色配置
                outline = self.load_json(self.config.outline_file, Outline)
                if not outline:
                    print(f"⚠️ 大纲文件不存在，跳过记忆重建")
                    return
                
                chapter_summary_list = [ch for ch in outline.chapters if ch.chapter_number == chapter_number]
                if not chapter_summary_list:
                    print(f"⚠️ 大纲中未找到第{chapter_number}章，跳过记忆重建")
                    return
                chapter_summary = chapter_summary_list[0]
                
                # 生成场景摘要（简化版，实际可能需要更复杂的逻辑）
                chapter = revision_status.revised_chapter
                scene_summaries = [
                    f"场景{scene.scene_number}: {scene.content[:100]}..."
                    for scene in chapter.scenes
                ]
                aggregated_summary = f"{chapter.chapter_title} - {len(chapter.scenes)}个场景"
                
                # 生成章节记忆
                from novelgen.runtime.memory import generate_chapter_memory_entry
                memory_entry = generate_chapter_memory_entry(
                    chapter=chapter,
                    outline_summary=chapter_summary,
                    scene_summaries=scene_summaries,
                    aggregated_summary=aggregated_summary,
                    verbose=self.verbose,
                    llm_config=self.config.chapter_memory_chain_config.llm_config
                )
                self._append_chapter_memory_entry(memory_entry)
                print(f"✅ 第{chapter_number}章记忆条目已重建")
            except Exception as exc:
                print(f"⚠️ 重建章节记忆失败：{exc}")

    def export_chapter(self, chapter_number: int, output_path: Optional[str] = None):
        """
        导出单个章节为txt文件

        Args:
            chapter_number: 章节编号
            output_path: 输出文件路径（可选）。如果不指定，默认保存到 chapters/chapter_XXX.txt
        """
        # 加载章节数据
        chapter_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}.json"
        )
        chapter = self.load_json(chapter_file, GeneratedChapter)
        if not chapter:
            raise ValueError(f"章节 {chapter_number} 不存在，请先生成章节")

        # 确定输出路径
        if output_path is None:
            output_path = os.path.join(
                self.config.chapters_dir,
                f"chapter_{chapter_number:03d}.txt"
            )

        # 导出
        export_chapter_to_txt(chapter, output_path)

    def export_all_chapters(self, output_path: Optional[str] = None):
        """
        导出所有章节为一个txt文件

        Args:
            output_path: 输出文件路径（可选）。如果不指定，默认保存到项目根目录的 {project_name}_full.txt
        """
        # 确定输出路径
        if output_path is None:
            output_path = os.path.join(
                self.project_dir,
                f"{self.project_name}_full.txt"
            )

        # 导出
        export_all_chapters_to_txt(self.project_dir, output_path)

    def cleanup(self):
        """清理资源，关闭所有连接
        
        在程序退出前调用，确保：
        1. Mem0/ChromaDB 客户端正确关闭
        2. SQLite 连接关闭
        3. 后台线程终止
        
        开发者: jamesenh, 开发时间: 2025-11-30
        """
        _debug_log("cleanup() 开始")
        
        # 1. 关闭 Mem0 管理器
        if self.mem0_manager is not None:
            _debug_log("关闭 Mem0 管理器...")
            start = time.time()
            try:
                self.mem0_manager.close()
                _debug_log(f"Mem0 关闭完成，耗时 {time.time() - start:.2f}s")
            except Exception as e:
                _debug_log(f"Mem0 关闭失败: {e}")
        
        # 2. 关闭工作流（SQLite 连接）
        if self.workflow is not None:
            _debug_log("关闭工作流...")
            start = time.time()
            try:
                # LangGraph 的 checkpointer 可能持有 SQLite 连接
                # 尝试获取并关闭
                if hasattr(self.workflow, 'checkpointer'):
                    checkpointer = self.workflow.checkpointer
                    if hasattr(checkpointer, 'conn'):
                        _debug_log("关闭 SQLite 连接...")
                        checkpointer.conn.close()
                        _debug_log("SQLite 连接已关闭")
                _debug_log(f"工作流关闭完成，耗时 {time.time() - start:.2f}s")
            except Exception as e:
                _debug_log(f"工作流关闭失败: {e}")
        
        _debug_log("cleanup() 完成")
