"""
大纲生成链
基于世界观、主题冲突和角色生成故事大纲

更新: 2025-11-28 - 添加动态章节支持（generate_initial_outline, extend_outline）
"""
import re
from typing import List, Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import (
    Outline, WorldSetting, ThemeConflict, CharactersConfig,
    ChapterSummary, ChapterMemoryEntry, StoryProgressEvaluation
)
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_outline_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建大纲生成链"""
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
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
    llm_config=None,
    show_prompt: bool = True
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
        show_prompt: verbose 模式下是否显示完整提示词

    Returns:
        Outline对象
    """
    chain = create_outline_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
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


# ==================== 动态章节扩展支持 ====================

def create_initial_outline_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建初始大纲生成链（仅生成开篇阶段）
    
    与完整大纲不同，初始大纲只规划开篇章节，高潮和结局保持占位描述。
    """
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[Outline](pydantic_object=Outline)
    parser = LLMJsonRepairOutputParser[Outline](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的故事大纲设计师，擅长规划长篇小说的开篇结构。

【你的任务】
为一部长篇小说规划「开篇阶段」的大纲，只需要详细规划前 {num_chapters} 章。
高潮和结局部分保持概括性描述即可，后续会根据剧情发展动态扩展。

【输入说明】
- 输入包含世界观、主题冲突、角色配置 JSON
- 这是一部可能有数十章的长篇小说，当前只规划开篇

【输出格式（JSON schema）】
{format_instructions}

【章节规划要求】
1. 只生成 {num_chapters} 个章节的详细计划
2. 章节编号从 1 开始连续递增
3. 开篇章节要完成：世界观引入、主角出场、核心冲突初现
4. 为每个章节补充 timeline_anchor（例如「T+0 天」「T+3 天」）
5. 补充 dependencies（本章开始前必须已发生的事实）

【大纲结构要求】
1. story_premise：完整的故事前提
2. beginning：详细的开端描述（对应当前规划的章节）
3. development：概括性的发展方向（后续会扩展）
4. climax：概括性的高潮走向（后续会扩展）
5. resolution：概括性的结局方向（后续会扩展）

【注意事项】
1. 严格按照 JSON 格式输出，不要使用 Markdown 包裹
2. 禁止输出未转义的英文双引号，使用「」或 \" 表达引用
3. is_complete 必须设为 false（因为这是初始大纲）
4. current_phase 必须设为 "opening" """),
        ("user", """世界观设定：
{world_setting}

主题冲突：
{theme_conflict}

角色配置：
{characters}

开篇章节数：{num_chapters}""")
    ])

    chain = prompt | llm | parser
    return chain


def generate_initial_outline(
    world_setting: WorldSetting,
    theme_conflict: ThemeConflict,
    characters: CharactersConfig,
    initial_chapters: int = 5,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> Outline:
    """
    生成初始大纲（仅开篇阶段）
    
    用于动态章节模式，只规划开篇章节，后续根据剧情发展扩展。
    
    Args:
        world_setting: 世界观设定
        theme_conflict: 主题冲突
        characters: 角色配置
        initial_chapters: 初始章节数（开篇阶段）
        verbose: 是否输出详细日志
        llm_config: LLM 配置
        show_prompt: verbose 模式下是否显示完整提示词
    
    Returns:
        Outline 对象（is_complete=False, current_phase="opening"）
    """
    chain = create_initial_outline_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    parser = PydanticOutputParser[Outline](pydantic_object=Outline)

    result = chain.invoke({
        "world_setting": world_setting.model_dump_json(indent=2),
        "theme_conflict": theme_conflict.model_dump_json(indent=2),
        "characters": characters.model_dump_json(indent=2),
        "num_chapters": initial_chapters,
        "format_instructions": parser.get_format_instructions()
    })

    # 确保标记为未完成
    result.is_complete = False
    result.current_phase = "opening"
    
    _validate_outline_metadata(result)
    return result


def create_extend_outline_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建大纲扩展链
    
    根据已有大纲和剧情进度，生成后续章节。
    """
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[Outline](pydantic_object=Outline)
    parser = LLMJsonRepairOutputParser[Outline](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的故事大纲设计师，负责扩展长篇小说的大纲。

【你的任务】
基于已有的大纲和剧情发展，为小说生成后续章节的计划。

【扩展模式】
根据 extension_mode 决定扩展方式：
- "continue"：继续发展阶段，生成 3-5 章发展剧情
- "wrap_up"：开始收尾，生成 2-3 章高潮+结局
- "force_end"：强制结束，生成 1-2 章压缩结局

【输入说明】
- 已有大纲的完整信息
- 最近章节的记忆摘要
- 未解决的伏笔/支线
- 剩余可用章节数

【输出格式（JSON schema）】
{format_instructions}

【章节规划要求】
1. 新章节编号必须从 {next_chapter_number} 开始连续递增
2. 新章节要承接前文剧情，保持连贯性
3. 处理未解决的伏笔（收尾模式下要收束支线）
4. 为每个章节补充 timeline_anchor 和 dependencies

【大纲结构要求】
1. 保留原有的 story_premise 和 beginning
2. 根据扩展内容更新 development
3. 若是收尾模式，详细规划 climax 和 resolution
4. chapters 列表必须包含所有章节（原有 + 新增）

【注意事项】
1. 严格按照 JSON 格式输出，不要使用 Markdown 包裹
2. 禁止输出未转义的英文双引号
3. 收尾模式（wrap_up/force_end）时，is_complete 设为 true
4. 更新 current_phase 为对应阶段"""),
        ("user", """【已有大纲】
{existing_outline}

【扩展模式】
{extension_mode}

【剩余可用章节数】
{remaining_chapters}

【最近章节记忆】
{recent_memories}

【未解决的伏笔/支线】
{unresolved_threads}

【下一章编号】
{next_chapter_number}

【扩展建议】
{recommendation}

请生成扩展后的完整大纲。""")
    ])

    chain = prompt | llm | parser
    return chain


def extend_outline(
    existing_outline: Outline,
    evaluation: StoryProgressEvaluation,
    chapter_memories: List[ChapterMemoryEntry],
    remaining_chapters: int,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> Outline:
    """
    扩展大纲
    
    根据剧情进度评估结果，生成后续章节的大纲。
    
    Args:
        existing_outline: 现有大纲
        evaluation: 剧情进度评估结果
        chapter_memories: 章节记忆列表
        remaining_chapters: 剩余可用章节数
        verbose: 是否输出详细日志
        llm_config: LLM 配置
        show_prompt: verbose 模式下是否显示完整提示词
    
    Returns:
        扩展后的 Outline 对象
    """
    chain = create_extend_outline_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    parser = PydanticOutputParser[Outline](pydantic_object=Outline)
    
    # 计算下一章编号
    next_chapter_number = len(existing_outline.chapters) + 1
    
    # 提取最近章节记忆
    recent_count = min(5, len(chapter_memories))
    recent_memories_text = ""
    if chapter_memories:
        recent = chapter_memories[-recent_count:]
        memory_parts = []
        for mem in recent:
            events = ", ".join(mem.key_events[:3]) if mem.key_events else "无"
            threads = ", ".join(mem.unresolved_threads[:2]) if mem.unresolved_threads else "无"
            memory_parts.append(
                f"第{mem.chapter_number}章「{mem.chapter_title}」：{mem.summary[:150]}... "
                f"关键事件：{events}；未解决：{threads}"
            )
        recent_memories_text = "\n".join(memory_parts)
    else:
        recent_memories_text = "暂无章节记忆"
    
    # 收集未解决的伏笔
    unresolved_text = "\n".join(f"- {t}" for t in evaluation.unresolved_threads) if evaluation.unresolved_threads else "暂无"
    
    result = chain.invoke({
        "existing_outline": existing_outline.model_dump_json(indent=2),
        "extension_mode": evaluation.evaluation_result,
        "remaining_chapters": remaining_chapters,
        "recent_memories": recent_memories_text,
        "unresolved_threads": unresolved_text,
        "next_chapter_number": next_chapter_number,
        "recommendation": evaluation.recommendation,
        "format_instructions": parser.get_format_instructions()
    })
    
    # 根据扩展模式设置状态
    if evaluation.evaluation_result in ("wrap_up", "force_end"):
        result.is_complete = True
        result.current_phase = "resolution"
    else:
        result.is_complete = False
        result.current_phase = "development"
    
    # 验证新增章节
    _validate_outline_metadata(result)
    
    return result
