"""
世界观生成链
根据用户输入生成小说世界观设定
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import WorldSetting
from novelgen.llm import get_llm


def create_world_chain(verbose: bool = False, llm_config=None):
    """创建世界观生成链"""
    parser = PydanticOutputParser[WorldSetting](pydantic_object=WorldSetting)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说世界观设计师。

你的任务：根据用户提供的简要描述，设计一个完整的小说世界观。

输入说明：用户会提供世界的基本设定（如类型、风格等）

输出格式：{format_instructions}

注意事项：
1. 世界观要自洽、有逻辑
2. 细节要丰富，但不冗余
3. 要为后续的故事发展留出空间
4. 严格按照JSON格式输出，不要使用Markdown包裹"""),
        ("user", "{user_input}")
    ])

    llm = get_llm(config=llm_config, verbose=verbose)
    chain = prompt | llm | parser

    return chain


def generate_world(user_input: str, verbose: bool = False, llm_config=None) -> WorldSetting:
    """
    生成世界观

    Args:
        user_input: 用户输入的世界设定描述
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置

    Returns:
        WorldSetting对象
    """
    chain = create_world_chain(verbose=verbose, llm_config=llm_config)
    parser = PydanticOutputParser[WorldSetting](pydantic_object=WorldSetting)

    result = chain.invoke({
        "user_input": user_input,
        "format_instructions": parser.get_format_instructions()
    })

    return result

