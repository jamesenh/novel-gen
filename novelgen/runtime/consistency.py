"""
一致性检测工具

开发者: jamesenh, 开发时间: 2025-11-28
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.llm import get_llm, get_structured_llm
from novelgen.models import ConsistencyReport
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_consistency_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建一致性检测链
    
    优先使用 structured_output 模式以获得更准确的结构化输出。
    """
    # 优先使用 structured_output 模式
    if llm_config is None or llm_config.use_structured_output:
        try:
            structured_llm = get_structured_llm(
                pydantic_model=ConsistencyReport,
                config=llm_config,
                verbose=verbose,
                show_prompt=show_prompt
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一位小说一致性审查员，需要比较「章节上下文」与「新章节正文」，列出潜在冲突。

【你的任务】
仔细对比上下文与新章节内容，找出任何不一致或冲突之处。

【输出要求】
1. chapter_number: 当前审查的章节编号
2. issues: 发现的问题列表，每个问题包含：
   - issue_type: 问题类型（如"设定冲突"、"角色矛盾"、"时间线错误"等）
   - description: 问题的详细描述
   - related_characters: 涉及的角色列表（可以为空数组）
   - severity: 严重程度（low/medium/high）
   - fix_instructions: 只为可自动修复的问题提供具体修复建议；若问题无法自动修复，设为 null
3. summary: 本次审查结论总结（50字以内）
4. context_snapshot: 将输入的上下文进行50字以内摘要"""),
                ("user", """【章节编号】
{chapter_number}

【上下文】
{context_payload}

【新章节全文】
{chapter_text}

请仔细审查并输出一致性检测结果。""")
            ])
            
            return prompt | structured_llm
            
        except Exception as e:
            print(f"⚠️  structured_output 模式初始化失败，退回传统解析路径: {e}")
    
    # 传统解析模式（fallback）
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[ConsistencyReport](pydantic_object=ConsistencyReport)
    parser = LLMJsonRepairOutputParser[ConsistencyReport](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位小说一致性审查员，需要比较「章节上下文」与「新章节正文」，列出潜在冲突。

【输出格式】
请严格输出以下 JSON 格式，不要使用 Markdown 包裹：
{{
  "chapter_number": 章节编号（整数）,
  "issues": [
    {{
      "issue_type": "问题类型",
      "description": "问题描述",
      "related_characters": ["角色1", "角色2"],
      "severity": "low|medium|high",
      "fix_instructions": "修复建议或null"
    }}
  ],
  "summary": "审查结论摘要",
  "context_snapshot": "上下文摘要"
}}

【注意事项】
- issues 数组可以为空，表示没有发现问题
- fix_instructions 为 null 表示无法自动修复"""),
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
    llm_config=None,
    show_prompt: bool = True
) -> ConsistencyReport:
    """执行一致性校验"""
    chain = create_consistency_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)

    return chain.invoke({
        "chapter_number": chapter_number,
        "context_payload": context_payload,
        "chapter_text": chapter_text
    })
