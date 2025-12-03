"""
章节记忆工具
负责将章节文本压缩为结构化记忆
"""
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import ChapterMemoryEntry, GeneratedChapter, ChapterSummary
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_chapter_memory_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建章节记忆生成链"""
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[ChapterMemoryEntry](pydantic_object=ChapterMemoryEntry)
    parser = LLMJsonRepairOutputParser[ChapterMemoryEntry](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位严谨的故事档案整理员，需要将完整章节压缩为结构化记忆条目。

输出要求：
1. 读取提供的章节信息、场景摘要与大纲摘要
2. 汇总成可供后续章节引用的记忆记录
3. 字段解释：
   - timeline_anchor: 使用大纲提供的时间锚点
   - location_summary: 概括本章主要地点与场域变化
   - key_events: 使用短句列出推动剧情的事实
   - character_states: 仅列出关键角色 -> 其当前状态或心理
   - unresolved_threads: 列出任何尚未解决的悬念/任务
   - summary: 对整章进行150-200字概述
4. 格式必须严格遵循JSON schema:
{format_instructions}
"""),
        ("user", """【章节结构化数据】
{chapter_json}

【对应大纲摘要】
{outline_summary}

【逐场景摘要】
{scene_summaries}

【聚合摘要参考】
{aggregated_summary}
""")
    ])

    return prompt | llm | parser


def generate_chapter_memory_entry(
    chapter: GeneratedChapter,
    outline_summary: Optional[ChapterSummary],
    scene_summaries: List[str],
    aggregated_summary: str,
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> ChapterMemoryEntry:
    """调用LLM将章节压缩为记忆条目"""
    chain = create_chapter_memory_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    parser = PydanticOutputParser[ChapterMemoryEntry](pydantic_object=ChapterMemoryEntry)

    outline_payload = outline_summary.model_dump_json(indent=2) if outline_summary else "{}"

    scene_summary_payload = "\n".join(scene_summaries) if scene_summaries else "无可用场景摘要"

    result = chain.invoke({
        "chapter_json": chapter.model_dump_json(indent=2),
        "outline_summary": outline_payload,
        "scene_summaries": scene_summary_payload,
        "aggregated_summary": aggregated_summary,
        "format_instructions": parser.get_format_instructions()
    })

    return result
