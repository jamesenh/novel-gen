"""
主题冲突生成链
基于世界观生成故事的主题和冲突

更新: 2025-12-02 - 添加多候选生成模式，支持从世界观自动推导
"""
import json
import os
from datetime import datetime
from typing import Any, Optional, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from novelgen.models import ThemeConflict, ThemeConflictVariant, ThemeConflictVariantsResult, WorldSetting
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_theme_conflict_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建主题冲突生成链"""
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[ThemeConflict](pydantic_object=ThemeConflict)
    parser = LLMJsonRepairOutputParser[ThemeConflict](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的故事策划师。

你的任务：
1. 基于世界观设定提炼最契合的核心主题
2. 设计主次分明、可支撑长篇叙事的冲突结构

输入说明：
- 将同时收到完整的世界观设定JSON与用户需求描述
- 输入数据字段含义不可删除或重命名

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 主题要深刻、有思考价值
2. 冲突要激烈、有张力
3. 主题和冲突要与世界观相契合
4. 次要主题和冲突要支撑主要内容
5. 严格按照JSON格式输出，不要使用Markdown包裹
6. 文本中不得出现未转义的英文双引号，必要时用「」或\"表示"""),
        ("user", """世界观设定：
{world_setting}

用户需求：
{user_input}""")
    ])

    chain = prompt | llm | parser

    return chain


def generate_theme_conflict(world_setting: WorldSetting, user_input: str = "", verbose: bool = False, llm_config=None, show_prompt: bool = True) -> ThemeConflict:
    """
    生成主题冲突

    Args:
        world_setting: 世界观设定
        user_input: 用户关于故事方向的描述
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置
        show_prompt: verbose 模式下是否显示完整提示词

    Returns:
        ThemeConflict对象
    """
    chain = create_theme_conflict_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    parser = PydanticOutputParser[ThemeConflict](pydantic_object=ThemeConflict)

    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "user_input": user_input if user_input else "请基于世界观自由发挥",
        "format_instructions": parser.get_format_instructions()
    })

    return result


# ==================== 多候选生成模式 ====================


class ThemeConflictVariantsOutput(BaseModel):
    """主题冲突多候选生成的中间输出模型"""
    variants: List[ThemeConflictVariant] = Field(description="主题冲突候选列表")


def create_theme_conflict_variants_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建主题冲突多候选生成链"""
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[ThemeConflictVariantsOutput](pydantic_object=ThemeConflictVariantsOutput)
    parser = LLMJsonRepairOutputParser[ThemeConflictVariantsOutput](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的故事策划师，擅长为同一个世界观设计多种不同风格的主题冲突方案。

你的任务：
1. 基于世界观设定，生成 {num_variants} 个风格各异的主题冲突候选
2. 每个候选应有独特的叙事风格和情感基调
3. 确保候选之间有明显的差异化

输入说明：
- 将收到完整的世界观设定 JSON
- 可能收到用户的主题方向提示（如有）

候选差异化维度（每个候选至少在 2-3 个维度上与其他候选不同）：
- 核心主题方向：成长/复仇/守护/爱情/探索/救赎/自我发现
- 冲突类型：外部冲突（敌对势力）/内心冲突（心魔抉择）/人际冲突（关系破裂）/命运冲突（宿命对抗）
- 作品基调：热血燃向/黑暗深沉/温馨治愈/悬疑紧张/轻松幽默
- 叙事节奏：快节奏冒险/慢热情感/跌宕起伏

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 每个候选的 variant_id 使用 "variant_1", "variant_2" 等格式
2. style_tag 用简短的风格标签概括（如「热血成长」「黑暗复仇」）
3. brief_description 用 50-100 字概括这个方案的核心主题和主要冲突
4. theme_conflict 必须是完整的主题冲突对象
5. 严格按照 JSON 格式输出，不要使用 Markdown 包裹
6. 文本中不得出现未转义的英文双引号，必要时用「」或\"表示"""),
        ("user", """世界观设定：
{world_setting}

用户主题方向：
{user_direction}

请生成 {num_variants} 个风格各异的主题冲突候选。""")
    ])

    chain = prompt | llm | parser

    return chain


def generate_theme_conflict_variants(
    world_setting: WorldSetting,
    user_direction: Optional[str] = None,
    num_variants: Optional[int] = None,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> ThemeConflictVariantsResult:
    """
    生成多个主题冲突候选
    
    Args:
        world_setting: 世界观设定
        user_direction: 用户输入的主题方向（可选，如 "复仇"、"爱情"）
        num_variants: 候选数量（默认 None 使用配置值，范围 2-5）
        verbose: 是否输出详细日志
        llm_config: LLM配置
        show_prompt: verbose 模式下是否显示完整提示词
    
    Returns:
        ThemeConflictVariantsResult 包含多个候选
    """
    # 如果未指定数量，使用默认值 3
    if num_variants is None:
        num_variants = 3
    # 限制候选数量在 2-5 范围内
    num_variants = max(2, min(5, num_variants))
    
    chain = create_theme_conflict_variants_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    parser = PydanticOutputParser[ThemeConflictVariantsOutput](pydantic_object=ThemeConflictVariantsOutput)
    
    direction_text = user_direction if user_direction else "请根据世界观自由发挥，探索不同的主题可能性"
    
    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "user_direction": direction_text,
        "num_variants": num_variants,
        "format_instructions": parser.get_format_instructions()
    })
    
    return ThemeConflictVariantsResult(
        user_direction=user_direction,
        world_setting_name=world_setting.world_name,
        variants=result.variants,
        generated_at=datetime.now().isoformat()
    )


def select_theme_conflict_variant(
    variants_result: ThemeConflictVariantsResult,
    variant_id: str
) -> ThemeConflict:
    """
    从候选中选择一个主题冲突
    
    Args:
        variants_result: 多候选生成结果
        variant_id: 要选择的变体 ID（如 "variant_1"）
    
    Returns:
        选中的 ThemeConflict 对象
    
    Raises:
        ValueError: 如果 variant_id 不存在
    """
    for variant in variants_result.variants:
        if variant.variant_id == variant_id:
            return variant.theme_conflict
    
    available_ids = [v.variant_id for v in variants_result.variants]
    raise ValueError(f"未找到 variant_id='{variant_id}'，可用的有: {available_ids}")


def save_theme_conflict_variants(variants_result: ThemeConflictVariantsResult, file_path: str) -> None:
    """
    保存主题冲突候选结果到文件
    
    Args:
        variants_result: 候选结果
        file_path: 保存路径
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(variants_result.model_dump(), f, ensure_ascii=False, indent=2)


def load_theme_conflict_variants(file_path: str) -> ThemeConflictVariantsResult:
    """
    从文件加载主题冲突候选结果
    
    Args:
        file_path: 文件路径
    
    Returns:
        ThemeConflictVariantsResult 对象
    
    Raises:
        FileNotFoundError: 如果文件不存在
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ThemeConflictVariantsResult(**data)

