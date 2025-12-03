"""
角色生成链
基于世界观和主题冲突生成角色
"""
from typing import Any


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import CharactersConfig, WorldSetting, ThemeConflict
from novelgen.llm import get_llm, get_structured_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_characters_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建角色生成链
    
    优先使用 structured_output 模式（如果配置启用且后端支持），
    否则退回到传统的 PydanticOutputParser + LLMJsonRepairOutputParser 路径。
    """
    # 如果配置启用 structured_output，尝试使用该模式
    if llm_config is None or llm_config.use_structured_output:
        try:
            structured_llm = get_structured_llm(
                pydantic_model=CharactersConfig,
                config=llm_config,
                verbose=verbose,
                show_prompt=show_prompt
            )
            
            # structured_output 模式下的 prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一位专业的角色设计师。

你的任务：
1. 基于世界观和主题冲突设计主角、反派及关键配角
2. 给出支撑长篇叙事的动机、背景与关系网络

输入说明：
- 输入包含世界观JSON与主题冲突JSON
- 必须保留输入中的设定约束

输出要求：
1. 必须输出符合 JSON schema 的结构化数据
2. 必须包含 protagonist（主角）字段，类型为 Character 对象
3. 可选包含 antagonist（反派）字段，类型为 Character 对象或 null
4. 可选包含 supporting_characters（配角列表）字段，类型为 Character 对象数组
5. 每个 Character 对象必须包含：name, role, gender, appearance, personality, background, motivation
6. 可选字段：
   - age: 整数
   - abilities: 字符串数组
   - relationships: 对象，键为其他角色名称，值为关系描述字符串（例如 {{"张三": "师徒关系", "李四": "竞争对手"}}）

注意事项：
1. 角色要立体、有深度
2. 角色的动机要符合主题冲突
3. 角色之间要有关系网络
4. 角色能力要符合世界观设定
5. 主角和反派要形成对立统一"""),
                ("user", """世界观设定：
{world_setting}

主题冲突：
{theme_conflict}""")
            ])
            
            chain = prompt | structured_llm
            return chain
            
        except Exception as e:
            print(f"⚠️  structured_output 模式初始化失败，退回传统解析路径: {e}")
    
    # 传统解析路径（fallback）
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
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


def generate_characters(world_setting: WorldSetting, theme_conflict: ThemeConflict, verbose: bool = False, llm_config=None, show_prompt: bool = True) -> CharactersConfig:
    """
    生成角色

    Args:
        world_setting: 世界观设定
        theme_conflict: 主题冲突
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置
        show_prompt: verbose 模式下是否显示完整提示词

    Returns:
        CharactersConfig对象
    """
    chain = create_characters_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    
    # 准备输入参数
    input_data = {
        "world_setting": world_setting.model_dump_json(indent=2),
        "theme_conflict": theme_conflict.model_dump_json(indent=2)
    }
    
    # 如果链使用传统解析路径，需要提供 format_instructions
    # structured_output 模式下不需要此参数
    if llm_config is None or not llm_config.use_structured_output:
        parser = PydanticOutputParser[CharactersConfig](pydantic_object=CharactersConfig)
        input_data["format_instructions"] = parser.get_format_instructions()
    
    result = chain.invoke(input_data)

    return result

