"""
章节计划生成链
将大纲中的章节细化为具体的场景计划
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import ChapterPlan, ChapterSummary, WorldSetting, CharactersConfig
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_chapter_plan_chain(verbose: bool = False, llm_config=None):
    """创建章节计划生成链"""
    llm = get_llm(config=llm_config, verbose=verbose)
    base_parser = PydanticOutputParser[ChapterPlan](pydantic_object=ChapterPlan)
    parser = LLMJsonRepairOutputParser[ChapterPlan](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的章节结构设计师。

你的任务：
1. 将章节摘要拆解为若干有清晰目标的场景
2. 输出可直接驱动文本生成的场景计划

输入说明：
- 输入包含世界观、角色配置与章节摘要JSON
- 场景数量由你根据剧情需要决定

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 场景要有明确的地点和出场角色
2. 每个场景要有清晰的目的
3. 场景之间要有连贯性
4. 关键动作要推动情节发展
5. 预计字数要合理（一般3000-5000字/场景）
6. 严格按照JSON格式输出，不要使用Markdown包裹
7. 文本中如需引用势力或法术名称，使用「」或\"，避免未转义双引号"""),
        ("user", """世界观设定：
{world_setting}

角色配置：
{characters}

章节摘要：
{chapter_summary}""")
    ])

    chain = prompt | llm | parser

    return chain


def generate_chapter_plan(
    chapter_summary: ChapterSummary,
    world_setting: WorldSetting,
    characters: CharactersConfig,
    verbose: bool = False,
    llm_config=None
) -> ChapterPlan:
    """
    生成章节计划

    Args:
        chapter_summary: 章节摘要
        world_setting: 世界观设定
        characters: 角色配置
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置

    Returns:
        ChapterPlan对象
    """
    chain = create_chapter_plan_chain(verbose=verbose, llm_config=llm_config)
    parser = PydanticOutputParser[ChapterPlan](pydantic_object=ChapterPlan)

    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "characters": characters.model_dump_json(indent=2),
        "chapter_summary": chapter_summary.model_dump_json(indent=2),
        "format_instructions": parser.get_format_instructions()
    })

    return result

