"""
意图识别与范围解析模块

提供:
1. 结构化意图对象（ParsedIntent）
2. 章节范围解析（支持中文数字）
3. LLM 意图识别链（结构化输出）
4. 规则解析（作为 LLM 的兜底）
5. 歧义检测与澄清问题生成

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import re
from typing import Optional, List, Tuple, Literal, Dict
from enum import Enum

from pydantic import BaseModel, Field


# ==================== 中文数字映射 ====================

CHINESE_DIGIT_MAP = {
    "零": 0, "〇": 0,
    "一": 1, "壹": 1,
    "二": 2, "贰": 2, "两": 2,
    "三": 3, "叁": 3,
    "四": 4, "肆": 4,
    "五": 5, "伍": 5,
    "六": 6, "陆": 6,
    "七": 7, "柒": 7,
    "八": 8, "捌": 8,
    "九": 9, "玖": 9,
    "十": 10, "拾": 10,
    "百": 100, "佰": 100,
}


def chinese_to_arabic(chinese_str: str) -> Optional[int]:
    """将中文数字转换为阿拉伯数字
    
    支持:
    - 个位数: 一、二、三...九
    - 十位数: 十、十一、二十、二十一...九十九
    - 百位数: 一百、一百零一、一百二十三...
    
    Args:
        chinese_str: 中文数字字符串
        
    Returns:
        阿拉伯数字，无法解析时返回 None
    """
    if not chinese_str:
        return None
    
    # 先尝试直接作为阿拉伯数字解析
    try:
        return int(chinese_str)
    except ValueError:
        pass
    
    chinese_str = chinese_str.strip()
    result = 0
    temp = 0
    
    i = 0
    while i < len(chinese_str):
        char = chinese_str[i]
        
        if char in CHINESE_DIGIT_MAP:
            digit = CHINESE_DIGIT_MAP[char]
            
            if digit == 10:  # 十
                if temp == 0:
                    temp = 1  # "十" 开头表示 10
                result += temp * 10
                temp = 0
            elif digit == 100:  # 百
                if temp == 0:
                    temp = 1
                result += temp * 100
                temp = 0
            else:
                temp = digit
        else:
            # 不认识的字符
            return None
        
        i += 1
    
    result += temp
    return result if result > 0 else None


# ==================== 章节范围数据结构 ====================

class ChapterScope(BaseModel):
    """章节范围
    
    表示一个章节范围，支持单章节和范围两种形式
    """
    start: int = Field(description="起始章节编号（包含）")
    end: int = Field(description="结束章节编号（包含）")
    
    @property
    def is_single(self) -> bool:
        """是否为单章节"""
        return self.start == self.end
    
    @property
    def count(self) -> int:
        """章节数量"""
        return self.end - self.start + 1
    
    def __str__(self) -> str:
        if self.is_single:
            return f"第{self.start}章"
        return f"第{self.start}-{self.end}章"


def parse_chapter_scope(text: str) -> Optional[ChapterScope]:
    """从文本中解析章节范围
    
    支持的模式:
    - "前N章" / "前三章" -> ChapterScope(1, N)
    - "第N章" / "第三章" -> ChapterScope(N, N)
    - "第M-N章" / "第M到N章" / "从M到N章" -> ChapterScope(M, N)
    - "第十二章到第十五章" -> ChapterScope(12, 15)
    - "2到5章" / "2-5章" -> ChapterScope(2, 5)
    
    Args:
        text: 输入文本
        
    Returns:
        ChapterScope 或 None（无法解析时）
    """
    text = text.strip()
    
    # 模式1: "前N章" / "前三章"
    match = re.search(r"前\s*([一二三四五六七八九十百零〇壹贰叁肆伍陆柒捌玖拾佰两0-9]+)\s*章", text)
    if match:
        n = chinese_to_arabic(match.group(1))
        if n:
            return ChapterScope(start=1, end=n)
    
    # 模式2: "第M-N章" / "第M到N章" / "第M至N章"（阿拉伯数字）
    match = re.search(r"第?\s*(\d+)\s*[-到至]\s*(\d+)\s*章", text)
    if match:
        start = int(match.group(1))
        end = int(match.group(2))
        if start <= end:
            return ChapterScope(start=start, end=end)
    
    # 模式3: "第M章到第N章" / "从第M章到第N章"（阿拉伯数字）
    match = re.search(r"第\s*(\d+)\s*章\s*[-到至]\s*第?\s*(\d+)\s*章", text)
    if match:
        start = int(match.group(1))
        end = int(match.group(2))
        if start <= end:
            return ChapterScope(start=start, end=end)
    
    # 模式4: 中文数字范围 "第十二章到第十五章" / "第三章到第五章"
    match = re.search(
        r"第\s*([一二三四五六七八九十百零〇壹贰叁肆伍陆柒捌玖拾佰两]+)\s*章?\s*[-到至]\s*第?\s*([一二三四五六七八九十百零〇壹贰叁肆伍陆柒捌玖拾佰两]+)\s*章",
        text
    )
    if match:
        start = chinese_to_arabic(match.group(1))
        end = chinese_to_arabic(match.group(2))
        if start and end and start <= end:
            return ChapterScope(start=start, end=end)
    
    # 模式5: 中文数字范围 "三到五章" / "三至五章"
    match = re.search(
        r"([一二三四五六七八九十百零〇壹贰叁肆伍陆柒捌玖拾佰两]+)\s*[-到至]\s*([一二三四五六七八九十百零〇壹贰叁肆伍陆柒捌玖拾佰两]+)\s*章",
        text
    )
    if match:
        start = chinese_to_arabic(match.group(1))
        end = chinese_to_arabic(match.group(2))
        if start and end and start <= end:
            return ChapterScope(start=start, end=end)
    
    # 模式6: 单章节 "第N章"（阿拉伯数字）
    match = re.search(r"第\s*(\d+)\s*章", text)
    if match:
        n = int(match.group(1))
        return ChapterScope(start=n, end=n)
    
    # 模式7: 单章节（中文数字）"第三章" / "第十章"
    match = re.search(r"第\s*([一二三四五六七八九十百零〇壹贰叁肆伍陆柒捌玖拾佰两]+)\s*章", text)
    if match:
        n = chinese_to_arabic(match.group(1))
        if n:
            return ChapterScope(start=n, end=n)
    
    return None


# ==================== 意图目标类型 ====================

class IntentTarget(str, Enum):
    """意图目标类型"""
    WORLD = "world"                      # 世界观
    THEME_CONFLICT = "theme_conflict"    # 主题冲突
    CHARACTERS = "characters"            # 人物角色
    OUTLINE = "outline"                  # 大纲
    CHAPTER_PLAN = "chapter_plan"        # 章节计划
    CHAPTER_TEXT = "chapter_text"        # 章节正文
    EXPORT = "export"                    # 导出
    FULL_WORKFLOW = "full_workflow"      # 全流程
    STATUS = "status"                    # 状态查询
    HELP = "help"                        # 帮助
    QUERY = "query"                      # 图谱查询
    UNKNOWN = "unknown"                  # 未知


class IntentMode(str, Enum):
    """意图模式（用于区分计划与正文）"""
    PLAN = "plan"       # 计划/规划
    TEXT = "text"       # 正文/内容
    UNSPECIFIED = "unspecified"  # 未指定


# ==================== 结构化意图对象 ====================

class ClarificationQuestion(BaseModel):
    """澄清问题"""
    question: str = Field(description="向用户提出的问题")
    options: List[str] = Field(default_factory=list, description="可选项（如有）")


class ParsedIntent(BaseModel):
    """结构化意图对象
    
    LLM 或规则解析器输出的标准化意图表示
    """
    # 基本信息
    target: IntentTarget = Field(description="意图目标类型")
    mode: IntentMode = Field(
        default=IntentMode.UNSPECIFIED, 
        description="意图模式：计划/正文/未指定"
    )
    
    # 范围约束
    chapter_scope: Optional[ChapterScope] = Field(
        default=None, 
        description="章节范围约束（如有）"
    )
    
    # 置信度与歧义
    confidence: float = Field(
        default=1.0, 
        ge=0.0, le=1.0,
        description="解析置信度（0-1）"
    )
    is_ambiguous: bool = Field(
        default=False, 
        description="是否存在歧义需要澄清"
    )
    ambiguity_reason: Optional[str] = Field(
        default=None, 
        description="歧义原因说明"
    )
    
    # 澄清问题
    clarification_questions: List[ClarificationQuestion] = Field(
        default_factory=list,
        description="需要向用户提出的澄清问题"
    )
    
    # 原始输入
    original_input: str = Field(default="", description="用户原始输入")
    
    # 解析来源
    source: Literal["llm", "rule", "hybrid"] = Field(
        default="rule",
        description="解析来源：llm/rule/hybrid"
    )
    
    def needs_clarification(self) -> bool:
        """是否需要澄清"""
        return self.is_ambiguous or len(self.clarification_questions) > 0
    
    def get_echo_message(self) -> str:
        """生成解析结果回显消息"""
        parts = []
        
        # 目标
        target_names = {
            IntentTarget.WORLD: "世界观",
            IntentTarget.THEME_CONFLICT: "主题冲突",
            IntentTarget.CHARACTERS: "人物角色",
            IntentTarget.OUTLINE: "大纲",
            IntentTarget.CHAPTER_PLAN: "章节计划",
            IntentTarget.CHAPTER_TEXT: "章节正文",
            IntentTarget.EXPORT: "导出",
            IntentTarget.FULL_WORKFLOW: "完整小说",
            IntentTarget.STATUS: "状态查询",
            IntentTarget.HELP: "帮助",
            IntentTarget.QUERY: "信息查询",
            IntentTarget.UNKNOWN: "未知",
        }
        parts.append(f"目标={target_names.get(self.target, str(self.target))}")
        
        # 模式
        if self.mode != IntentMode.UNSPECIFIED:
            mode_names = {IntentMode.PLAN: "计划", IntentMode.TEXT: "正文"}
            parts.append(f"模式={mode_names.get(self.mode, str(self.mode))}")
        
        # 范围
        if self.chapter_scope:
            parts.append(f"范围={self.chapter_scope}")
        
        return "；".join(parts)


# ==================== LLM 意图识别链输出模型 ====================

class LLMIntentOutput(BaseModel):
    """LLM 意图识别输出（用于 structured output）
    
    注意：这个模型专门用于 LLM with_structured_output，
    字段设计需考虑 LLM 的理解能力
    """
    target: str = Field(
        description="识别到的目标，可选值: world, theme_conflict, characters, outline, chapter_plan, chapter_text, export, full_workflow, status, help, query, unknown"
    )
    mode: str = Field(
        default="unspecified",
        description="模式，可选值: plan（计划/规划）, text（正文/内容）, unspecified（未指定）"
    )
    chapter_start: Optional[int] = Field(
        default=None,
        description="章节范围起始编号（如有），例如「前3章」为 1，「第5章」为 5"
    )
    chapter_end: Optional[int] = Field(
        default=None,
        description="章节范围结束编号（如有），例如「前3章」为 3，「第5章」为 5，「第2到5章」为 5"
    )
    is_ambiguous: bool = Field(
        default=False,
        description="是否存在歧义需要向用户澄清"
    )
    ambiguity_reason: Optional[str] = Field(
        default=None,
        description="如存在歧义，说明歧义原因"
    )
    suggested_question: Optional[str] = Field(
        default=None,
        description="如存在歧义，建议向用户提出的澄清问题"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0, le=1.0,
        description="解析置信度（0-1），低于 0.5 表示不确定"
    )


# ==================== 规则解析器 ====================

# 目标关键词映射
TARGET_KEYWORDS = {
    # 世界观
    IntentTarget.WORLD: ["世界观", "世界", "世界设定", "背景", "背景设定"],
    # 主题冲突
    IntentTarget.THEME_CONFLICT: ["主题", "主题冲突", "冲突", "核心冲突"],
    # 人物角色
    IntentTarget.CHARACTERS: ["人物", "角色", "人物角色", "角色设定", "人物设定", "主角", "配角"],
    # 大纲
    IntentTarget.OUTLINE: ["大纲", "故事大纲", "剧情大纲", "章节大纲"],
    # 章节计划
    IntentTarget.CHAPTER_PLAN: ["章节计划", "场景计划", "详细计划"],
    # 章节正文
    IntentTarget.CHAPTER_TEXT: ["章节正文", "正文", "章节内容", "内容"],
    # 导出
    IntentTarget.EXPORT: ["导出", "输出", "export"],
}

# 全流程触发词
FULL_WORKFLOW_KEYWORDS = [
    "开始生成", "继续生成", "一键生成", "跑完整流程", 
    "完整生成", "全部生成", "从头生成", "run", "resume",
    "继续", "开始",
]

# 模式关键词
MODE_PLAN_KEYWORDS = ["计划", "规划", "planning", "plan"]
MODE_TEXT_KEYWORDS = ["正文", "内容", "text", "content", "写"]


def parse_intent_by_rules(user_input: str) -> ParsedIntent:
    """基于规则解析用户意图
    
    作为 LLM 意图识别的兜底方案
    
    Args:
        user_input: 用户输入
        
    Returns:
        ParsedIntent 对象
    """
    input_lower = user_input.lower()
    
    # 1. 解析章节范围
    chapter_scope = parse_chapter_scope(user_input)
    
    # 2. 解析模式
    mode = IntentMode.UNSPECIFIED
    if any(kw in input_lower for kw in MODE_PLAN_KEYWORDS):
        mode = IntentMode.PLAN
    elif any(kw in input_lower for kw in MODE_TEXT_KEYWORDS):
        mode = IntentMode.TEXT
    
    # 3. 检查是否是全流程生成
    for kw in FULL_WORKFLOW_KEYWORDS:
        if kw in input_lower:
            # 检查是否有明确的目标产物词
            target = _extract_target_from_keywords(user_input)
            if target is None:
                return ParsedIntent(
                    target=IntentTarget.FULL_WORKFLOW,
                    mode=mode,
                    chapter_scope=chapter_scope,
                    original_input=user_input,
                    source="rule"
                )
    
    # 4. 检查状态查询（优先级高于“生成”动词，避免将“生成进度”误判为执行生成）
    status_keywords = ["状态", "进度", "完成情况", "完成度", "status"]
    if any(kw in input_lower for kw in status_keywords):
        return ParsedIntent(
            target=IntentTarget.STATUS,
            chapter_scope=chapter_scope,
            original_input=user_input,
            source="rule"
        )
    
    # 5. 检查导出/输出（不需要“生成”动词即可触发）
    export_keywords = ["导出", "输出", "export"]
    if any(kw in input_lower for kw in export_keywords):
        return ParsedIntent(
            target=IntentTarget.EXPORT,
            chapter_scope=chapter_scope,
            original_input=user_input,
            source="rule"
        )
    
    # 6. 检查生成动词 + 目标产物
    generate_verbs = ["生成", "创建", "写", "创作", "做"]
    if any(verb in input_lower for verb in generate_verbs):
        target = _extract_target_from_keywords(user_input)
        if target:
            # 检查是否存在歧义（章节相关但未指定模式）
            is_ambiguous = False
            ambiguity_reason = None
            clarification_questions = []
            
            if chapter_scope and mode == IntentMode.UNSPECIFIED:
                # 有章节范围但没有明确说是计划还是正文
                if target in [IntentTarget.CHAPTER_PLAN, IntentTarget.CHAPTER_TEXT, IntentTarget.UNKNOWN]:
                    is_ambiguous = True
                    ambiguity_reason = "无法确定是生成章节计划还是章节正文"
                    clarification_questions.append(ClarificationQuestion(
                        question=f"你想生成{chapter_scope}的什么内容？",
                        options=["章节计划（详细场景规划）", "章节正文（完整文本内容）"]
                    ))
                    # 默认设为 CHAPTER_PLAN，但标记为歧义
                    target = IntentTarget.CHAPTER_PLAN
            
            return ParsedIntent(
                target=target,
                mode=mode,
                chapter_scope=chapter_scope,
                is_ambiguous=is_ambiguous,
                ambiguity_reason=ambiguity_reason,
                clarification_questions=clarification_questions,
                original_input=user_input,
                source="rule"
            )
        else:
            # 有生成动词但无明确目标产物关键词
            # 检查是否有章节范围（如"生成第3章"）
            if chapter_scope and mode == IntentMode.UNSPECIFIED:
                # "生成第N章" 是歧义场景：可能是章节计划或章节正文
                return ParsedIntent(
                    target=IntentTarget.CHAPTER_PLAN,  # 默认为章节计划
                    mode=mode,
                    chapter_scope=chapter_scope,
                    is_ambiguous=True,
                    ambiguity_reason="「生成第N章」可能指章节计划或章节正文",
                    clarification_questions=[ClarificationQuestion(
                        question=f"你想生成{chapter_scope}的什么内容？",
                        options=["章节计划（详细场景规划）", "章节正文（完整文本内容）"]
                    )],
                    original_input=user_input,
                    source="rule"
                )
            
            # 无章节范围的"生成"视为全流程
            return ParsedIntent(
                target=IntentTarget.FULL_WORKFLOW,
                mode=mode,
                chapter_scope=chapter_scope,
                original_input=user_input,
                source="rule"
            )
    
    # 7. 检查图谱查询
    query_keywords = ["谁是", "关系", "什么人", "介绍", "告诉我", "查询"]
    if any(kw in input_lower for kw in query_keywords):
        return ParsedIntent(
            target=IntentTarget.QUERY,
            original_input=user_input,
            source="rule"
        )
    
    # 8. 检查帮助
    help_keywords = ["帮助", "help", "怎么", "如何", "命令"]
    if any(kw in input_lower for kw in help_keywords):
        return ParsedIntent(
            target=IntentTarget.HELP,
            original_input=user_input,
            source="rule"
        )
    
    # 9. 检查是否有章节范围但无其他关键词（歧义场景）
    if chapter_scope:
        # 例如 "继续生成到第5章"
        return ParsedIntent(
            target=IntentTarget.FULL_WORKFLOW,
            chapter_scope=chapter_scope,
            is_ambiguous=True,
            ambiguity_reason="检测到章节范围但未明确生成目标",
            clarification_questions=[ClarificationQuestion(
                question=f"你想对{chapter_scope}做什么操作？",
                options=["生成章节计划", "生成章节正文", "执行完整流程到该章节"]
            )],
            original_input=user_input,
            source="rule"
        )
    
    # 10. 默认为未知
    return ParsedIntent(
        target=IntentTarget.UNKNOWN,
        original_input=user_input,
        confidence=0.3,
        source="rule"
    )


def _extract_target_from_keywords(user_input: str) -> Optional[IntentTarget]:
    """从用户输入中提取目标类型
    
    按关键词长度降序匹配，优先匹配更精确的关键词
    """
    # 收集所有关键词并按长度降序排序
    all_keywords: List[Tuple[str, IntentTarget]] = []
    for target, keywords in TARGET_KEYWORDS.items():
        for kw in keywords:
            all_keywords.append((kw, target))
    
    all_keywords.sort(key=lambda x: len(x[0]), reverse=True)
    
    for keyword, target in all_keywords:
        if keyword in user_input:
            return target
    
    return None


# ==================== LLM 意图识别 ====================

# LLM 意图识别提示词（支持对话历史）
INTENT_RECOGNITION_PROMPT = """你是一个小说生成系统的意图识别助手。你的任务是理解用户的自然语言请求，并将其转换为结构化的意图对象。

## 可识别的目标类型

- **world**: 世界观/世界设定/背景设定
- **theme_conflict**: 主题/主题冲突/核心冲突
- **characters**: 人物/角色/角色设定
- **outline**: 大纲/故事大纲/剧情大纲
- **chapter_plan**: 章节计划/场景计划/详细规划
- **chapter_text**: 章节正文/章节内容/正文
- **export**: 导出/输出/导出文本
- **full_workflow**: 完整生成/开始生成/继续生成/一键生成
- **status**: 状态查询/进度查询
- **help**: 帮助/命令说明
- **query**: 角色查询/关系查询
- **unknown**: 无法识别

## 模式（mode）

- **plan**: 生成计划/规划（如章节计划）
- **text**: 生成正文/内容（如章节正文）
- **unspecified**: 未明确指定

## 章节范围识别

识别用户输入中的章节范围，例如：
- "前3章" → chapter_start=1, chapter_end=3
- "第5章" → chapter_start=5, chapter_end=5
- "第2-5章" / "第2到5章" → chapter_start=2, chapter_end=5
- "前三章" → chapter_start=1, chapter_end=3（中文数字）
- "第十章" → chapter_start=10, chapter_end=10（中文数字）

## 歧义检测

以下情况必须标记为歧义（is_ambiguous=true）：

1. **章节相关但未指定模式**：
   - "生成第3章" → 可能是章节计划或章节正文
   - 建议问题："你想生成第3章的章节计划还是章节正文？"

2. **模糊的范围描述**：
   - "把后面几章规划一下" → 不知道具体是哪几章
   - 建议问题："请具体说明是哪几章？例如「第5-8章」"

3. **不完整的请求**：
   - "把中间几章补上" → 不知道起止章节
   - 建议问题："请说明需要补充的章节范围"

## 状态/进度查询默认规则（避免过度追问）

当用户询问"当前进度/完成进度/生成进度/状态如何/完成到哪一步"等状态类问题时：
- 默认 target=status
- 除非用户明确指定某一部分或某一章（如"第3章正文进度""大纲进度"），否则 is_ambiguous 必须为 false
- 不要为了"要看哪一部分"而反复追问；直接给出整体进度摘要即可

## 置信度（confidence）

- 1.0: 完全确定
- 0.8: 基本确定
- 0.5: 存在疑问但可推测
- 0.3: 高度不确定

## 对话历史使用规则（关键）

以下是对话历史和会话摘要（如有）。你可以使用历史来：
1. **指代消解**：理解"这个"、"那个"、"它"、"刚才"等指代词
2. **缺参补齐**：当用户未指定范围时，可从历史中推断（如"再生成正文"可能沿用上一轮的章节范围）
3. **范围沿用**：当用户说"继续"、"接着"、"再来一遍"时，沿用上一轮的范围

**关键约束**：
- **当轮输入优先**：当轮明确指定的目标/范围/模式不可被历史覆盖
- **不确定时必须澄清**：如果无法确定范围或目标，设置 is_ambiguous=true 并提出问题
- **禁止静默扩张范围**：不可将历史中的大范围（如"全部章节"）默认应用到当轮

{chat_history_section}

## 用户输入

{user_input}

请分析上述用户输入并输出结构化意图。"""

# 无历史版本的提示词（向后兼容）
INTENT_RECOGNITION_PROMPT_NO_HISTORY = """你是一个小说生成系统的意图识别助手。你的任务是理解用户的自然语言请求，并将其转换为结构化的意图对象。

## 可识别的目标类型

- **world**: 世界观/世界设定/背景设定
- **theme_conflict**: 主题/主题冲突/核心冲突
- **characters**: 人物/角色/角色设定
- **outline**: 大纲/故事大纲/剧情大纲
- **chapter_plan**: 章节计划/场景计划/详细规划
- **chapter_text**: 章节正文/章节内容/正文
- **export**: 导出/输出/导出文本
- **full_workflow**: 完整生成/开始生成/继续生成/一键生成
- **status**: 状态查询/进度查询
- **help**: 帮助/命令说明
- **query**: 角色查询/关系查询
- **unknown**: 无法识别

## 模式（mode）

- **plan**: 生成计划/规划（如章节计划）
- **text**: 生成正文/内容（如章节正文）
- **unspecified**: 未明确指定

## 章节范围识别

识别用户输入中的章节范围，例如：
- "前3章" → chapter_start=1, chapter_end=3
- "第5章" → chapter_start=5, chapter_end=5
- "第2-5章" / "第2到5章" → chapter_start=2, chapter_end=5
- "前三章" → chapter_start=1, chapter_end=3（中文数字）
- "第十章" → chapter_start=10, chapter_end=10（中文数字）

## 歧义检测

以下情况必须标记为歧义（is_ambiguous=true）：

1. **章节相关但未指定模式**：
   - "生成第3章" → 可能是章节计划或章节正文
   - 建议问题："你想生成第3章的章节计划还是章节正文？"

2. **模糊的范围描述**：
   - "把后面几章规划一下" → 不知道具体是哪几章
   - 建议问题："请具体说明是哪几章？例如「第5-8章」"

3. **不完整的请求**：
   - "把中间几章补上" → 不知道起止章节
   - 建议问题："请说明需要补充的章节范围"

## 状态/进度查询默认规则（避免过度追问）

当用户询问"当前进度/完成进度/生成进度/状态如何/完成到哪一步"等状态类问题时：
- 默认 target=status
- 除非用户明确指定某一部分或某一章（如"第3章正文进度""大纲进度"），否则 is_ambiguous 必须为 false
- 不要为了"要看哪一部分"而反复追问；直接给出整体进度摘要即可

## 置信度（confidence）

- 1.0: 完全确定
- 0.8: 基本确定
- 0.5: 存在疑问但可推测
- 0.3: 高度不确定

## 用户输入

{user_input}

请分析上述用户输入并输出结构化意图。"""


def create_llm_intent_chain(with_history: bool = False):
    """创建 LLM 意图识别链
    
    Args:
        with_history: 是否使用包含历史的提示词模板
    
    Returns:
        配置了 structured output 的 LLM 链
    """
    from novelgen.llm import get_structured_llm
    from novelgen.config import LLMConfig
    from langchain_core.prompts import ChatPromptTemplate
    
    # 使用轻量级模型配置（意图识别不需要强大模型）
    config = LLMConfig()
    # 可以在这里覆盖模型配置，例如使用更快的模型
    
    llm = get_structured_llm(LLMIntentOutput, config=config)
    
    # 选择提示词模板
    template = INTENT_RECOGNITION_PROMPT if with_history else INTENT_RECOGNITION_PROMPT_NO_HISTORY
    prompt = ChatPromptTemplate.from_template(template)
    
    chain = prompt | llm
    
    return chain


def format_chat_history_for_prompt(
    chat_history: Optional[List[Dict[str, str]]] = None,
    summary: Optional[str] = None
) -> str:
    """将对话历史格式化为提示词片段
    
    Args:
        chat_history: 对话历史列表 [{"role": "user/assistant", "content": "..."}]
        summary: 可选的会话摘要
        
    Returns:
        格式化后的历史片段
    """
    if not chat_history and not summary:
        return ""
    
    parts = []
    
    if summary:
        parts.append(f"## 会话摘要\n{summary}")
    
    if chat_history:
        parts.append("## 对话历史（最近几轮）")
        for msg in chat_history[-6:]:  # 限制最多 6 条消息
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")[:200]  # 截断长消息
            if len(msg.get("content", "")) > 200:
                content += "..."
            parts.append(f"- {role}: {content}")
    
    return "\n".join(parts)


def parse_intent_by_llm(
    user_input: str, 
    llm_chain=None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    summary: Optional[str] = None
) -> Optional[ParsedIntent]:
    """使用 LLM 解析用户意图
    
    Args:
        user_input: 用户输入
        llm_chain: 可选的预创建 LLM 链（用于复用）
        chat_history: 对话历史（用于指代消解和范围沿用）
        summary: 可选的会话摘要
        
    Returns:
        ParsedIntent 对象，LLM 调用失败时返回 None
    """
    try:
        has_history = bool(chat_history) or bool(summary)
        
        if llm_chain is None:
            llm_chain = create_llm_intent_chain(with_history=has_history)
        
        # 构建调用参数
        invoke_params = {"user_input": user_input}
        
        if has_history:
            # 格式化历史片段
            history_section = format_chat_history_for_prompt(chat_history, summary)
            invoke_params["chat_history_section"] = history_section
        
        result: LLMIntentOutput = llm_chain.invoke(invoke_params)
        
        # 转换 LLM 输出为 ParsedIntent
        target = _map_llm_target(result.target)
        mode = _map_llm_mode(result.mode)
        
        # 构建章节范围
        chapter_scope = None
        if result.chapter_start is not None and result.chapter_end is not None:
            chapter_scope = ChapterScope(start=result.chapter_start, end=result.chapter_end)
        elif result.chapter_start is not None:
            chapter_scope = ChapterScope(start=result.chapter_start, end=result.chapter_start)
        
        # 构建澄清问题
        clarification_questions = []
        if result.is_ambiguous and result.suggested_question:
            clarification_questions.append(ClarificationQuestion(
                question=result.suggested_question,
                options=[]
            ))
        
        return ParsedIntent(
            target=target,
            mode=mode,
            chapter_scope=chapter_scope,
            confidence=result.confidence,
            is_ambiguous=result.is_ambiguous,
            ambiguity_reason=result.ambiguity_reason,
            clarification_questions=clarification_questions,
            original_input=user_input,
            source="llm"
        )
    except Exception as e:
        # LLM 调用失败，返回 None 触发规则兜底
        print(f"⚠️ LLM 意图识别失败: {e}")
        return None


def _map_llm_target(target_str: str) -> IntentTarget:
    """将 LLM 输出的目标字符串映射为 IntentTarget 枚举"""
    mapping = {
        "world": IntentTarget.WORLD,
        "theme_conflict": IntentTarget.THEME_CONFLICT,
        "characters": IntentTarget.CHARACTERS,
        "outline": IntentTarget.OUTLINE,
        "chapter_plan": IntentTarget.CHAPTER_PLAN,
        "chapter_text": IntentTarget.CHAPTER_TEXT,
        "export": IntentTarget.EXPORT,
        "full_workflow": IntentTarget.FULL_WORKFLOW,
        "status": IntentTarget.STATUS,
        "help": IntentTarget.HELP,
        "query": IntentTarget.QUERY,
        "unknown": IntentTarget.UNKNOWN,
    }
    return mapping.get(target_str.lower(), IntentTarget.UNKNOWN)


def _map_llm_mode(mode_str: str) -> IntentMode:
    """将 LLM 输出的模式字符串映射为 IntentMode 枚举"""
    mapping = {
        "plan": IntentMode.PLAN,
        "text": IntentMode.TEXT,
        "unspecified": IntentMode.UNSPECIFIED,
    }
    return mapping.get(mode_str.lower(), IntentMode.UNSPECIFIED)


# ==================== 混合解析器 ====================

def parse_intent(
    user_input: str, 
    use_llm: bool = True,
    llm_chain=None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    summary: Optional[str] = None
) -> ParsedIntent:
    """解析用户意图（混合模式）
    
    1. 如果启用 LLM，先尝试 LLM 解析
    2. LLM 失败或禁用时，使用规则解析
    3. 融合两者结果（如果都有的话）
    
    Args:
        user_input: 用户输入
        use_llm: 是否启用 LLM 意图识别
        llm_chain: 可选的预创建 LLM 链
        chat_history: 对话历史（用于指代消解和范围沿用）
        summary: 可选的会话摘要
        
    Returns:
        ParsedIntent 对象
    """
    # 规则解析（始终执行，作为基线）
    rule_intent = parse_intent_by_rules(user_input)
    
    # 状态/帮助等查询类意图优先走确定性规则，避免 LLM 过度澄清导致循环追问
    if rule_intent.target in [IntentTarget.STATUS, IntentTarget.HELP]:
        return rule_intent
    
    if not use_llm:
        return rule_intent
    
    # LLM 解析（传入历史）
    llm_intent = parse_intent_by_llm(
        user_input, 
        llm_chain,
        chat_history=chat_history,
        summary=summary
    )
    
    if llm_intent is None:
        # LLM 失败，返回规则解析结果
        return rule_intent
    
    # 融合结果
    return _merge_intents(llm_intent, rule_intent)


def _merge_intents(llm_intent: ParsedIntent, rule_intent: ParsedIntent) -> ParsedIntent:
    """融合 LLM 和规则解析结果
    
    策略：
    1. 章节范围优先信任规则解析（因为正则更精确）
    2. 目标和模式优先信任 LLM（因为语义理解更好）
    3. 歧义标记取两者的并集
    """
    # 使用规则解析的章节范围（更精确）
    chapter_scope = rule_intent.chapter_scope
    
    # 如果规则没解析到但 LLM 解析到了，使用 LLM 的
    if chapter_scope is None and llm_intent.chapter_scope is not None:
        chapter_scope = llm_intent.chapter_scope
    
    # 目标和模式使用 LLM 的（语义理解更好）
    target = llm_intent.target
    mode = llm_intent.mode
    
    # 如果 LLM 识别为 unknown，使用规则的
    if target == IntentTarget.UNKNOWN and rule_intent.target != IntentTarget.UNKNOWN:
        target = rule_intent.target
        mode = rule_intent.mode
    
    # 对于状态/帮助等查询类意图，优先信任规则结果（安全：避免误触发生成）
    if rule_intent.target in [IntentTarget.STATUS, IntentTarget.HELP]:
        target = rule_intent.target
        mode = rule_intent.mode

    # 对于导出意图，优先信任规则结果（关键词确定性强，避免 LLM 误判为“生成第N章”）
    if rule_intent.target == IntentTarget.EXPORT:
        target = rule_intent.target
        mode = rule_intent.mode
    
    # 歧义处理：取两者的并集
    is_ambiguous = llm_intent.is_ambiguous or rule_intent.is_ambiguous
    ambiguity_reason = llm_intent.ambiguity_reason or rule_intent.ambiguity_reason
    
    # 澄清问题合并
    clarification_questions = []
    seen_questions = set()
    for q in llm_intent.clarification_questions + rule_intent.clarification_questions:
        if q.question not in seen_questions:
            clarification_questions.append(q)
            seen_questions.add(q.question)
    
    # 置信度取较低者（保守策略）
    confidence = min(llm_intent.confidence, rule_intent.confidence)
    
    # 状态查询不应因为“想看哪一部分”而进入澄清循环：强制视为不歧义
    if target == IntentTarget.STATUS:
        is_ambiguous = False
        ambiguity_reason = None
        clarification_questions = []
    
    return ParsedIntent(
        target=target,
        mode=mode,
        chapter_scope=chapter_scope,
        confidence=confidence,
        is_ambiguous=is_ambiguous,
        ambiguity_reason=ambiguity_reason,
        clarification_questions=clarification_questions,
        original_input=llm_intent.original_input,
        source="hybrid"
    )
