"""
场景文本生成链
根据场景计划生成实际的小说文本
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import GeneratedScene, ScenePlan, WorldSetting, CharactersConfig
from novelgen.llm import get_llm


def create_scene_text_chain(verbose: bool = False):
    """创建场景文本生成链"""
    parser = PydanticOutputParser[GeneratedScene](pydantic_object=GeneratedScene)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说作家。

你的任务：根据场景计划生成高质量的小说文本。

输入说明：你会收到世界观、角色配置、场景计划和前文概要

输出格式：{format_instructions}

注意事项：
1. 文笔要优美、流畅
2. 符合世界观设定和角色性格
3. 场景描写要生动、细腻
4. 对话要符合人物身份
5. 节奏要把握好，不拖沓不急躁
6. 字数要符合预期（误差不超过20%）
7. 严格按照JSON格式输出，不要使用Markdown包裹"""),
        ("user", """世界观设定：
{world_setting}

角色配置：
{characters}

场景计划：
{scene_plan}

前文概要：
{previous_summary}""")
    ])
    
    llm = get_llm(verbose=verbose)
    chain = prompt | llm | parser
    
    return chain


def generate_scene_text(
    scene_plan: ScenePlan,
    world_setting: WorldSetting,
    characters: CharactersConfig,
    previous_summary: str = "",
    verbose: bool = False
) -> GeneratedScene:
    """
    生成场景文本
    
    Args:
        scene_plan: 场景计划
        world_setting: 世界观设定
        characters: 角色配置
        previous_summary: 前文概要
        verbose: 是否输出详细日志（提示词、时间、token）
        
    Returns:
        GeneratedScene对象
    """
    chain = create_scene_text_chain(verbose=verbose)
    parser = PydanticOutputParser[GeneratedScene](pydantic_object=GeneratedScene)
    
    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "characters": characters.model_dump_json(indent=2),
        "scene_plan": scene_plan.model_dump_json(indent=2),
        "previous_summary": previous_summary if previous_summary else "这是第一个场景",
        "format_instructions": parser.get_format_instructions()
    })
    
    return result

