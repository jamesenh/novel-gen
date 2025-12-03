"""
剧情进度评估链
评估当前剧情进度，决定是继续发展、开始收尾还是强制结束

开发者: jamesenh, 开发时间: 2025-11-28
"""
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from novelgen.models import (
    StoryProgressEvaluation,
    ThemeConflict,
    ChapterMemoryEntry,
    Outline,
)
from novelgen.llm import get_llm, get_structured_llm
from novelgen.chains.output_fixing import LLMJsonRepairOutputParser


def create_story_progress_chain(verbose: bool = False, llm_config=None, show_prompt: bool = True):
    """创建剧情进度评估链
    
    优先使用 structured_output 模式以获得更准确的结构化输出。
    """
    if llm_config is None or llm_config.use_structured_output:
        try:
            structured_llm = get_structured_llm(
                pydantic_model=StoryProgressEvaluation,
                config=llm_config,
                verbose=verbose,
                show_prompt=show_prompt
            )
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一位专业的小说策划师，负责评估长篇小说的剧情进度。

【你的任务】
根据当前的剧情发展状态，评估故事是否应该：
1. continue（继续发展）：主线冲突尚未解决，还有足够的剩余章节空间
2. wrap_up（开始收尾）：主线冲突接近解决，或剩余章节不足，应开始收束支线并推向高潮结局
3. force_end（强制结束）：已达到或超过最大章节数，必须立即结束

【评估标准】
- 若剩余章节 <= 0：必须返回 force_end
- 若剩余章节 <= 总章节数的 20%：倾向返回 wrap_up，除非主线冲突完全未触及
- 若主线冲突解决进度 >= 0.8：建议返回 wrap_up
- 否则：根据剧情发展自然程度判断

【主线冲突进度评估指南】
- 0.0-0.2：冲突刚刚展开，主角刚接触核心矛盾
- 0.3-0.5：冲突深入发展，各方势力开始交锋
- 0.6-0.7：冲突进入白热化，关键转折点出现
- 0.8-0.9：冲突接近解决，决战或最终对决在即
- 1.0：冲突已完全解决

【输出要求】
请以 JSON 格式输出以下字段：
1. evaluation_result 必须是 "continue"、"wrap_up" 或 "force_end" 之一
2. main_conflict_progress 必须是 0.0 到 1.0 之间的浮点数
3. unresolved_threads: 当前未解决的伏笔/支线列表
4. character_arc_status: 主要角色弧光状态（角色名 -> 状态描述）
5. recommendation: 解释你的判断理由

【注意】
- 不需要输出 current_chapter 和 remaining_chapters，这些由系统自动填充
- 文本中不得出现未转义的英文双引号"""),
                ("user", """【章节进度信息】
当前已完成章节数：{current_chapter}
最大允许章节数：{max_chapters}
剩余可用章节数：{remaining_chapters}

【核心冲突描述】
{main_conflict}

【最近章节记忆摘要】
{recent_memories}

【当前未解决的伏笔/支线】
{unresolved_threads}

【大纲中的结局走向】
{resolution_hint}

请评估当前剧情进度并给出建议。""")
            ])
            
            chain = prompt | structured_llm
            return chain
            
        except Exception as e:
            print(f"⚠️  structured_output 模式初始化失败，退回传统解析路径: {e}")
    
    # 传统解析模式
    llm = get_llm(config=llm_config, verbose=verbose, show_prompt=show_prompt)
    base_parser = PydanticOutputParser[StoryProgressEvaluation](pydantic_object=StoryProgressEvaluation)
    parser = LLMJsonRepairOutputParser[StoryProgressEvaluation](parser=base_parser, llm=llm)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位专业的小说策划师，负责评估长篇小说的剧情进度。

【你的任务】
根据当前的剧情发展状态，评估故事是否应该：
1. continue（继续发展）：主线冲突尚未解决，还有足够的剩余章节空间
2. wrap_up（开始收尾）：主线冲突接近解决，或剩余章节不足，应开始收束支线并推向高潮结局
3. force_end（强制结束）：已达到或超过最大章节数，必须立即结束

【评估标准】
- 若剩余章节 <= 0：必须返回 force_end
- 若剩余章节 <= 总章节数的 20%：倾向返回 wrap_up，除非主线冲突完全未触及
- 若主线冲突解决进度 >= 0.8：建议返回 wrap_up
- 否则：根据剧情发展自然程度判断

【主线冲突进度评估指南】
- 0.0-0.2：冲突刚刚展开，主角刚接触核心矛盾
- 0.3-0.5：冲突深入发展，各方势力开始交锋
- 0.6-0.7：冲突进入白热化，关键转折点出现
- 0.8-0.9：冲突接近解决，决战或最终对决在即
- 1.0：冲突已完全解决

【输出格式】
请严格输出以下 JSON 格式，不要使用 Markdown 包裹：
{{
  "evaluation_result": "continue|wrap_up|force_end",
  "main_conflict_progress": 0.0到1.0之间的浮点数,
  "unresolved_threads": ["伏笔1", "伏笔2"],
  "character_arc_status": {{"角色名": "状态描述"}},
  "recommendation": "判断理由说明"
}}

【注意事项】
1. 不需要输出 current_chapter 和 remaining_chapters，系统会自动填充
2. evaluation_result 必须是 "continue"、"wrap_up" 或 "force_end" 之一
3. main_conflict_progress 必须是 0.0 到 1.0 之间的浮点数
4. 文本中不得出现未转义的英文双引号"""),
        ("user", """【章节进度信息】
当前已完成章节数：{current_chapter}
最大允许章节数：{max_chapters}
剩余可用章节数：{remaining_chapters}

【核心冲突描述】
{main_conflict}

【最近章节记忆摘要】
{recent_memories}

【当前未解决的伏笔/支线】
{unresolved_threads}

【大纲中的结局走向】
{resolution_hint}

请评估当前剧情进度并给出建议。""")
    ])

    chain = prompt | llm | parser
    return chain


def evaluate_story_progress(
    current_chapter: int,
    max_chapters: int,
    theme_conflict: ThemeConflict,
    outline: Outline,
    chapter_memories: List[ChapterMemoryEntry],
    verbose: bool = False,
    llm_config=None,
    show_prompt: bool = True
) -> StoryProgressEvaluation:
    """
    评估剧情进度，决定是继续、收尾还是强制结束
    
    Args:
        current_chapter: 当前已完成的章节数
        max_chapters: 最大允许章节数
        theme_conflict: 主题与冲突配置
        outline: 当前大纲
        chapter_memories: 章节记忆列表
        verbose: 是否输出详细日志
        llm_config: LLM配置
        show_prompt: verbose 模式下是否显示完整提示词
    
    Returns:
        StoryProgressEvaluation 对象
    """
    chain = create_story_progress_chain(verbose=verbose, llm_config=llm_config, show_prompt=show_prompt)
    
    # 计算剩余章节
    remaining_chapters = max_chapters - current_chapter
    
    # 提取最近 N 章的记忆摘要
    recent_count = min(5, len(chapter_memories))
    recent_memories_text = ""
    if chapter_memories:
        recent = chapter_memories[-recent_count:]
        memory_parts = []
        for mem in recent:
            events = ", ".join(mem.key_events[:3]) if mem.key_events else "无"
            memory_parts.append(f"第{mem.chapter_number}章「{mem.chapter_title}」：{mem.summary[:100]}... 关键事件：{events}")
        recent_memories_text = "\n".join(memory_parts)
    else:
        recent_memories_text = "暂无章节记忆"
    
    # 收集未解决的伏笔
    unresolved = []
    for mem in chapter_memories:
        unresolved.extend(mem.unresolved_threads)
    # 去重并限制数量
    unresolved = list(set(unresolved))[:10]
    unresolved_text = "\n".join(f"- {t}" for t in unresolved) if unresolved else "暂无明显未解决的伏笔"
    
    # 构建输入数据
    input_data = {
        "current_chapter": current_chapter,
        "max_chapters": max_chapters,
        "remaining_chapters": remaining_chapters,
        "main_conflict": theme_conflict.main_conflict,
        "recent_memories": recent_memories_text,
        "unresolved_threads": unresolved_text,
        "resolution_hint": outline.resolution if outline else "未定义"
    }
    
    result = chain.invoke(input_data)
    
    # 补充计算字段
    if isinstance(result, StoryProgressEvaluation):
        # 确保 current_chapter 和 remaining_chapters 正确
        result.current_chapter = current_chapter
        result.remaining_chapters = remaining_chapters
    
    return result

