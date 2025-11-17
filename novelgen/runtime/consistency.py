"""
一致性检测工具
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.llm import get_llm
from novelgen.models import ConsistencyReport
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_consistency_chain(verbose: bool = False, llm_config=None):
    """创建一致性检测链"""
    llm = get_llm(config=llm_config, verbose=verbose)
    base_parser = PydanticOutputParser[ConsistencyReport](pydantic_object=ConsistencyReport)
    parser = LLMJsonRepairOutputParser[ConsistencyReport](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位小说一致性审查员，需要比较「章节上下文」与「新章节正文」，列出潜在冲突。

请输出JSON（schema如下）：
{format_instructions}

字段说明：
- issues: 列出每个冲突（类型、描述、涉及角色、severity、修复建议）
  - fix_instructions: 只为可自动修复的问题提供具体修复建议；若问题无法自动修复或需要人工判断，将此字段留空（null）
- summary: 本次审查结论总结
- context_snapshot: 将输入的上下文进行50字以内摘要，方便追溯"""),
        ("user", """【章节编号】
{chapter_number}

【上下文】
{context_payload}

【新章节全文】
{chapter_text}
""")
    ])

    return prompt | llm | parser


def run_consistency_check(
    chapter_number: int,
    context_payload: str,
    chapter_text: str,
    verbose: bool = False,
    llm_config=None
) -> ConsistencyReport:
    """执行一致性校验"""
    chain = create_consistency_chain(verbose=verbose, llm_config=llm_config)
    parser = PydanticOutputParser[ConsistencyReport](pydantic_object=ConsistencyReport)

    return chain.invoke({
        "chapter_number": chapter_number,
        "context_payload": context_payload,
        "chapter_text": chapter_text,
        "format_instructions": parser.get_format_instructions()
    })
