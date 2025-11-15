"""
角色生成链
基于世界观和主题冲突生成角色
"""
from typing import Any


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import CharactersConfig, WorldSetting, ThemeConflict
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_characters_chain(verbose: bool = False, llm_config=None):
    """创建角色生成链"""
    llm = get_llm(config=llm_config, verbose=verbose)
    base_parser = PydanticOutputParser[CharactersConfig](pydantic_object=CharactersConfig)
    parser = LLMJsonRepairOutputParser[CharactersConfig](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的角色设计师。

你的任务：
1. 基于世界观和主题冲突设计主角、反派及关键配角
2. 给出支撑长篇叙事的动机、背景与关系网络

输入说明：
- 输入包含世界观JSON与主题冲突JSON
- 必须保留输入中的设定约束

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 角色要立体、有深度
2. 角色的动机要符合主题冲突
3. 角色之间要有关系网络
4. 角色能力要符合世界观设定
5. 主角和反派要形成对立统一
6. 严格按照JSON格式输出，不要使用Markdown包裹
7. 正文内容如需引用称谓或势力名称，统一使用「」或写成\"，严禁出现未转义的英文双引号"""),
        ("user", """世界观设定：
{world_setting}

主题冲突：
{theme_conflict}""")
    ])

    chain = prompt | llm | parser

    return chain


def generate_characters(world_setting: WorldSetting, theme_conflict: ThemeConflict, verbose: bool = False, llm_config=None) -> CharactersConfig:
    """
    生成角色

    Args:
        world_setting: 世界观设定
        theme_conflict: 主题冲突
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置

    Returns:
        CharactersConfig对象
    """
    chain = create_characters_chain(verbose=verbose, llm_config=llm_config)
    parser = PydanticOutputParser[CharactersConfig](pydantic_object=CharactersConfig)

    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "theme_conflict": theme_conflict.model_dump_json(indent=2),
        "format_instructions": parser.get_format_instructions()
    })

    return result

