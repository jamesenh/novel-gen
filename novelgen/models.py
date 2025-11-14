"""
数据模型定义
所有业务相关的数据结构都定义在此文件中
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """全局设置"""
    project_name: str = Field(description="项目名称")
    author: str = Field(default="Jamesenh", description="作者")
    llm_model: str = Field(default="gpt-4", description="使用的LLM模型")
    temperature: float = Field(default=0.7, description="生成温度")


class WorldSetting(BaseModel):
    """世界观设定"""
    world_name: str = Field(description="世界名称")
    time_period: str = Field(description="时代背景")
    geography: str = Field(description="地理环境")
    social_system: str = Field(description="社会制度")
    power_system: Optional[str] = Field(default=None, description="力量体系（如有）")
    technology_level: str = Field(description="科技水平")
    culture_customs: str = Field(description="文化习俗")
    special_rules: Optional[str] = Field(default=None, description="特殊规则")


class ThemeConflict(BaseModel):
    """主题与冲突"""
    core_theme: str = Field(description="核心主题")
    sub_themes: List[str] = Field(description="次要主题")
    main_conflict: str = Field(description="主要冲突")
    sub_conflicts: List[str] = Field(description="次要冲突")
    tone: str = Field(description="作品基调")


class Character(BaseModel):
    """角色信息"""
    name: str = Field(description="角色姓名")
    role: str = Field(description="角色定位（主角/配角/反派等）")
    age: Optional[int] = Field(default=None, description="年龄")
    gender: str = Field(description="性别")
    appearance: str = Field(description="外貌特征")
    personality: str = Field(description="性格特点")
    background: str = Field(description="背景故事")
    motivation: str = Field(description="行动动机")
    abilities: Optional[List[str]] = Field(default=None, description="特殊能力")
    relationships: Optional[Dict[str, str]] = Field(default=None, description="与其他角色的关系")


class CharactersConfig(BaseModel):
    """角色配置集合"""
    protagonist: Character = Field(description="主角")
    antagonist: Optional[Character] = Field(default=None, description="反派")
    supporting_characters: List[Character] = Field(default_factory=list, description="配角列表")


class ChapterSummary(BaseModel):
    """章节摘要"""
    chapter_number: int = Field(description="章节编号")
    chapter_title: str = Field(description="章节标题")
    summary: str = Field(description="章节概要")
    key_events: List[str] = Field(description="关键事件")


class Outline(BaseModel):
    """小说大纲"""
    story_premise: str = Field(description="故事前提")
    beginning: str = Field(description="开端")
    development: str = Field(description="发展")
    climax: str = Field(description="高潮")
    resolution: str = Field(description="结局")
    chapters: List[ChapterSummary] = Field(description="章节列表")


class ScenePlan(BaseModel):
    """场景计划"""
    scene_number: int = Field(description="场景编号")
    location: str = Field(description="场景地点")
    characters: List[str] = Field(description="出场角色")
    purpose: str = Field(description="场景目的")
    key_actions: List[str] = Field(description="关键动作")
    estimated_words: int = Field(description="预计字数")
    scene_type: str = Field(description="场景类型: 日常/对话/战斗/发展/高潮/结局")
    intensity: str = Field(description="强度等级: 低/中/高")
    developer_name: str = Field(default="Jamesenh")  # 开发者名字
    developer_date: str = Field(default="2025-11-15")  # 开发时间


class ChapterPlan(BaseModel):
    """章节详细计划"""
    chapter_number: int = Field(description="章节编号")
    chapter_title: str = Field(description="章节标题")
    scenes: List[ScenePlan] = Field(description="场景列表")


class GeneratedScene(BaseModel):
    """生成的场景文本"""
    scene_number: int = Field(description="场景编号")
    content: str = Field(description="场景正文")
    word_count: int = Field(description="实际字数")


class GeneratedChapter(BaseModel):
    """生成的章节"""
    chapter_number: int = Field(description="章节编号")
    chapter_title: str = Field(description="章节标题")
    scenes: List[GeneratedScene] = Field(description="场景文本列表")
    total_words: int = Field(description="总字数")
