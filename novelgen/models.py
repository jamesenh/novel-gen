"""
数据模型定义
所有业务相关的数据结构都定义在此文件中
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """全局设置"""
    project_name: str = Field(description="项目名称")
    author: str = Field(default="Jamesenh", description="作者")
    llm_model: str = Field(default="gpt-4", description="使用的LLM模型")
    temperature: float = Field(default=0.7, description="生成温度")
    persistence_enabled: bool = Field(default=True, description="是否启用数据持久化")
    vector_store_enabled: bool = Field(default=True, description="是否启用向量存储")


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


class ChapterDependency(BaseModel):
    """章节依赖信息"""
    dependency_type: str = Field(description="依赖类型，如事件/角色状态/地点等")
    description: str = Field(description="依赖描述，说明必须满足的条件")
    chapter_number: Optional[int] = Field(default=None, description="依赖的章节编号（如适用）")
    event_id: Optional[str] = Field(default=None, description="依赖的事件ID或自定义标识")


class ChapterSummary(BaseModel):
    """章节摘要"""
    chapter_number: int = Field(description="章节编号")
    chapter_title: str = Field(description="章节标题")
    summary: str = Field(description="章节概要")
    key_events: List[str] = Field(description="关键事件")
    timeline_anchor: Optional[str] = Field(default=None, description="时间线锚点，表明本章发生的时间位置")
    dependencies: List[ChapterDependency] = Field(default_factory=list, description="本章开始前必须满足的依赖列表")


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


class ChapterMemoryEntry(BaseModel):
    """章节记忆表记录"""
    chapter_number: int = Field(description="章节编号")
    chapter_title: str = Field(description="章节标题")
    timeline_anchor: Optional[str] = Field(default=None, description="时间线锚点")
    location_summary: Optional[str] = Field(default=None, description="本章主要地点概述")
    key_events: List[str] = Field(default_factory=list, description="推动剧情的主要事件")
    character_states: Dict[str, str] = Field(default_factory=dict, description="关键角色当前状态")
    unresolved_threads: List[str] = Field(default_factory=list, description="未解决的悬念或任务")
    summary: str = Field(description="章节摘要（整章）")


class ConsistencyIssue(BaseModel):
    """一致性问题
    
    注：是否可自动修复通过 fix_instructions 是否为空来判断
    """
    issue_type: str = Field(description="问题类型（设定冲突/角色矛盾等）")
    description: str = Field(description="问题描述")
    related_characters: List[str] = Field(default_factory=list, description="涉及角色")
    severity: str = Field(default="medium", description="严重程度: low/medium/high")
    fix_instructions: Optional[str] = Field(default=None, description="修复建议（若为空则不可自动修复）")


class ConsistencyReport(BaseModel):
    """一致性检测结果"""
    chapter_number: int = Field(description="章节编号")
    issues: List[ConsistencyIssue] = Field(default_factory=list, description="发现的问题列表")
    summary: str = Field(description="检测摘要")
    context_snapshot: Optional[str] = Field(default=None, description="用于检测的上下文摘要")


class RevisionStatus(BaseModel):
    """章节修订状态"""
    chapter_number: int = Field(description="章节编号")
    status: str = Field(description="状态: pending/accepted/rejected")
    revision_notes: str = Field(description="修订说明")
    issues: List[ConsistencyIssue] = Field(default_factory=list, description="待修复问题列表")
    revised_chapter: Optional[GeneratedChapter] = Field(default=None, description="修订候选的完整章节结构")
    created_at: str = Field(description="创建时间")
    decision_at: Optional[str] = Field(default=None, description="确认时间")


# 持久化相关数据模型

class EntityStateSnapshot(BaseModel):
    """实体在特定时间点的状态快照"""
    project_id: str = Field(description="项目ID")
    entity_type: str = Field(description="实体类型：character, location, item")
    entity_id: str = Field(description="实体ID")
    chapter_index: Optional[int] = Field(default=None, description="章节索引")
    scene_index: Optional[int] = Field(default=None, description="场景索引")
    timestamp: datetime = Field(description="时间戳")
    state_data: Dict[str, Any] = Field(description="JSON格式的状态数据")
    version: int = Field(default=1, description="版本号")


class StoryMemoryChunk(BaseModel):
    """文本记忆块"""
    chunk_id: str = Field(description="记忆块ID")
    project_id: str = Field(description="项目ID")
    chapter_index: Optional[int] = Field(default=None, description="章节索引")
    scene_index: Optional[int] = Field(default=None, description="场景索引")
    content: str = Field(description="原始文本内容")
    content_type: str = Field(description="内容类型：scene, dialogue, description")
    entities_mentioned: List[str] = Field(default_factory=list, description="提及的实体ID")
    tags: List[str] = Field(default_factory=list, description="内容标签")
    embedding_id: Optional[str] = Field(default=None, description="向量存储中的ID")
    created_at: datetime = Field(description="创建时间")


class SceneMemoryContext(BaseModel):
    """场景记忆上下文，用于传递给生成链"""
    project_id: str = Field(description="项目ID")
    chapter_index: Optional[int] = Field(default=None, description="章节索引")
    scene_index: Optional[int] = Field(default=None, description="场景索引")
    entity_states: List[EntityStateSnapshot] = Field(default_factory=list, description="实体状态列表")
    relevant_memories: List[StoryMemoryChunk] = Field(default_factory=list, description="相关记忆列表")
    timeline_context: Optional[Dict[str, Any]] = Field(default=None, description="时间线上下文")
    retrieval_timestamp: datetime = Field(description="检索时间戳")
