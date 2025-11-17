# 开发者: jamesenh, 开发时间: 2025-11-17

"""
编排器
协调整个小说生成流程
"""
import os
import json
from typing import Optional, Union, List

from novelgen.models import (
    WorldSetting, ThemeConflict, CharactersConfig,
    Outline, ChapterPlan, GeneratedChapter, GeneratedScene,
    ChapterSummary, ChapterMemoryEntry, ConsistencyReport
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
from novelgen.runtime.revision import revise_text


class NovelOrchestrator:
    """小说生成编排器"""

    def __init__(self, project_name: str, base_dir: str = "projects", verbose: bool = False):
        """
        初始化编排器

        Args:
            project_name: 项目名称
            base_dir: 项目基础目录
            verbose: 是否启用详细日志（显示提示词、响应时间、token使用情况）
        """
        self.project_name = project_name
        self.project_dir = os.path.join(base_dir, project_name)
        self.config = ProjectConfig(project_dir=self.project_dir)
        self.verbose = verbose

        # 创建项目目录
        os.makedirs(self.project_dir, exist_ok=True)
        os.makedirs(self.config.chapters_dir, exist_ok=True)

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

    def _maybe_trigger_auto_revision(self, report: ConsistencyReport, chapter_text: str, chapter_number: int):
        """
        如果一致性报告包含可自动修复项，则调用修订链并输出结果

        Args:
            report: 一致性检测结果
            chapter_text: 原章节文本
            chapter_number: 当前章节编号
        """
        actionable = [
            issue for issue in report.issues
            if issue.can_auto_fix and issue.fix_instructions
        ]
        if not actionable:
            return

        revision_notes = "\n".join(
            f"- {issue.issue_type}: {issue.fix_instructions}"
            for issue in actionable
        )
        revised_text = revise_text(chapter_text, revision_notes)
        revision_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}_revised.txt"
        )
        with open(revision_file, 'w', encoding='utf-8') as f:
            f.write(revised_text)
        print(f"🔁 已针对章节{chapter_number}生成修订稿：{revision_file}")

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
            scene = generate_scene_text(
                scene_plan,
                world,
                characters,
                previous_summary,
                chapter_context=chapter_context_payload,
                verbose=self.verbose,
                llm_config=self.config.scene_text_chain_config.llm_config
            )
            scenes.append(scene)

            # 更新前文概要
            scene_summary = self._summarize_scene_safe(scene)
            scene_summaries.append(f"场景{scene.scene_number}: {scene_summary}")
            previous_summary = scene_summary

        aggregated_summary = self._summarize_chapter_safe(scenes)

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

        # 更新章节记忆
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
        except Exception as exc:
            print(f"⚠️ 章节记忆生成失败：{exc}")

        # 一致性检测
        chapter_text = self._collect_chapter_text(chapter)
        context_payload = self._build_consistency_context(chapter_number, chapter_summary)
        try:
            report = run_consistency_check(
                chapter_number=chapter_number,
                context_payload=context_payload,
                chapter_text=chapter_text,
                verbose=self.verbose,
                llm_config=self.config.consistency_chain_config.llm_config
            )
            self._record_consistency_report(report)
            self._maybe_trigger_auto_revision(report, chapter_text, chapter_number)
        except Exception as exc:
            print(f"⚠️ 一致性检测失败：{exc}")

        return chapter

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

        for chapter_num in target_numbers:

            # 生成章节计划
            self.step5_create_chapter_plan(chapter_num, force=force)

            # 生成章节文本
            self.step6_generate_chapter_text(chapter_num, force=force)

        print(f"\n🎉 共{len(target_numbers)}章已生成完毕！")

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
