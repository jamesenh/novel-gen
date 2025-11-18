# 开发者: jamesenh, 开发时间: 2025-11-17

"""
编排器
协调整个小说生成流程
"""
import os
import json
from typing import Optional, Union, List, Dict, Any

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
from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager
from datetime import datetime


class NovelOrchestrator:
    """小说生成编排器"""

    def __init__(self, project_name: str, base_dir: str = "projects", verbose: bool = False):
        """初始化编排器

        Args:
            project_name: 项目名称
            base_dir: 项目基础目录
            verbose: 是否启用详细日志（显示提示词、响应时间、token使用情况）

        注意：
            - 持久化相关配置在实例化时读取；如需变更配置，请创建新的 NovelOrchestrator 实例。
        """
        self.project_name = project_name
        self.project_dir = os.path.join(base_dir, project_name)
        self.config = ProjectConfig(project_dir=self.project_dir)
        self.verbose = verbose

        # 创建项目目录
        os.makedirs(self.project_dir, exist_ok=True)
        os.makedirs(self.config.chapters_dir, exist_ok=True)

        # 初始化持久化管理器
        self.db_manager: Optional[DatabaseManager] = None
        self.vector_manager: Optional[VectorStoreManager] = None

        # 从配置中读取持久化设置（默认启用）
        persistence_enabled = getattr(self.config, "persistence_enabled", True)
        vector_store_enabled = getattr(self.config, "vector_store_enabled", True)

        if persistence_enabled:
            try:
                db_path = self.config.get_db_path()
                self.db_manager = DatabaseManager(db_path, enabled=True)
                if self.db_manager.is_enabled():
                    print(f"✅ 数据库持久化已启用: {db_path}")
                else:
                    print("⚠️ 数据库持久化初始化失败，将降级到非持久化模式")
            except Exception as e:
                print(f"⚠️ 数据库初始化异常，降级到非持久化模式: {e}")
                self.db_manager = DatabaseManager(":memory:", enabled=False)
        else:
            print("ℹ️ 已通过配置关闭数据库持久化（ProjectConfig.persistence_enabled=False）")

        if vector_store_enabled:
            try:
                vector_dir = self.config.get_vector_store_dir()
                embedding_config = getattr(self.config, "embedding_config", None)
                self.vector_manager = VectorStoreManager(
                    vector_dir, 
                    enabled=True,
                    embedding_config=embedding_config
                )
                if self.vector_manager.is_enabled():
                    print(f"✅ 向量存储已启用: {vector_dir}")
                    if embedding_config:
                        print(f"   使用 embedding 模型: {embedding_config.model_name}")
                else:
                    print("⚠️ 向量存储初始化失败，将降级到非持久化模式")
            except Exception as e:
                print(f"⚠️ 向量存储初始化异常，降级到非持久化模式: {e}")
                self.vector_manager = VectorStoreManager(":memory:", enabled=False)
        else:
            print("ℹ️ 已通过配置关闭向量存储（ProjectConfig.vector_store_enabled=False）")

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
            if dep.chapter_number is None:
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
                
                # 同步更新数据库快照
                print(f"💾 正在更新第{chapter_number}章的数据库快照...")
                self._save_entity_snapshot("chapter_text", f"chapter_{chapter_number}_text", 
                                          revised_chapter.model_dump(), chapter_number)
                
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
                
                # 更新向量存储：先删除旧记忆，再添加新记忆
                print(f"🔄 正在更新第{chapter_number}章的向量存储...")
                try:
                    # 删除该章节的旧向量记忆
                    self._delete_chapter_vector_memory(chapter_number)
                    # 添加修订后的新向量记忆
                    for scene in revised_chapter.scenes:
                        self._save_scene_content_to_vector(
                            scene.content, 
                            chapter_number, 
                            scene.scene_number
                        )
                    print(f"✅ 第{chapter_number}章向量存储已更新")
                except Exception as vec_exc:
                    print(f"⚠️ 更新向量存储失败：{vec_exc}")
                
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
        调用摘要链生成场景摘要，若失败则使用片段作为降级结果
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
    def _save_entity_snapshot(self, entity_type: str, entity_id: str, state_data: Dict[str, Any], 
                          chapter_index: Optional[int] = None, scene_index: Optional[int] = None):
        """保存实体状态快照到数据库"""
        if not self.db_manager or not self.db_manager.is_enabled():
            return
        
        try:
            snapshot = EntityStateSnapshot(
                project_id=self.project_name,
                entity_type=entity_type,
                entity_id=entity_id,
                chapter_index=chapter_index,
                scene_index=scene_index,
                timestamp=datetime.now(),
                state_data=state_data
            )
            self.db_manager.save_entity_snapshot(snapshot)
        except Exception as e:
            print(f"⚠️ 保存实体状态快照失败: {e}")
    
    def _save_scene_content_to_vector(self, content: str, chapter_index: int, scene_index: int, 
                                     content_type: str = "scene"):
        """保存场景内容到向量存储和数据库"""
        if not self.vector_manager or not self.vector_manager.is_enabled():
            return
        
        try:
            # 保存到向量存储，并获取创建的记忆块
            chunks = self.vector_manager.add_scene_content(
                content=content,
                project_id=self.project_name,
                chapter_index=chapter_index,
                scene_index=scene_index
            )
            
            # 同时保存到数据库的 memory_chunks 表
            if chunks and self.db_manager and self.db_manager.is_enabled():
                for chunk in chunks:
                    self.db_manager.save_memory_chunk(chunk)
                print(f"已将{len(chunks)}个记忆块保存到数据库")
                
        except Exception as e:
            print(f"⚠️ 保存场景内容到向量存储失败: {e}")
    
    def _delete_chapter_vector_memory(self, chapter_index: int):
        """删除指定章节的所有向量记忆和数据库记录"""
        # 1. 从向量库删除
        if self.vector_manager and self.vector_manager.is_enabled():
            try:
                # 获取该章节的所有记忆块
                chunks = self.vector_manager.get_chunks_by_project(
                    project_id=self.project_name,
                    chapter_index=chapter_index
                )
                
                if chunks and self.vector_manager.vector_store:
                    # 删除向量库中的记忆块
                    chunk_ids = [chunk.chunk_id for chunk in chunks]
                    self.vector_manager.vector_store.collection.delete(ids=chunk_ids)
                    print(f"已从向量库删除第{chapter_index}章的{len(chunk_ids)}个记忆块")
            except Exception as e:
                print(f"⚠️ 删除章节向量记忆失败: {e}")
        
        # 2. 从数据库删除
        if self.db_manager and self.db_manager.is_enabled():
            try:
                # 直接通过SQL删除该章节的所有记忆块
                with self.db_manager.get_connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM memory_chunks WHERE project_id = ? AND chapter_index = ?",
                        (self.project_name, chapter_index)
                    )
                    deleted_count = cursor.rowcount
                    conn.commit()
                    print(f"已从数据库删除第{chapter_index}章的{deleted_count}个记忆块记录")
            except Exception as e:
                print(f"⚠️ 删除章节数据库记忆记录失败: {e}")
    
    def close(self):
        """关闭持久化连接"""
        if self.db_manager:
            try:
                self.db_manager.close()
            except Exception as e:
                print(f"⚠️ 关闭数据库连接失败: {e}")
        
        if self.vector_manager:
            try:
                self.vector_manager.close()
            except Exception as e:
                print(f"⚠️ 关闭向量存储连接失败: {e}")

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
        
        # 保存世界观状态快照到数据库
        self._save_entity_snapshot("world", "main_world", world.model_dump())
        
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
        
        # 保存主题冲突状态快照到数据库
        self._save_entity_snapshot("theme", "main_theme", theme_conflict.model_dump())
        
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
        
        # 保存角色状态快照到数据库
        self._save_entity_snapshot("characters", "main_characters", characters.model_dump())
        
        # 为每个角色保存单独的状态快照
        # 保存主角
        self._save_entity_snapshot("character", characters.protagonist.name, characters.protagonist.model_dump())
        # 保存反派（如果存在）
        if characters.antagonist:
            self._save_entity_snapshot("character", characters.antagonist.name, characters.antagonist.model_dump())
        # 保存配角
        for character in characters.supporting_characters:
            self._save_entity_snapshot("character", character.name, character.model_dump())
        
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
        
        # 保存大纲状态快照到数据库
        self._save_entity_snapshot("outline", "main_outline", outline.model_dump())
        
        # 为每个章节保存单独的状态快照
        for chapter in outline.chapters:
            self._save_entity_snapshot("chapter", f"chapter_{chapter.chapter_number}", 
                                      chapter.model_dump(), chapter.chapter_number)
        
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
            
            # 保存章节计划状态快照到数据库
            self._save_entity_snapshot("chapter_plan", f"chapter_{num}_plan", 
                                      chapter_plan.model_dump(), num)
            
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
            
            # 如果没有已存在的记忆上下文，则生成新的
            if scene_memory_context is None:
                try:
                    from novelgen.chains.memory_context_chain import retrieve_scene_memory_context
                    scene_memory_context = retrieve_scene_memory_context(
                        scene_plan=scene_plan,
                        characters_config=characters,
                        project_id=self.project_name,
                        chapter_index=chapter_number,
                        scene_index=scene_plan.scene_number,
                        db_manager=self.db_manager,
                        vector_manager=self.vector_manager,
                        llm_config=self.config.memory_context_chain_config.llm_config,
                        output_dir=self.project_dir
                    )
                    print(f"    🧠 已为场景{scene_plan.scene_number}生成记忆上下文")
                except Exception as exc:
                    print(f"⚠️ 场景记忆上下文生成失败，将忽略：{exc}")
                    scene_memory_context = None

            scene = generate_scene_text(
                scene_plan,
                world,
                characters,
                previous_summary,
                chapter_context=chapter_context_payload,
                scene_memory_context=scene_memory_context,
                verbose=self.verbose,
                llm_config=self.config.scene_text_chain_config.llm_config
            )
            scenes.append(scene)

            # 保存场景内容到向量存储
            self._save_scene_content_to_vector(scene.content, chapter_number, scene.scene_number)

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
        
        # 保存章节状态快照到数据库
        self._save_entity_snapshot("chapter_text", f"chapter_{chapter_number}_text", 
                                  chapter.model_dump(), chapter_number)

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
