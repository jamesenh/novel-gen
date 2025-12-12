"""
角色生成链
基于世界观和主题冲突生成角色
"""
import os
from typing import Any, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from novelgen.chains.output_fixing import LLMJsonRepairOutputParser
from novelgen.llm import get_llm, get_structured_llm
from novelgen.models import CharactersConfig, ThemeConflict, WorldSetting


def _resolve_character_count(num_characters: Optional[int]) -> int:
    """解析角色生成数量，支持环境变量覆盖并限制范围"""
    default_count = 5
    env_value = os.getenv("CHARACTERS_DEFAULT_COUNT")
    if env_value:
        try:
            default_count = max(3, min(12, int(env_value)))
        except ValueError:
            pass
    if num_characters is None:
        return default_count
    return max(3, min(12, num_characters))


def create_characters_chain(
    target_count: int,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True,
):
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
                show_prompt=show_prompt,
            )

            # structured_output 模式下的 prompt
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """你是一位专业的角色设计师。

你的任务：
1. 基于世界观和主题冲突设计主角、反派及关键配角
2. 给出支撑长篇叙事的动机、背景与关系网络
3. 总角色数量（含主角/反派/配角）必须达到 {target_character_count} 个，不足时补足配角

输入说明：
- 输入包含世界观JSON与主题冲突JSON
- 必须保留输入中的设定约束

输出要求：
1. 必须输出符合 JSON schema 的结构化数据
2. 必须包含 protagonist（主角）字段，类型为 Character 对象
3. 可选包含 antagonist（反派）字段，类型为 Character 对象或 null
4. 可选包含 supporting_characters（配角列表）字段，类型为 Character 对象数组，按重要性排序
5. supporting_characters 数量需使总角色数达到 {target_character_count}（含主角/反派），不足时增加配角
6. 每个 Character 对象必须包含：name, role, gender, appearance, personality, background, motivation
7. 可选字段：
   - age: 整数
   - abilities: 字符串数组
   - relationships: 对象，键为其他角色名称，值为关系描述字符串（详细描述，可较长）
   - relationships_brief: 对象，键为其他角色名称，值为简短关系标签（≤12字，用于可视化展示，例如 {{"张三": "师徒", "李四": "宿敌"}}）

注意事项：
1. 角色要立体、有深度
2. 角色的动机要符合主题冲突
3. 角色之间要有关系网络，同时提供 relationships（详细描述）和 relationships_brief（≤12字的简短标签）
4. 角色能力要符合世界观设定
5. 主角和反派要形成对立统一""",
                    ),
                    (
                        "user",
                        """世界观设定：
{world_setting}

主题冲突：
{theme_conflict}""",
                    ),
                ]
            )

            chain = prompt | structured_llm
            return chain

        except Exception as e:
            print(f"⚠️  structured_output 模式初始化失败，退回传统解析路径: {e}")

    # 传统解析路径（fallback）
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[CharactersConfig](pydantic_object=CharactersConfig)
    parser = LLMJsonRepairOutputParser[CharactersConfig](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """你是一位专业的角色设计师。

你的任务：
1. 基于世界观和主题冲突设计主角、反派及关键配角
2. 给出支撑长篇叙事的动机、背景与关系网络
3. 总角色数量（含主角/反派/配角）必须达到 {target_character_count} 个，不足时补足配角

输入说明：
- 输入包含世界观JSON与主题冲突JSON
- 必须保留输入中的设定约束

输出格式（JSON schema）：
{format_instructions}

注意事项：
1. 角色要立体、有深度
2. 角色的动机要符合主题冲突
3. 角色之间要有关系网络，同时提供 relationships（详细描述）和 relationships_brief（≤12字的简短标签，用于可视化展示）
4. 角色能力要符合世界观设定
5. 主角和反派要形成对立统一
6. supporting_characters 数量需使总角色数达到 {target_character_count}，按重要性排序
7. 严格按照JSON格式输出，不要使用Markdown包裹
8. 正文内容如需引用称谓或势力名称，统一使用「」或写成\", 严禁出现未转义的英文双引号""",
            ),
            (
                "user",
                """世界观设定：
{world_setting}

主题冲突：
{theme_conflict}""",
            ),
        ]
    )

    chain = prompt | llm | parser

    return chain


def generate_characters(
    world_setting: WorldSetting,
    theme_conflict: ThemeConflict,
    num_characters: Optional[int] = None,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True,
) -> CharactersConfig:
    """
    生成角色

    Args:
        world_setting: 世界观设定
        theme_conflict: 主题冲突
        num_characters: 目标角色数量（含主角/反派/配角），None 时使用默认值
        verbose: 是否输出详细日志（提示词、时间、token）
        llm_config: LLM配置
        show_prompt: verbose 模式下是否显示完整提示词

    Returns:
        CharactersConfig对象
    """
    target_count = _resolve_character_count(num_characters)
    chain = create_characters_chain(
        target_count=target_count,
        verbose=verbose,
        llm_config=llm_config,
        show_prompt=show_prompt,
    )

    # 准备输入参数
    input_data: dict[str, Any] = {
        "world_setting": world_setting.model_dump_json(indent=2),
        "theme_conflict": theme_conflict.model_dump_json(indent=2),
        "target_character_count": target_count,
    }

    # 如果链使用传统解析路径，需要提供 format_instructions
    # structured_output 模式下不需要此参数
    if llm_config is None or not llm_config.use_structured_output:
        parser = PydanticOutputParser[CharactersConfig](pydantic_object=CharactersConfig)
        input_data["format_instructions"] = parser.get_format_instructions()

    result = chain.invoke(input_data)

    supporting = list(result.supporting_characters or [])
    antagonist_exists = result.antagonist is not None
    required_supporting = max(0, target_count - 1 - (1 if antagonist_exists else 0))
    current_total = 1 + (1 if antagonist_exists else 0) + len(supporting)

    if current_total < target_count:
        raise ValueError(
            f"生成的角色数量不足，期望 {target_count} 个，实际 {current_total} 个，请重试"
        )

    if len(supporting) > required_supporting:
        result.supporting_characters = supporting[:required_supporting]
    else:
        result.supporting_characters = supporting

    return result
