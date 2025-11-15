"""
编排器
协调整个小说生成流程
"""
import os
import json
from pathlib import Path
from typing import Optional

from novelgen.models import (
    WorldSetting, ThemeConflict, CharactersConfig,
    Outline, ChapterPlan, GeneratedChapter, GeneratedScene
)
from novelgen.config import ProjectConfig
from novelgen.chains.world_chain import generate_world
from novelgen.chains.theme_conflict_chain import generate_theme_conflict
from novelgen.chains.characters_chain import generate_characters
from novelgen.chains.outline_chain import generate_outline
from novelgen.chains.chapters_plan_chain import generate_chapter_plan
from novelgen.chains.scene_text_chain import generate_scene_text
from novelgen.runtime.exporter import export_chapter_to_txt, export_all_chapters_to_txt


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
    
    def step5_create_chapter_plan(self, chapter_number: int, force: bool = False) -> ChapterPlan:
        """
        步骤5: 创建章节计划
        
        Args:
            chapter_number: 章节编号
            
        Returns:
            ChapterPlan对象
        """
        plan_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}_plan.json"
        )
        existing = self._maybe_use_existing(
            plan_file, ChapterPlan, force, f"第{chapter_number}章章节计划"
        )
        if existing:
            return existing

        print(f"📝 正在生成第{chapter_number}章的计划...")
        world = self.load_json(self.config.world_file, WorldSetting)
        characters = self.load_json(self.config.characters_file, CharactersConfig)
        outline = self.load_json(self.config.outline_file, Outline)
        
        if not all([world, characters, outline]):
            raise ValueError("缺少前置文件，请先执行前置步骤")
        
        # 找到对应章节
        chapter_summary = None
        for ch in outline.chapters:
            if ch.chapter_number == chapter_number:
                chapter_summary = ch
                break
        
        if not chapter_summary:
            raise ValueError(f"章节{chapter_number}不存在于大纲中")
        
        chapter_plan = generate_chapter_plan(
            chapter_summary,
            world,
            characters,
            verbose=self.verbose,
            llm_config=self.config.chapters_plan_chain_config.llm_config
        )
        
        # 保存章节计划
        self.save_json(chapter_plan, plan_file)
        print(f"✅ 章节计划已保存: {plan_file}")
        return chapter_plan
    
    def step6_generate_chapter_text(self, chapter_number: int) -> GeneratedChapter:
        """
        步骤6: 生成章节文本
        
        Args:
            chapter_number: 章节编号
            
        Returns:
            GeneratedChapter对象
        """
        print(f"✍️  正在生成第{chapter_number}章的文本...")
        world = self.load_json(self.config.world_file, WorldSetting)
        characters = self.load_json(self.config.characters_file, CharactersConfig)
        
        plan_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}_plan.json"
        )
        chapter_plan = self.load_json(plan_file, ChapterPlan)
        
        if not all([world, characters, chapter_plan]):
            raise ValueError("缺少前置文件，请先执行前置步骤")
        
        # 生成各场景文本
        scenes = []
        previous_summary = ""
        
        for scene_plan in chapter_plan.scenes:
            print(f"  生成场景 {scene_plan.scene_number}...")
            scene = generate_scene_text(
                scene_plan,
                world,
                characters,
                previous_summary,
                verbose=self.verbose,
                llm_config=self.config.scene_text_chain_config.llm_config
            )
            scenes.append(scene)
            
            # 更新前文概要
            previous_summary = f"前一场景概要：{scene_plan.purpose}"
        
        # 组装章节
        total_words = sum(scene.word_count for scene in scenes)
        chapter = GeneratedChapter(
            chapter_number=chapter_number,
            chapter_title=chapter_plan.chapter_title,
            scenes=scenes,
            total_words=total_words
        )
        
        # 保存章节文本
        text_file = os.path.join(
            self.config.chapters_dir,
            f"chapter_{chapter_number:03d}.json"
        )
        self.save_json(chapter, text_file)
        print(f"✅ 章节文本已保存: {text_file}")
        return chapter
    
    def generate_all_chapters(self):
        """生成所有章节"""
        outline = self.load_json(self.config.outline_file, Outline)
        if not outline:
            raise ValueError("大纲文件不存在，请先执行步骤4")
        
        for chapter_summary in outline.chapters:
            chapter_num = chapter_summary.chapter_number
            
            # 生成章节计划
            self.step5_create_chapter_plan(chapter_num)
            
            # 生成章节文本
            self.step6_generate_chapter_text(chapter_num)
        
        print(f"\n🎉 全部{len(outline.chapters)}章已生成完毕！")
    
    def export_chapter(self, chapter_number: int, output_path: Optional[str] = None):
        """
        导出单个章节为txt文件
        
        Args:
            chapter_number: 章节编号
            output_path: 输出文件路径（可选）。如果不指定，默认保存到 chapters/chapter_XXX.txt
        """
        # 加载章节数据
        chapter = self.load_chapter(chapter_number)
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

