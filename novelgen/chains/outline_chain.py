"""
大纲生成链
基于世界观、主题冲突和角色生成故事大纲
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import Outline, WorldSetting, ThemeConflict, CharactersConfig
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_outline_chain(verbose: bool = False, llm_config=None):
    """创建大纲生成链"""
    llm = get_llm(config=llm_config, verbose=verbose)
    base_parser = PydanticOutputParser[Outline](pydantic_object=Outline)
    parser = LLMJsonRepairOutputParser[Outline](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的故事大纲设计师。

你的任务：
1. 综合世界观、主题冲突与角色设定，规划完整故事走向
2. 按章节给出起承转合明确的剧情推进路径

输入说明：
- 输入包含世界观、主题冲突、角色配置JSON及期望章节数
- 任何输入字段均不可删除，必要时可引用

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 大纲要遵循经典的故事结构（起承转合）
2. 每个章节要有明确的目的和推进作用
3. 章节之间要有逻辑递进关系
4. 关键事件要体现主题和冲突
5. 要为角色发展留出空间
6. 严格按照JSON格式输出，不要使用Markdown包裹
7. 禁止输出未转义的英文双引号，使用「」或\"表达引用"""),
        ("user", """世界观设定：
{world_setting}

主题冲突：
{theme_conflict}

角色配置：
{characters}

预期章节数：{num_chapters}""")
    ])

    chain = prompt | llm | parser

    return chain


def generate_outline(
    world_setting: WorldSetting,
    theme_conflict: ThemeConflict,
    characters: CharactersConfig,
    num_chapters: int = 20,
    verbose: bool = False,
    llm_config=None
) -> Outline:
    """
    生成故事大纲

    Args:
        world_setting: 世界观设定
        theme_conflict: 主题冲突
        characters: 角色配置
        num_chapters: 预期章节数
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置

    Returns:
        Outline对象
    """
    chain = create_outline_chain(verbose=verbose, llm_config=llm_config)
    parser = PydanticOutputParser[Outline](pydantic_object=Outline)

    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "theme_conflict": theme_conflict.model_dump_json(indent=2),
        "characters": characters.model_dump_json(indent=2),
        "num_chapters": num_chapters,
        "format_instructions": parser.get_format_instructions()
    })

    return result

