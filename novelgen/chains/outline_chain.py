"""
大纲生成链
基于世界观、主题冲突和角色生成故事大纲
"""
import re
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
5. 为每个章节补充 timeline_anchor（例如「T+3 天」「第5夜」）以及 dependencies（依赖的章节/事件列表，即本章开始时必须已发生的事实）
6. 若章节出现闪回或倒叙，需在timeline_anchor中标注「闪回/回忆」
7. 严格按照JSON格式输出，不要使用Markdown包裹
8. 禁止输出未转义的英文双引号，使用「」或\"表达引用"""),
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

    _validate_outline_metadata(result)
    return result


def _extract_timeline_value(anchor: str):
    if not anchor:
        return None
    match = re.search(r"(-?\\d+)", anchor)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _validate_outline_metadata(outline: Outline):
    """基础校验：时间线递进与依赖引用合法性"""
    last_value = None
    for chapter in outline.chapters:
        if not chapter.timeline_anchor:
            raise ValueError(f"章节 {chapter.chapter_number} 缺少 timeline_anchor")

        value = _extract_timeline_value(chapter.timeline_anchor)
        if value is not None and last_value is not None and value < last_value:
            anchor = chapter.timeline_anchor.lower()
            if all(flag not in anchor for flag in ("闪回", "回忆", "flashback")):
                raise ValueError(
                    f"章节 {chapter.chapter_number} 的 timeline_anchor ({chapter.timeline_anchor}) 早于上一章且未标注闪回"
                )
        if value is not None:
            last_value = value

        for dep in chapter.dependencies:
            if dep.chapter_number is not None and dep.chapter_number >= chapter.chapter_number:
                raise ValueError(
                    f"章节 {chapter.chapter_number} 的依赖 {dep.chapter_number} 不合法（不能依赖自身或未来章节）"
                )

    return outline
