"""
主题冲突生成链
基于世界观生成故事的主题和冲突
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import ThemeConflict, WorldSetting
from novelgen.llm import get_llm


def create_theme_conflict_chain(verbose: bool = False, llm_config=None):
    """创建主题冲突生成链"""
    parser = PydanticOutputParser[ThemeConflict](pydantic_object=ThemeConflict)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的故事策划师。

你的任务：基于已有的世界观设定，设计故事的核心主题和冲突结构。

输入说明：你会收到完整的世界观设定JSON和用户的故事方向描述

输出格式：{format_instructions}

注意事项：
1. 主题要深刻、有思考价值
2. 冲突要激烈、有张力
3. 主题和冲突要与世界观相契合
4. 次要主题和冲突要支撑主要内容
5. 严格按照JSON格式输出，不要使用Markdown包裹"""),
        ("user", """世界观设定：
{world_setting}

用户需求：
{user_input}""")
    ])

    llm = get_llm(config=llm_config, verbose=verbose)
    chain = prompt | llm | parser

    return chain


def generate_theme_conflict(world_setting: WorldSetting, user_input: str = "", verbose: bool = False, llm_config=None) -> ThemeConflict:
    """
    生成主题冲突

    Args:
        world_setting: 世界观设定
        user_input: 用户关于故事方向的描述
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置

    Returns:
        ThemeConflict对象
    """
    chain = create_theme_conflict_chain(verbose=verbose, llm_config=llm_config)
    parser = PydanticOutputParser[ThemeConflict](pydantic_object=ThemeConflict)

    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "user_input": user_input if user_input else "请基于世界观自由发挥",
        "format_instructions": parser.get_format_instructions()
    })

    return result

