"""
世界观生成链
根据用户输入生成小说世界观设定
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import WorldSetting
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_world_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建世界观生成链"""
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[WorldSetting](pydantic_object=WorldSetting)
    parser = LLMJsonRepairOutputParser[WorldSetting](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说世界观设计师。

你的任务：
1. 根据用户提供的简要描述，完整构建一个自洽的小说世界观
2. 给出足够支持后续链路的关键细节

输入说明：
- 用户会提供世界的基本设定（如类型、风格、关键元素等）
- 所有输入均为JSON文本，保持字段含义不变

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 世界观要自洽、有逻辑
2. 细节要丰富，但不冗余
3. 要为后续的故事发展留出空间
4. 严格按照JSON格式输出，不要使用Markdown包裹
5. 文本内容中如需强调词语，使用「」、（）或将英文双引号写成\"，禁止出现未转义的英文双引号"""),
        ("user", "{user_input}")
    ])

    chain = prompt | llm | parser

    return chain


def generate_world(user_input: str, verbose: bool = False, llm_config=None, show_prompt: bool = True) -> WorldSetting:
    """
    生成世界观

    Args:
        user_input: 用户输入的世界设定描述
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置
        show_prompt: verbose 模式下是否显示完整提示词

    Returns:
        WorldSetting对象
    """
    chain = create_world_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    parser = PydanticOutputParser[WorldSetting](pydantic_object=WorldSetting)

    result = chain.invoke({
        "user_input": user_input,
        "format_instructions": parser.get_format_instructions()
    })

    return result

