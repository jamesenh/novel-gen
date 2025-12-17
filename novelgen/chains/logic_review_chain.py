"""
章节逻辑审查链

对章节内容进行逻辑连贯性审查，检测因果链断裂、动机不合理、衔接突兀等问题，
输出结构化审查报告（含评分、问题列表与修复指引）。

作者: jamesenh, 2025-12-17
开发者: jamesenh, 开发时间: 2025-12-16
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.llm import get_llm, get_structured_llm
from novelgen.models import LogicReviewReport, ChapterPlan, GeneratedChapter
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


SYSTEM_PROMPT = """你是一位专业的小说逻辑审查员，负责审查章节内容的合理性与逻辑连贯性。

【审查维度】
1. **因果链**：事件之间的因果关系是否合理、是否存在断裂
2. **人物动机**：角色的行为动机是否合理、是否符合人设
3. **场景衔接**：场景之间的过渡是否自然、是否存在跳跃感
4. **世界规则**：是否违反已建立的世界观规则（如力量体系、社会制度等）
5. **节奏控制**：铺垫、转折、高潮的节奏是否合理
6. **信息揭示**：信息揭示的顺序是否导致理解断层

【评分标准】
- 90-100分：逻辑严密，无明显问题
- 75-89分：整体合理，有轻微瑕疵但不影响阅读
- 60-74分：存在较明显的逻辑问题，需要修复
- 0-59分：存在严重逻辑问题，必须修复

【严重程度定义】
- high：严重影响故事连贯性，必须修复（如重大因果断裂、角色行为完全不合理）
- medium：影响阅读体验，建议修复（如轻微衔接问题、次要矛盾）
- low：细节问题，可选修复（如文字描述不够精确）

【输出要求】
1. overall_score: 0-100 的整数评分
2. issues: 问题列表，每项包含 issue_type、description、severity、evidence（可选）、fix_instructions（可选）
3. summary: 50-100字的审查结论"""


def create_logic_review_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建逻辑审查链
    
    优先使用 structured_output 模式以获得更准确的结构化输出。
    若初始化失败则退回传统解析模式。
    
    Args:
        verbose: 是否启用详细日志
        llm_config: LLM 配置
        show_prompt: verbose 模式下是否显示完整提示词
        
    Returns:
        可调用的链
    """
    # 优先使用 structured_output 模式
    if llm_config is None or llm_config.use_structured_output:
        try:
            structured_llm = get_structured_llm(
                pydantic_model=LogicReviewReport,
                config=llm_config,
                verbose=verbose,
                show_prompt=show_prompt
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("user", """【章节编号】
{chapter_number}

【章节计划】
{chapter_plan}

【章节正文】
{chapter_text}

【章节上下文】
{chapter_context}

请仔细审查并输出逻辑审查报告。""")
            ])
            
            return prompt | structured_llm
            
        except Exception as e:
            print(f"⚠️  structured_output 模式初始化失败，退回传统解析路径: {e}")
    
    # 传统解析模式（fallback）
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[LogicReviewReport](pydantic_object=LogicReviewReport)
    parser = LLMJsonRepairOutputParser[LogicReviewReport](parser=base_parser, llm=llm)

    fallback_system_prompt = SYSTEM_PROMPT + """

【JSON 输出格式】
请严格输出以下 JSON 格式，不要使用 Markdown 包裹：
{{
  "chapter_number": 章节编号（整数）,
  "overall_score": 评分（0-100 整数）,
  "issues": [
    {{
      "issue_type": "问题类型",
      "description": "问题描述",
      "severity": "low|medium|high",
      "evidence": "问题依据（可选）",
      "fix_instructions": "修复建议（可选）"
    }}
  ],
  "summary": "审查结论摘要"
}}"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", fallback_system_prompt),
        ("user", """【章节编号】
{chapter_number}

【章节计划】
{chapter_plan}

【章节正文】
{chapter_text}

【章节上下文】
{chapter_context}
""")
    ])

    return prompt | llm | parser


def run_logic_review(
    chapter_number: int,
    chapter_plan: str,
    chapter_text: str,
    chapter_context: str = "",
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> LogicReviewReport:
    """执行章节逻辑审查
    
    Args:
        chapter_number: 章节编号
        chapter_plan: 章节计划的 JSON 字符串
        chapter_text: 章节正文（所有场景拼接）
        chapter_context: 章节上下文（前文摘要、角色状态等）
        verbose: 是否启用详细日志
        llm_config: LLM 配置
        show_prompt: verbose 模式下是否显示完整提示词
        
    Returns:
        LogicReviewReport: 逻辑审查报告
    """
    chain = create_logic_review_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)

    return chain.invoke({
        "chapter_number": chapter_number,
        "chapter_plan": chapter_plan,
        "chapter_text": chapter_text,
        "chapter_context": chapter_context
    })
