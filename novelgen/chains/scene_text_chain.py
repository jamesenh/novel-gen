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
        ("system", """你是一位专业的小说作家，精通简体中文创作。

【核心要求】
1. 语言：使用简体中文，避免西化表达
2. 视角：采用第三人称有限视角，以本场景的核心角色为视角载体
3. 字数：严格控制在目标字数的±20%范围内（目标字数见输入信息）
4. 设定约束：不得修改世界观和角色配置中的任何已有信息，只能在此基础上展开。遇到不确定的地方，宁可模糊处理也不要编造新设定

【节奏控制】
根据场景类型(scene_type)和强度(intensity)调整叙事节奏：
- 日常/对话场景：多心理描写，节奏舒缓，注重细节刻画
- 战斗/高潮场景：少环境多动作，短句为主，节奏快速
- 发展场景：平衡叙事与描写，稳步推进情节
- 强度越高，节奏越快，动作和对话占比越大

【前文概要使用】
前文概要仅供保持情节连贯性和设定一致，不要在正文中机械复述。重点参考：
- 角色关系和当前状态
- 世界观设定（境界、规则等）
- 事件承接关系

【避免套路化】
- 避免陈词滥调和重复性的外貌/神态描写
- 同一人物多次出场时，变换描写角度和侧重点
- 比喻和修辞要有新意，不要反复使用相同表达

【输出格式】
{format_instructions}

重要：必须严格按JSON格式输出，不要Markdown包裹，不要任何额外文字"""),
        ("user", """【字数要求】
目标字数：{scene_plan_obj.estimated_words} 字（中文字符数）
可接受范围：{word_count_min} ~ {word_count_max} 字（±20%）

【场景信息】
场景类型：{scene_plan_obj.scene_type}
强度等级：{scene_plan_obj.intensity}

【世界观设定】
{world_setting}

【角色配置】
{characters}

【场景计划】
{scene_plan}

【前文概要】
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

    # 计算字数范围
    target_words = scene_plan.estimated_words
    word_count_min = int(target_words * 0.8)
    word_count_max = int(target_words * 1.2)

    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "characters": characters.model_dump_json(indent=2),
        "scene_plan": scene_plan.model_dump_json(indent=2),
        "scene_plan_obj": scene_plan,  # 传递对象本身，用于访问具体属性
        "previous_summary": previous_summary if previous_summary else "这是第一个场景",
        "format_instructions": parser.get_format_instructions(),
        "word_count_min": word_count_min,
        "word_count_max": word_count_max
    })

    return result

