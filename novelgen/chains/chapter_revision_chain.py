"""
章节修订链
基于一致性检测结果对章节内容进行结构化修订
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import GeneratedChapter
from novelgen.llm import get_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_revision_chain(verbose: bool = False, llm_config=None):
    """创建章节修订链"""
    llm = get_llm(config=llm_config, verbose=verbose)
    base_parser = PydanticOutputParser[GeneratedChapter](pydantic_object=GeneratedChapter)
    parser = LLMJsonRepairOutputParser[GeneratedChapter](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说编辑，精通简体中文和小说创作。

【你的任务】
基于一致性检测报告，对一章已生成的小说进行**最小必要修订**，修复设定冲突、用词问题、逻辑错误等。

【输入说明】
1. original_chapter：原始章节的完整 JSON 结构
   - chapter_number: 章节编号（整数）
   - chapter_title: 章节标题（字符串）
   - scenes: 场景列表，每个场景有：
     - scene_number: 场景编号（整数）
     - content: 场景正文（字符串）
     - word_count: 字数统计（整数）
   - total_words: 总字数（整数）

2. revision_notes：修订说明文本
   - 来自一致性检测报告，列出需要修复的问题及建议

【输出格式（JSON schema）】
{format_instructions}

【修订约束】
1. **保持结构不变**：
   - chapter_number 和 chapter_title 必须与输入完全一致（除非明确要求修复标题错误）
   - 尽量保留场景数量和顺序，只在绝对必要时增删场景
   - 每个场景的 scene_number 应与原场景对应（若未增删场景）

2. **最小必要修改**：
   - 仅针对 revision_notes 中指出的问题进行修改
   - 优先修改场景的 content 内容，而非重写整个场景
   - 保持原文的语言风格和叙事视角
   - 避免大面积改写与问题无关的段落

3. **字数要求**：
   - 修订后的 word_count 和 total_words 必须重新计算并反映实际字数
   - 若非必要，尽量保持与原文字数接近

4. **输出格式**：
   - 必须严格按 JSON 格式输出，不要用 Markdown 包裹
   - scenes 列表中的 content 字段禁止包含未转义的英文双引号
   - 如需引号，使用「」或转义的 \\"

【注意事项】
- 如果 revision_notes 为空或没有明确的修复建议，保持原文不变
- 对于不确定的修订，宁可保守处理，不要过度修改
- 修订应保持与世界观、角色设定、前文剧情的一致性"""),
        ("user", """【原始章节（JSON）】
{original_chapter_json}

【修订说明】
{revision_notes}

请根据以上修订说明，对原始章节进行最小必要修订，并以完整的 GeneratedChapter JSON 格式输出。""")
    ])

    chain = prompt | llm | parser

    return chain


def revise_chapter(
    original_chapter: GeneratedChapter,
    revision_notes: str,
    verbose: bool = False,
    llm_config=None
) -> GeneratedChapter:
    """
    修订章节（结构化输出版本）

    Args:
        original_chapter: 原始章节的 GeneratedChapter 对象
        revision_notes: 修订说明文本
        verbose: 是否显示详细日志
        llm_config: LLM 配置

    Returns:
        修订后的 GeneratedChapter 对象
    """
    chain = create_revision_chain(verbose=verbose, llm_config=llm_config)
    parser = PydanticOutputParser[GeneratedChapter](pydantic_object=GeneratedChapter)

    # 将原始章节转为 JSON 字符串传入
    original_chapter_json = original_chapter.model_dump_json(indent=2, ensure_ascii=False)

    result = chain.invoke({
        "original_chapter_json": original_chapter_json,
        "revision_notes": revision_notes,
        "format_instructions": parser.get_format_instructions()
    })

    return result
