"""
角色生成链
基于世界观和主题冲突生成角色
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import CharactersConfig, WorldSetting, ThemeConflict
from novelgen.llm import get_llm


def create_characters_chain(verbose: bool = False):
    """创建角色生成链"""
    parser = PydanticOutputParser[CharactersConfig](pydantic_object=CharactersConfig)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的角色设计师。

你的任务：基于世界观和主题冲突，设计小说的主要角色。

输入说明：你会收到世界观设定JSON和主题冲突JSON

输出格式：{format_instructions}

注意事项：
1. 角色要立体、有深度
2. 角色的动机要符合主题冲突
3. 角色之间要有关系网络
4. 角色能力要符合世界观设定
5. 主角和反派要形成对立统一
6. 严格按照JSON格式输出，不要使用Markdown包裹
7. 正文内容中不要使用双引号"""),
        ("user", """世界观设定：
{world_setting}

主题冲突：
{theme_conflict}""")
    ])
    
    llm = get_llm(verbose=verbose)
    chain = prompt | llm | parser
    
    return chain


def generate_characters(world_setting: WorldSetting, theme_conflict: ThemeConflict, verbose: bool = False) -> CharactersConfig:
    """
    生成角色
    
    Args:
        world_setting: 世界观设定
        theme_conflict: 主题冲突
        verbose: 是否输出详细日志（提示词、时间、token）
        
    Returns:
        CharactersConfig对象
    """
    chain = create_characters_chain(verbose=verbose)
    parser = PydanticOutputParser[CharactersConfig](pydantic_object=CharactersConfig)
    
    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "theme_conflict": theme_conflict.model_dump_json(indent=2),
        "format_instructions": parser.get_format_instructions()
    })
    
    return result

