"""
场景文本生成链
根据场景计划生成实际的小说文本
"""
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import (
    GeneratedScene,
    ScenePlan,
    WorldSetting,
    CharactersConfig,
    SceneMemoryContext,
)
from novelgen.llm import get_llm, get_structured_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_scene_text_chain(verbose: bool = False, llm_config=None):
    """创建场景文本生成链
    
    优先使用 structured_output 模式。
    注：由于此链生成长正文，后续可考虑拆分为“结构 + 正文”两步生成。
    """
    if llm_config is None or llm_config.use_structured_output:
        try:
            structured_llm = get_structured_llm(
                pydantic_model=GeneratedScene,
                config=llm_config,
                verbose=verbose
            )
            
            # structured_output 模式下的 prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一位专业的小说作家，精通简体中文创作。

【核心要求】
1. 语言：使用简体中文，避免西化表达
2. 视角：采用第三人称有限视角，以本场景的核心角色为视角载体
3. 字数：严格控制在目标字数的±20%范围内（目标字数见输入信息）
4. 设定约束：不得修改世界观、角色配置以及章节上下文中的任何既有信息。遇到不确定事项，宁可模糊处理也不要推翻上下文。

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

【章节上下文】
章节上下文提供最近若干章的关键状态及未决悬念。生成文本必须与其一致，若要引入新设定，需要在正文中给出合理解释。

【场景记忆上下文（如有）】
如果提供了结构化的场景记忆上下文（SceneMemoryContext），其中的实体状态(entity_states)、近期事件与记忆片段(recent_events/relevant_memories，如果存在)应被视为约束性信息：
- 不得无故推翻其中已经确立的事实（例如已死亡角色突然出现、地点/时间与记忆严重冲突）
- 如需改变角色状态或关系，必须在剧情中给出清晰的过程与合理解释

【避免套路化】
- 避免陈词滥调和重复性的外貌/神态描写
- 同一人物多次出场时，变换描写角度和侧重点
- 比喻和修辞要有新意，不要反复使用相同表达

【输出要求】
1. 必须输出符合 JSON schema 的结构化数据
2. 必须包含 scene_number（场景编号）字段，类型为整数
3. 必须包含 content（场景正文）字段，类型为字符串，包含完整的场景文本
4. 必须包含 word_count（字数统计）字段，类型为整数，统计 content 的中文字符数"""),
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

【章节上下文】
{chapter_context}

【场景记忆上下文（如有）】
{scene_memory_context}

【场景计划、
{scene_plan}

【前文概要】
{previous_summary}""")
            ])
            
            chain = prompt | structured_llm
            return chain
            
        except Exception as e:
            print(f"⚠️  structured_output 模式初始化失败，退回传统解析路径: {e}")
    
    llm = get_llm(config=llm_config, verbose=verbose)
    base_parser = PydanticOutputParser[GeneratedScene](pydantic_object=GeneratedScene)
    parser = LLMJsonRepairOutputParser[GeneratedScene](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说作家，精通简体中文创作。

【核心要求】
1. 语言：使用简体中文，避免西化表达
2. 视角：采用第三人称有限视角，以本场景的核心角色为视角载体
3. 字数：严格控制在目标字数的±20%范围内（目标字数见输入信息）
4. 设定约束：不得修改世界观、角色配置以及章节上下文中的任何既有信息。遇到不确定事项，宁可模糊处理也不要推翻上下文。

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

【章节上下文】
章节上下文提供最近若干章的关键状态及未决悬念。生成文本必须与其一致，若要引入新设定，需要在正文中给出合理解释。

【场景记忆上下文（如有）】
如果提供了结构化的场景记忆上下文（SceneMemoryContext），其中的实体状态(entity_states)、近期事件与记忆片段(recent_events/relevant_memories，如果存在)应被视为约束性信息：
- 不得无故推翻其中已经确立的事实（例如已死亡角色突然出现、地点/时间与记忆严重冲突）
- 如需改变角色状态或关系，必须在剧情中给出清晰的过程与合理解释

【避免套路化】
- 避免陈词滥调和重复性的外貌/神态描写
- 同一人物多次出场时，变换描写角度和侧重点
- 比喻和修辞要有新意，不要反复使用相同表达

【输出格式（JSON schema）】
{format_instructions}

重要：
1. 必须严格按JSON格式输出，不要Markdown包裹，不要任何额外文字
2. 正文字段禁止出现未转义的英文双引号，必要时使用「」或\""""),
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

【章节上下文】
{chapter_context}

【场景记忆上下文（如有）】
{scene_memory_context}

【场景计划】
{scene_plan}

【前文概要】
{previous_summary}""")
    ])

    chain = prompt | llm | parser

    return chain


def generate_scene_text(
    scene_plan: ScenePlan,
    world_setting: WorldSetting,
    characters: CharactersConfig,
    previous_summary: str = "",
    chapter_context: str = "",
    scene_memory_context: Optional[SceneMemoryContext] = None,
    verbose: bool = False,
    llm_config=None,
) -> GeneratedScene:
    """
    生成场景文本

    Args:
        scene_plan: 场景计划
        world_setting: 世界观设定
        characters: 角色配置
        previous_summary: 前文概要
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置

    Returns:
        GeneratedScene对象
    """
    chain = create_scene_text_chain(verbose=verbose, llm_config=llm_config)

    # 计算字数范围
    target_words = scene_plan.estimated_words
    word_count_min = int(target_words * 0.8)
    word_count_max = int(target_words * 1.2)

    if scene_memory_context is not None:
        try:
            scene_memory_context_payload = scene_memory_context.model_dump_json(indent=2)
        except Exception:
            scene_memory_context_payload = "null"
    else:
        scene_memory_context_payload = "null"

    input_data = {
        "world_setting": world_setting.model_dump_json(indent=2),
        "characters": characters.model_dump_json(indent=2),
        "scene_plan": scene_plan.model_dump_json(indent=2),
        "scene_plan_obj": scene_plan,  # 传递对象本身，用于访问具体属性
        "scene_plan_obj.intensity": scene_plan.intensity,
        "scene_plan_obj.scene_type": scene_plan.scene_type,
        "scene_plan_obj.estimated_words": scene_plan.estimated_words,
        "previous_summary": previous_summary if previous_summary else "这是第一个场景",
        "chapter_context": chapter_context or "[]",
        "scene_memory_context": scene_memory_context_payload,
        "word_count_min": word_count_min,
        "word_count_max": word_count_max
    }
    
    if llm_config is None or not llm_config.use_structured_output:
        parser = PydanticOutputParser[GeneratedScene](pydantic_object=GeneratedScene)
        input_data["format_instructions"] = parser.get_format_instructions()

    result = chain.invoke(input_data)

    return result
