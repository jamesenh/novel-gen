"""
对话式 Agent 模块
提供 ng chat 命令的核心 REPL 会话功能

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
更新: 2025-12-16 - 集成 LLM 意图识别与范围解析
更新: 2025-12-16 - 添加会话上下文管理、澄清闭环、follow-up 参数补全
更新: 2025-12-16 - 添加打字机效果输出
"""
import os
import sys
import json
import time
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field

# 导入意图解析器
from novelgen.agent.intent_parser import (
    ParsedIntent, IntentTarget, IntentMode, ChapterScope,
    parse_intent, parse_intent_by_rules, parse_chapter_scope,
    ClarificationQuestion
)

# 导入会话状态管理
from novelgen.agent.conversation_state import (
    ConversationState,
    ConversationConfig,
    PendingClarification,
    LastExecutedIntent,
)


class IntentType(str, Enum):
    """用户意图类型（保留兼容性）"""
    GENERATE_FULL = "generate_full"       # 全流程生成（开始/继续/一键）
    GENERATE_TARGET = "generate_target"   # 目标型生成（生成X）
    GENERATE_SCOPED = "generate_scoped"   # 带范围的生成（如生成前3章章节计划）
    QUERY_GRAPH = "query_graph"           # 图谱查询
    SET_PREFERENCE = "set_pref"           # 设置偏好
    ROLLBACK = "rollback"                 # 回滚
    EXPORT = "export"                     # 导出
    STATUS = "status"                     # 查看状态
    EXPLAIN = "explain"                   # 解释/问答
    HELP = "help"                         # 帮助
    CLARIFICATION = "clarification"       # 需要澄清
    UNKNOWN = "unknown"                   # 未知


# ==================== 目标型生成相关定义 ====================
# 开发者: Jamesenh
# 开发时间: 2025-12-16

# 目标产物关键词到工作流节点的映射
TARGET_KEYWORDS_TO_NODE = {
    # 世界观相关
    "世界观": "world_creation",
    "世界": "world_creation",
    "世界设定": "world_creation",
    "背景": "world_creation",
    "背景设定": "world_creation",
    
    # 主题冲突相关
    "主题": "theme_conflict_creation",
    "主题冲突": "theme_conflict_creation",
    "冲突": "theme_conflict_creation",
    "核心冲突": "theme_conflict_creation",
    
    # 角色相关
    "人物": "character_creation",
    "角色": "character_creation",
    "人物角色": "character_creation",
    "角色设定": "character_creation",
    "人物设定": "character_creation",
    "主角": "character_creation",
    "配角": "character_creation",
    
    # 大纲相关
    "大纲": "outline_creation",
    "故事大纲": "outline_creation",
    "剧情大纲": "outline_creation",
    "章节大纲": "outline_creation",
    
    # 章节计划相关
    "章节计划": "chapter_planning",
    "场景计划": "chapter_planning",
    "详细计划": "chapter_planning",
}

# 工作流节点的执行顺序和依赖关系
# 键为节点名，值为该节点的所有前置节点（按顺序）
NODE_DEPENDENCIES = {
    "world_creation": [],
    "theme_conflict_creation": ["world_creation"],
    "character_creation": ["world_creation", "theme_conflict_creation"],
    "outline_creation": ["world_creation", "theme_conflict_creation", "character_creation"],
    "chapter_planning": ["world_creation", "theme_conflict_creation", "character_creation", "outline_creation"],
}

# 节点名称到中文显示名的映射
NODE_DISPLAY_NAMES = {
    "world_creation": "世界观",
    "theme_conflict_creation": "主题冲突",
    "character_creation": "人物角色",
    "outline_creation": "大纲",
    "chapter_planning": "章节计划",
}

# 全流程生成的触发关键词
FULL_WORKFLOW_KEYWORDS = [
    "开始生成", "继续生成", "一键生成", "跑完整流程", 
    "完整生成", "全部生成", "从头生成", "run", "resume",
    "继续", "开始",  # 单独出现时默认为全流程
]


class MissingInfo(BaseModel):
    """缺失信息"""
    field: str = Field(description="缺失字段名")
    description: str = Field(description="字段描述")
    question: str = Field(description="向用户提问的问题")


class TargetedGenerationPlan(BaseModel):
    """目标型生成计划
    
    用于存储目标型生成的执行计划，包含目标节点和缺失依赖
    
    开发者: Jamesenh
    开发时间: 2025-12-16
    """
    target_node: str = Field(description="目标工作流节点名")
    missing_deps: List[str] = Field(default_factory=list, description="缺失的前置依赖节点")
    requires_confirmation: bool = Field(default=True, description="是否需要确认（始终为 True）")


class ScopedGenerationPlan(BaseModel):
    """带范围的生成计划
    
    用于存储带章节范围的生成计划，支持约束感知降级
    
    开发者: Jamesenh
    开发时间: 2025-12-16
    """
    target_node: str = Field(description="目标工作流节点名")
    chapter_scope: Optional[ChapterScope] = Field(default=None, description="章节范围约束")
    parsed_intent: ParsedIntent = Field(description="完整的解析意图")
    can_execute_precisely: bool = Field(default=False, description="当前工具是否支持精确执行该范围")
    fallback_options: List[str] = Field(default_factory=list, description="降级选项")


class ChatAgent:
    """对话式 Agent
    
    提供多轮对话能力，支持自然语言驱动生成/查询/回滚等动作
    
    更新: 2025-12-16 - 集成 LLM 意图识别与范围解析
    更新: 2025-12-16 - 添加会话上下文管理、澄清闭环、follow-up 参数补全
    """
    
    def __init__(self, project_dir: str, project_id: str):
        """初始化 Agent
        
        Args:
            project_dir: 项目目录路径
            project_id: 项目ID
        """
        self.project_dir = project_dir
        self.project_id = project_id
        
        # 初始化工具注册表
        from novelgen.tools.registry import ToolRegistry
        self.registry = ToolRegistry(project_dir, project_id)
        
        # 注册所有工具
        self._register_all_tools()
        
        # 会话配置与状态
        self._conversation_config = ConversationConfig()
        self.conversation_state = self._conversation_config.create_conversation_state(
            project_dir, project_id
        )
        
        # 兼容性：保留旧的 conversation_history 属性（委托给 conversation_state）
        # 当前待确认的计划
        self.pending_plan = None
        
        # LLM 意图识别开关（可通过配置或命令控制）
        self.use_llm_intent: bool = True
        
        # LLM 意图识别链（惰性初始化）
        self._llm_intent_chain = None
    
    @property
    def conversation_history(self) -> List[Dict[str, str]]:
        """兼容性属性：返回对话历史列表"""
        return self.conversation_state.get_history_for_llm(include_summary=False)
    
    @property
    def pending_clarification(self) -> Optional[PendingClarification]:
        """获取待澄清状态"""
        return self.conversation_state.pending_clarification
    
    @pending_clarification.setter
    def pending_clarification(self, value):
        """设置待澄清状态（兼容旧代码）"""
        if value is None:
            self.conversation_state.clear_pending_clarification()
        elif isinstance(value, ParsedIntent):
            # 从 ParsedIntent 转换
            questions = [q.question for q in value.clarification_questions]
            options = [q.options for q in value.clarification_questions]
            self.conversation_state.set_pending_clarification(
                original_input=value.original_input,
                parsed_intent_dict=value.model_dump(),
                questions=questions,
                options=options
            )
        elif isinstance(value, PendingClarification):
            self.conversation_state.pending_clarification = value
    
    def _register_all_tools(self):
        """注册所有可用工具"""
        from novelgen.tools.workflow_tools import create_workflow_tools
        from novelgen.tools.preference_tools import create_preference_tools
        from novelgen.tools.graph_tools import create_graph_tools
        from novelgen.tools.memory_tools import create_memory_tools
        # 细粒度工具（Phase A）
        from novelgen.tools.project_tools import create_project_tools
        from novelgen.tools.settings_tools import create_settings_tools
        from novelgen.tools.outline_tools import create_outline_tools
        from novelgen.tools.chapter_tools import create_chapter_tools
        # 细粒度工具（Phase B/C/D - 可选）
        from novelgen.tools.export_tools import create_export_tools
        from novelgen.tools.consistency_tools import create_consistency_tools
        from novelgen.tools.scene_tools import create_scene_tools
        # 审查与修订工具
        from novelgen.tools.revision_tools import create_revision_tools
        
        # 注册各类工具
        for tool in create_workflow_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_preference_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_graph_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_memory_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        # 注册细粒度工具（Agent 专用）
        for tool in create_project_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_settings_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_outline_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_chapter_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        # Phase B/C/D 工具
        for tool in create_export_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_consistency_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        for tool in create_scene_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
        
        # 审查与修订工具
        for tool in create_revision_tools(self.project_dir, self.project_id):
            self.registry.register(tool)
    
    def get_project_summary(self) -> Dict[str, Any]:
        """获取项目进度摘要"""
        # 使用 workflow.status 工具
        plan = self.registry.create_plan("workflow.status")
        result = self.registry.execute_plan(plan)
        
        summary = {
            "project_id": self.project_id,
            "project_dir": self.project_dir
        }
        
        if result.success and result.data:
            summary.update(result.data)
        
        return summary
    
    def get_preferences_summary(self, limit: int = 5) -> List[str]:
        """获取偏好摘要"""
        plan = self.registry.create_plan("preference.list", {"limit": limit})
        result = self.registry.execute_plan(plan)
        
        if result.success and result.data:
            prefs = result.data.get("preferences", [])
            return [p.get("memory", p.get("content", str(p))) for p in prefs[:limit]]
        return []
    
    def handle_slash_command(self, command: str, args: str = "") -> str:
        """处理斜杠命令
        
        Args:
            command: 斜杠命令（如 '/run'）
            args: 命令参数
            
        Returns:
            响应消息
        """
        # 特殊命令处理
        if command == "/auto":
            return self._handle_auto_command(args)
        
        if command == "/help":
            return self._get_help_message()
        
        if command == "/quit" or command == "/exit":
            return "__EXIT__"
        
        if command == "/yes" or command == "/y":
            return self._confirm_pending_plan()
        
        if command == "/no" or command == "/n":
            return self._cancel_pending_plan()
        
        # 查找对应工具
        tool = self.registry.get_tool_by_slash(command)
        if tool is None:
            return f"未知命令: {command}\n使用 /help 查看可用命令"
        
        # 解析参数
        params = self._parse_args(args, tool.name)
        
        # 创建执行计划
        plan = self.registry.create_plan(tool.name, params)
        
        # 检查是否需要确认
        if plan.requires_confirmation:
            self.pending_plan = plan
            return f"⚠️ {plan.confirmation_message}\n输入 /yes 确认，/no 取消"
        
        # 直接执行
        return self._execute_and_format(plan)
    
    def handle_natural_language(self, user_input: str) -> str:
        """处理自然语言输入
        
        Args:
            user_input: 用户输入
            
        Returns:
            响应消息
            
        更新: 2025-12-16 - 集成 LLM 意图识别与范围解析，支持澄清与约束感知降级
        更新: 2025-12-16 - 添加会话上下文管理、澄清闭环、follow-up 参数补全
        """
        # 重置轮次计数器
        self.registry.reset_turn_counters()
        
        # 记录用户消息
        self.conversation_state.add_user_message(user_input)
        
        # 检查是否处于等待澄清状态
        if self.conversation_state.is_awaiting_clarification():
            response = self._handle_clarification_response(user_input)
            # 记录助手回复
            self.conversation_state.add_assistant_message(response)
            return response
        
        # 获取对话历史用于 LLM
        chat_history = self.conversation_state.get_history_for_llm(include_summary=True)
        
        # 使用新的意图解析器（传入历史）
        parsed = parse_intent(
            user_input, 
            use_llm=self.use_llm_intent,
            llm_chain=self._llm_intent_chain,
            chat_history=chat_history[:-1] if chat_history else None,  # 排除刚添加的当轮
            summary=self.conversation_state.summary
        )
        
        # 检查是否需要澄清
        if parsed.needs_clarification():
            response = self._handle_clarification_needed(parsed)
            self.conversation_state.add_assistant_message(response)
            return response
        
        # 尝试 follow-up 参数补全
        parsed = self._try_followup_completion(parsed)
        
        # 生成执行前回显
        echo_msg = self._generate_echo_message(parsed)
        
        # 将 ParsedIntent 转换为 IntentType 并处理
        intent_type = self._parsed_intent_to_type(parsed)
        
        if intent_type == IntentType.GENERATE_FULL:
            response = self._handle_generate_full_intent(user_input)
        elif intent_type == IntentType.GENERATE_TARGET:
            response = self._handle_generate_target_intent_v2(parsed)
        elif intent_type == IntentType.GENERATE_SCOPED:
            response = self._handle_scoped_generation_intent(parsed)
        elif intent_type == IntentType.QUERY_GRAPH:
            response = self._handle_query_intent(user_input)
        elif intent_type == IntentType.STATUS:
            response = self._handle_status_intent()
        elif intent_type == IntentType.EXPORT:
            response = self._handle_export_intent(parsed)
        elif intent_type == IntentType.HELP:
            response = self._get_help_message()
        elif intent_type == IntentType.EXPLAIN:
            response = self._handle_explain_intent(user_input)
        else:
            response = self._handle_unknown_intent(user_input)
        
        # 如果有回显消息且不是帮助/状态等查询类意图，添加到响应前
        if echo_msg and intent_type not in [IntentType.STATUS, IntentType.HELP, IntentType.EXPLAIN, IntentType.UNKNOWN]:
            full_response = f"{echo_msg}\n\n{response}"
        else:
            full_response = response
        
        # 记录助手回复
        self.conversation_state.add_assistant_message(full_response)
        
        return full_response
    
    def _try_followup_completion(self, parsed: ParsedIntent) -> ParsedIntent:
        """尝试 follow-up 参数补全
        
        当目标/范围缺失时，尝试从最近一次执行的意图中提取候选
        
        Args:
            parsed: 当前解析的意图
            
        Returns:
            补全后的意图（如果适用）或原意图
        """
        last = self.conversation_state.last_executed_intent
        if last is None:
            return parsed
        
        # 检查是否是 follow-up 场景：
        # 1. 有章节相关目标但缺少范围
        # 2. 有"再"、"继续"等关键词
        input_lower = parsed.original_input.lower()
        followup_keywords = ["再", "继续", "接着", "同样", "一样"]
        is_followup = any(kw in input_lower for kw in followup_keywords)
        
        if not is_followup:
            return parsed
        
        # 尝试补全范围
        if parsed.chapter_scope is None and last.chapter_start is not None:
            # 从上一轮沿用范围
            new_scope = ChapterScope(
                start=last.chapter_start,
                end=last.chapter_end or last.chapter_start
            )
            
            # 创建新的 ParsedIntent 带补全的范围
            return ParsedIntent(
                target=parsed.target,
                mode=parsed.mode if parsed.mode != IntentMode.UNSPECIFIED else (
                    IntentMode.PLAN if last.mode == "plan" else 
                    IntentMode.TEXT if last.mode == "text" else 
                    IntentMode.UNSPECIFIED
                ),
                chapter_scope=new_scope,
                confidence=parsed.confidence * 0.9,  # 略微降低置信度
                is_ambiguous=False,
                ambiguity_reason=None,
                clarification_questions=[],
                original_input=parsed.original_input,
                source="hybrid"
            )
        
        return parsed
    
    def _handle_clarification_response(self, user_input: str) -> str:
        """处理澄清回答
        
        当系统处于等待澄清状态时，解析用户的回答并合并回原意图
        
        Args:
            user_input: 用户的澄清回答
            
        Returns:
            响应消息
        """
        pending = self.conversation_state.pending_clarification
        if pending is None:
            # 不应该发生，但做兜底
            return self._handle_unknown_intent(user_input)
        
        # 尝试解析回答
        resolved_intent = self._resolve_clarification(user_input, pending)
        
        if resolved_intent is None:
            # 无法解析回答
            pending.increment_count()
            
            if pending.is_exhausted():
                # 超过澄清次数上限
                self.conversation_state.clear_pending_clarification()
                return (
                    "❌ 多次澄清后仍无法理解你的需求。\n\n"
                    "**建议**：请使用更明确的表达或斜杠命令，例如：\n"
                    "- `/run` 执行完整流程\n"
                    "- 「生成第1-3章的章节计划」\n"
                    "- 「生成第1章的正文」"
                )
            
            # 重复提问
            questions_text = "\n".join([
                f"**问题 {i}**: {q}" + (f"\n  选项: {', '.join(pending.options[i-1])}" if i-1 < len(pending.options) and pending.options[i-1] else "")
                for i, q in enumerate(pending.questions, 1)
            ])
            return (
                f"❓ 抱歉，我没有理解你的回答。\n\n"
                f"原问题：\n{questions_text}\n\n"
                f"请回复具体选项编号（如「1」「2」）或关键词。"
            )
        
        # 成功解析，清除待澄清状态
        self.conversation_state.clear_pending_clarification()
        
        # 生成回显
        echo_msg = self._generate_echo_message(resolved_intent)
        
        # 检查是否仍需澄清（理论上不应该，但做防御）
        if resolved_intent.needs_clarification():
            return self._handle_clarification_needed(resolved_intent)
        
        # 转换意图类型并处理
        intent_type = self._parsed_intent_to_type(resolved_intent)
        
        if intent_type == IntentType.GENERATE_SCOPED:
            response = self._handle_scoped_generation_intent(resolved_intent)
        elif intent_type == IntentType.GENERATE_TARGET:
            response = self._handle_generate_target_intent_v2(resolved_intent)
        elif intent_type == IntentType.GENERATE_FULL:
            response = self._handle_generate_full_intent(resolved_intent.original_input)
        else:
            response = self._handle_unknown_intent(user_input)
        
        if echo_msg:
            return f"{echo_msg}\n\n{response}"
        return response
    
    def _resolve_clarification(self, user_input: str, pending: PendingClarification) -> Optional[ParsedIntent]:
        """解析澄清回答并合并回原意图
        
        Args:
            user_input: 用户的澄清回答
            pending: 待澄清状态
            
        Returns:
            合并后的 ParsedIntent 或 None（无法解析）
        """
        input_lower = user_input.strip().lower()
        
        # 尝试解析数字选项（如 "1"、"2"）
        try:
            choice_num = int(input_lower)
            if pending.options and len(pending.options) > 0:
                # 假设第一个问题的选项
                first_options = pending.options[0]
                if 1 <= choice_num <= len(first_options):
                    selected_option = first_options[choice_num - 1]
                    return self._apply_clarification_choice(pending, selected_option)
        except ValueError:
            pass
        
        # 尝试匹配关键词
        # 章节计划 vs 章节正文
        plan_keywords = ["1", "计划", "章节计划", "场景计划", "规划", "plan"]
        text_keywords = ["2", "正文", "章节正文", "内容", "text"]
        
        if any(kw in input_lower for kw in plan_keywords):
            return self._apply_clarification_choice(pending, "chapter_plan")
        
        if any(kw in input_lower for kw in text_keywords):
            return self._apply_clarification_choice(pending, "chapter_text")
        
        # 全流程
        full_keywords = ["3", "完整", "全部", "流程", "full"]
        if any(kw in input_lower for kw in full_keywords):
            return self._apply_clarification_choice(pending, "full_workflow")
        
        return None
    
    def _apply_clarification_choice(self, pending: PendingClarification, choice: str) -> ParsedIntent:
        """应用澄清选择到原意图
        
        Args:
            pending: 待澄清状态
            choice: 选择的选项
            
        Returns:
            合并后的 ParsedIntent
        """
        # 从 pending 恢复原意图
        original_dict = pending.parsed_intent_dict
        
        # 确定新的目标和模式
        if choice == "chapter_plan":
            target = IntentTarget.CHAPTER_PLAN
            mode = IntentMode.PLAN
        elif choice == "chapter_text":
            target = IntentTarget.CHAPTER_TEXT
            mode = IntentMode.TEXT
        elif choice == "full_workflow":
            target = IntentTarget.FULL_WORKFLOW
            mode = IntentMode.UNSPECIFIED
        else:
            # 尝试从选项文本推断
            if "计划" in choice or "规划" in choice:
                target = IntentTarget.CHAPTER_PLAN
                mode = IntentMode.PLAN
            elif "正文" in choice or "内容" in choice:
                target = IntentTarget.CHAPTER_TEXT
                mode = IntentMode.TEXT
            else:
                target = IntentTarget(original_dict.get("target", "unknown"))
                mode = IntentMode(original_dict.get("mode", "unspecified"))
        
        # 恢复章节范围
        chapter_scope = None
        scope_dict = original_dict.get("chapter_scope")
        if scope_dict:
            chapter_scope = ChapterScope(
                start=scope_dict.get("start", 1),
                end=scope_dict.get("end", 1)
            )
        
        return ParsedIntent(
            target=target,
            mode=mode,
            chapter_scope=chapter_scope,
            confidence=0.9,
            is_ambiguous=False,
            ambiguity_reason=None,
            clarification_questions=[],
            original_input=pending.original_input,
            source="rule"  # 澄清回答的解析基于规则
        )
    
    def _generate_echo_message(self, parsed: ParsedIntent) -> str:
        """生成解析结果回显消息
        
        在执行前向用户展示系统理解的意图，提高透明度
        """
        if parsed.target in [IntentTarget.STATUS, IntentTarget.HELP, IntentTarget.QUERY, IntentTarget.UNKNOWN]:
            return ""
        
        echo = f"📖 **理解你的请求**：{parsed.get_echo_message()}"
        return echo
    
    def _parsed_intent_to_type(self, parsed: ParsedIntent) -> IntentType:
        """将 ParsedIntent 转换为 IntentType
        
        用于兼容现有的意图处理逻辑
        """
        if parsed.target == IntentTarget.FULL_WORKFLOW:
            return IntentType.GENERATE_FULL
        elif parsed.target in [IntentTarget.WORLD, IntentTarget.THEME_CONFLICT, 
                               IntentTarget.CHARACTERS, IntentTarget.OUTLINE]:
            return IntentType.GENERATE_TARGET
        elif parsed.target in [IntentTarget.CHAPTER_PLAN, IntentTarget.CHAPTER_TEXT]:
            # 如果有章节范围，使用带范围的生成处理
            if parsed.chapter_scope:
                return IntentType.GENERATE_SCOPED
            return IntentType.GENERATE_TARGET
        elif parsed.target == IntentTarget.EXPORT:
            return IntentType.EXPORT
        elif parsed.target == IntentTarget.STATUS:
            return IntentType.STATUS
        elif parsed.target == IntentTarget.HELP:
            return IntentType.HELP
        elif parsed.target == IntentTarget.QUERY:
            return IntentType.QUERY_GRAPH
        elif parsed.target == IntentTarget.UNKNOWN:
            return IntentType.EXPLAIN
        else:
            return IntentType.UNKNOWN
    
    def _handle_clarification_needed(self, parsed: ParsedIntent) -> str:
        """处理需要澄清的意图
        
        保存待澄清意图，向用户展示澄清问题
        """
        self.pending_clarification = parsed
        
        response = "❓ **需要更多信息**\n\n"
        
        if parsed.ambiguity_reason:
            response += f"原因：{parsed.ambiguity_reason}\n\n"
        
        for i, q in enumerate(parsed.clarification_questions, 1):
            response += f"**问题 {i}**: {q.question}\n"
            if q.options:
                for j, opt in enumerate(q.options, 1):
                    response += f"  {j}. {opt}\n"
            response += "\n"
        
        response += "请回复具体选项或详细说明你的需求。"
        
        return response

    def _handle_export_intent(self, parsed: ParsedIntent) -> str:
        """处理导出意图
        
        支持：
        - 无章节范围：导出整本（export.all）
        - 单章节：导出该章（export.chapter）
        - 范围章节：导出范围内每章（export.range）
        
        开发者: Jamesenh
        开发时间: 2025-12-16
        """
        scope = parsed.chapter_scope
        if scope is None:
            plan = self.registry.create_plan("export.all", {})
            return self._execute_and_format(plan)
        
        if scope.is_single:
            plan = self.registry.create_plan("export.chapter", {"chapter_number": scope.start})
            return self._execute_and_format(plan)
        
        plan = self.registry.create_plan(
            "export.range",
            {"chapter_start": scope.start, "chapter_end": scope.end}
        )
        return self._execute_and_format(plan)
    
    def _handle_scoped_generation_intent(self, parsed: ParsedIntent) -> str:
        """处理带范围的生成意图
        
        使用细粒度工具精确执行章节范围生成：
        1. 章节计划：调用 chapter.plan.generate
        2. 章节正文：调用 chapter.text.generate（默认顺序约束）
        
        开发者: Jamesenh
        开发时间: 2025-12-16
        更新: 2025-12-16 - 集成细粒度工具，支持精确范围执行
        """
        # 确定目标节点
        target_node = self._intent_target_to_node(parsed.target)
        if target_node is None:
            return self._handle_unknown_intent(parsed.original_input)
        
        target_display = NODE_DISPLAY_NAMES.get(target_node, target_node)
        scope = parsed.chapter_scope
        
        # 使用细粒度工具精确执行
        if target_node == "chapter_planning":
            # 章节计划：使用 chapter.plan.generate 精确执行
            self.pending_plan = ScopedGenerationPlan(
                target_node=target_node,
                chapter_scope=scope,
                parsed_intent=parsed,
                can_execute_precisely=True,
                fallback_options=[]
            )
            
            return (
                f"📋 **生成计划**\n\n"
                f"🎯 目标：**{target_display}**\n"
                f"📖 范围：**{scope}**\n\n"
                f"将调用 `chapter.plan.generate` 精确生成指定范围的章节计划。\n"
                f"- 已存在的计划将被跳过（missing_only=true）\n"
                f"- 如需强制覆盖，请使用 force=true\n\n"
                f"⏳ 输入 /yes 确认执行，/no 取消"
            )
        
        elif target_node == "chapter_text":
            # 章节正文：使用 chapter.text.generate（默认顺序约束）
            self.pending_plan = ScopedGenerationPlan(
                target_node=target_node,
                chapter_scope=scope,
                parsed_intent=parsed,
                can_execute_precisely=True,
                fallback_options=[]
            )
            
            return (
                f"📋 **生成计划**\n\n"
                f"🎯 目标：**{target_display}**\n"
                f"📖 范围：**{scope}**\n\n"
                f"将调用 `chapter.text.generate` 生成指定范围的章节正文。\n"
                f"- 默认顺序约束（sequential=true）：若前置章节缺失将被阻止\n"
                f"- 已存在的正文将被跳过（missing_only=true）\n\n"
                f"⏳ 输入 /yes 确认执行，/no 取消"
            )
        
        else:
            # 其他目标节点：使用原有工作流逻辑
            return self._handle_generate_target_intent_v2(parsed)
    
    def _classify_intent(self, user_input: str) -> IntentType:
        """意图分类（基于关键词，区分全流程生成与目标型生成）
        
        更新: 2025-12-16 - 支持目标型生成识别
        注意: 此方法保留用于向后兼容，新代码应使用 parse_intent
        """
        input_lower = user_input.lower()
        
        # 1. 首先检查是否是全流程生成意图
        # 包含明确的全流程触发词
        for kw in FULL_WORKFLOW_KEYWORDS:
            if kw in input_lower:
                # 但如果同时包含目标产物词，则为目标型生成
                target = self._extract_target_from_input(user_input)
                if target is None:
                    return IntentType.GENERATE_FULL
        
        # 2. 检查是否是目标型生成（"生成X"模式）
        # 包含"生成"动词但有明确目标产物
        generate_verbs = ["生成", "创建", "写", "创作", "做"]
        if any(verb in input_lower for verb in generate_verbs):
            target = self._extract_target_from_input(user_input)
            if target is not None:
                return IntentType.GENERATE_TARGET
            # 无明确目标的"生成"视为全流程
            return IntentType.GENERATE_FULL
        
        # 3. 状态查询
        status_keywords = ["状态", "进度", "完成", "status"]
        if any(kw in input_lower for kw in status_keywords):
            return IntentType.STATUS
        
        # 4. 图谱查询
        query_keywords = ["谁是", "关系", "什么人", "介绍", "告诉我", "查询"]
        if any(kw in input_lower for kw in query_keywords):
            return IntentType.QUERY_GRAPH
        
        # 5. 帮助
        help_keywords = ["帮助", "help", "怎么", "如何", "命令"]
        if any(kw in input_lower for kw in help_keywords):
            return IntentType.HELP
        
        # 6. 默认为解释/问答
        return IntentType.EXPLAIN
    
    def _intent_target_to_node(self, target: IntentTarget) -> Optional[str]:
        """将 IntentTarget 转换为工作流节点名
        
        Args:
            target: 意图目标类型
            
        Returns:
            工作流节点名或 None
        """
        mapping = {
            IntentTarget.WORLD: "world_creation",
            IntentTarget.THEME_CONFLICT: "theme_conflict_creation",
            IntentTarget.CHARACTERS: "character_creation",
            IntentTarget.OUTLINE: "outline_creation",
            IntentTarget.CHAPTER_PLAN: "chapter_planning",
            IntentTarget.CHAPTER_TEXT: "chapter_text",
        }
        return mapping.get(target)
    
    def _handle_generate_target_intent_v2(self, parsed: ParsedIntent) -> str:
        """处理目标型生成意图（基于 ParsedIntent）
        
        1. 从 ParsedIntent 提取目标节点
        2. 检查前置依赖是否满足
        3. 如果有缺失前置，显示补齐计划并请求确认
        4. 确认后执行 workflow.run(stop_at=<target_node>)
        
        开发者: Jamesenh
        开发时间: 2025-12-16
        """
        # 1. 转换目标为工作流节点
        target_node = self._intent_target_to_node(parsed.target)
        if target_node is None:
            # 无法识别目标，降级为全流程生成
            return self._handle_generate_full_intent(parsed.original_input)
        
        # 复用现有的目标型生成逻辑
        return self._handle_generate_target_with_node(target_node)
    
    def _extract_target_from_input(self, user_input: str) -> Optional[str]:
        """从用户输入中提取生成目标（返回工作流节点名）
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            工作流节点名（如 "character_creation"）或 None
        """
        # 按关键词长度降序排列，优先匹配更精确的关键词
        sorted_keywords = sorted(TARGET_KEYWORDS_TO_NODE.keys(), key=len, reverse=True)
        
        for keyword in sorted_keywords:
            if keyword in user_input:
                return TARGET_KEYWORDS_TO_NODE[keyword]
        
        return None
    
    def _handle_generate_full_intent(self, user_input: str) -> str:
        """处理全流程生成意图（开始/继续生成完整小说）
        
        更新: 2025-12-16 - 重命名自 _handle_generate_intent
        """
        # 先获取状态
        status_plan = self.registry.create_plan("workflow.status")
        status_result = self.registry.execute_plan(status_plan)
        
        if not status_result.success:
            return f"获取项目状态失败: {status_result.error}"
        
        status_data = status_result.data or {}
        can_resume = status_data.get("can_resume", False)
        completed_chapters = status_data.get("completed_chapters", 0)
        
        # 判断使用 run 还是 resume
        if can_resume and completed_chapters > 0:
            tool_name = "workflow.resume"
            action_desc = "继续生成"
        else:
            tool_name = "workflow.run"
            action_desc = "开始生成"
        
        # 创建计划
        plan = self.registry.create_plan(
            tool_name,
            {},
            f"确定要{action_desc}吗？（当前已完成 {completed_chapters} 章）"
        )
        
        if plan.requires_confirmation:
            self.pending_plan = plan
            return f"📝 准备{action_desc}完整小说\n当前已完成 {completed_chapters} 章\n\n输入 /yes 确认，/no 取消"
        
        return self._execute_and_format(plan)
    
    def _handle_generate_target_intent(self, user_input: str) -> str:
        """处理目标型生成意图（生成特定阶段产物）
        
        1. 识别目标节点（世界观/主题冲突/人物角色/大纲等）
        2. 检查前置依赖是否满足
        3. 如果有缺失前置，显示补齐计划并请求确认
        4. 确认后执行 workflow.run(stop_at=<target_node>)
        
        开发者: Jamesenh
        开发时间: 2025-12-16
        """
        # 1. 提取目标节点
        target_node = self._extract_target_from_input(user_input)
        if target_node is None:
            # 无法识别目标，降级为全流程生成
            return self._handle_generate_full_intent(user_input)
        
        return self._handle_generate_target_with_node(target_node)
    
    def _handle_generate_target_with_node(self, target_node: str) -> str:
        """处理目标型生成意图（基于节点名）
        
        内部方法，被 _handle_generate_target_intent 和 _handle_generate_target_intent_v2 调用
        """
        target_display = NODE_DISPLAY_NAMES.get(target_node, target_node)
        
        # 2. 获取项目状态，检查前置依赖
        status_plan = self.registry.create_plan("workflow.status")
        status_result = self.registry.execute_plan(status_plan)
        
        if not status_result.success:
            return f"获取项目状态失败: {status_result.error}"
        
        status_data = status_result.data or {}
        steps = status_data.get("completed_steps", [])
        
        # 3. 计算缺失的前置依赖
        required_deps = NODE_DEPENDENCIES.get(target_node, [])
        missing_deps = self._get_missing_dependencies(target_node, steps)
        
        # 4. 构建确认消息和执行计划
        if missing_deps:
            # 有缺失前置，需要用户确认补齐
            missing_display = [NODE_DISPLAY_NAMES.get(d, d) for d in missing_deps]
            
            # 设置特殊的 pending_plan，包含 stop_at 参数
            # 注意：这个确认不受 /auto on 影响
            self.pending_plan = TargetedGenerationPlan(
                target_node=target_node,
                missing_deps=missing_deps,
                requires_confirmation=True  # 始终需要确认
            )
            
            return (
                f"📋 **目标型生成计划**\n\n"
                f"🎯 目标产物：**{target_display}**\n\n"
                f"⚠️ 检测到缺失前置步骤：\n"
                f"  - {', '.join(missing_display)}\n\n"
                f"执行计划：\n"
                f"  1. 自动补齐缺失前置\n"
                f"  2. 生成{target_display}\n"
                f"  3. 在 `{target_node}` 停止（不继续后续步骤）\n\n"
                f"⏳ 输入 /yes 确认执行，/no 取消"
            )
        else:
            # 前置已满足，检查目标是否已存在
            if self._is_step_completed(target_node, steps):
                return (
                    f"✅ **{target_display}** 已存在\n\n"
                    f"如需重新生成，请先使用 `/rollback` 回滚到该步骤之前。"
                )
            
            # 前置满足但目标未生成，直接创建执行计划
            self.pending_plan = TargetedGenerationPlan(
                target_node=target_node,
                missing_deps=[],
                requires_confirmation=True  # 始终需要确认
            )
            
            return (
                f"📋 **目标型生成计划**\n\n"
                f"🎯 目标产物：**{target_display}**\n\n"
                f"✅ 所有前置步骤已完成\n\n"
                f"执行计划：\n"
                f"  1. 生成{target_display}\n"
                f"  2. 在 `{target_node}` 停止（不继续后续步骤）\n\n"
                f"⏳ 输入 /yes 确认执行，/no 取消"
            )
    
    def _get_missing_dependencies(self, target_node: str, completed_steps: List[str]) -> List[str]:
        """获取目标节点缺失的前置依赖
        
        Args:
            target_node: 目标工作流节点
            completed_steps: 已完成的步骤列表
            
        Returns:
            缺失的依赖节点列表（按执行顺序）
        """
        required_deps = NODE_DEPENDENCIES.get(target_node, [])
        missing = []
        
        for dep in required_deps:
            if not self._is_step_completed(dep, completed_steps):
                missing.append(dep)
        
        return missing
    
    def _is_step_completed(self, step_name: str, completed_steps: List[str]) -> bool:
        """检查步骤是否已完成
        
        Args:
            step_name: 步骤名称
            completed_steps: 已完成的步骤列表
            
        Returns:
            是否已完成
        """
        return step_name in completed_steps
    
    def _handle_query_intent(self, user_input: str) -> str:
        """处理查询意图"""
        # 尝试从输入中提取角色名
        # 简单实现：使用图谱工具查询
        
        # 先获取所有角色
        from novelgen.config import ProjectConfig
        from novelgen.graph.kuzu_store import KuzuStore
        
        try:
            config = ProjectConfig(project_dir=self.project_dir)
            if not config.graph_enabled:
                return "图谱功能未启用"
            
            store = KuzuStore(config.get_graph_dir(), read_only=True)
            if not store.is_available or not store.connect():
                return "图谱数据库不可用，请先运行: ng graph rebuild <project>"
            
            try:
                all_chars = store.get_all_characters()
                
                # 尝试匹配角色名
                matched_char = None
                for char in all_chars:
                    if char["name"] in user_input:
                        matched_char = char["name"]
                        break
                
                if matched_char:
                    # 查询角色详情
                    plan = self.registry.create_plan("graph.whois", {"name": matched_char})
                    result = self.registry.execute_plan(plan)
                    
                    if result.success and result.data:
                        char_data = result.data.get("character", {})
                        
                        response = f"👤 **{char_data.get('name')}**\n"
                        response += f"角色: {char_data.get('role', '-')}\n"
                        response += f"性别: {char_data.get('gender', '-')}\n"
                        
                        if char_data.get('personality'):
                            response += f"\n性格: {char_data['personality'][:100]}..."
                        
                        if char_data.get('background'):
                            response += f"\n\n背景: {char_data['background'][:150]}..."
                        
                        return response
                    else:
                        return f"查询失败: {result.error}"
                else:
                    # 没有匹配到角色，列出所有角色
                    if all_chars:
                        char_list = "\n".join([f"  - {c['name']} ({c['role']})" for c in all_chars])
                        return f"未能识别角色名。当前项目中的角色:\n{char_list}\n\n请指定具体角色名进行查询。"
                    else:
                        return "图谱中暂无角色数据，请先生成小说或运行 ng graph rebuild"
            finally:
                store.close()
                
        except Exception as e:
            return f"查询出错: {e}"
    
    def _handle_status_intent(self) -> str:
        """处理状态查询意图"""
        plan = self.registry.create_plan("workflow.status")
        result = self.registry.execute_plan(plan)
        
        if not result.success:
            return f"获取状态失败: {result.error}"
        
        data = result.data or {}
        
        response = f"📊 **项目状态: {self.project_id}**\n\n"
        
        completed_steps = data.get("completed_steps", [])
        if completed_steps:
            response += f"✅ 已完成步骤: {', '.join(completed_steps)}\n"
        
        total_chapters = data.get("total_chapters_planned", 0)
        completed_chapters = data.get("completed_chapters", 0)
        in_progress = data.get("in_progress_chapters", 0)
        total_words = data.get("total_words", 0)
        
        response += f"\n📖 章节进度: {completed_chapters}/{total_chapters} 章完成"
        if in_progress > 0:
            response += f" ({in_progress} 章进行中)"
        
        response += f"\n📝 总字数: {total_words:,} 字"
        
        if data.get("can_resume"):
            response += "\n\n💡 可以使用 /resume 继续生成"
        
        return response
    
    def _handle_explain_intent(self, user_input: str) -> str:
        """处理解释/问答意图"""
        # 尝试使用记忆搜索
        plan = self.registry.create_plan("memory.search_scenes", {"query": user_input, "limit": 3})
        result = self.registry.execute_plan(plan)
        
        if result.success and result.data:
            memories = result.data.get("memories", [])
            if memories:
                response = "🔍 找到以下相关信息:\n\n"
                for i, mem in enumerate(memories[:3], 1):
                    content = mem.get("memory", mem.get("content", str(mem)))
                    response += f"{i}. {content[:150]}...\n\n"
                return response
        
        return "抱歉，我没有找到相关信息。你可以尝试:\n" \
               "- /status 查看项目状态\n" \
               "- /whois <角色名> 查询角色信息\n" \
               "- /help 查看所有可用命令"
    
    def _handle_unknown_intent(self, user_input: str) -> str:
        """处理未知意图"""
        return "我不太理解你的意思。你可以:\n" \
               "- 说「继续生成」来继续创作\n" \
               "- 说「查看状态」了解进度\n" \
               "- 问「林风是谁」查询角色\n" \
               "- 输入 /help 查看所有命令"
    
    def _handle_auto_command(self, args: str) -> str:
        """处理 /auto 命令"""
        args_lower = args.strip().lower()
        
        if args_lower == "on":
            self.registry.set_auto_confirm(True)
            return "✅ 自动确认模式已开启（破坏性操作仍需确认）"
        elif args_lower == "off":
            self.registry.set_auto_confirm(False)
            return "✅ 自动确认模式已关闭"
        else:
            current = "开启" if self.registry.session.auto_confirm else "关闭"
            return f"当前自动确认模式: {current}\n使用 /auto on 或 /auto off 切换"
    
    def _confirm_pending_plan(self) -> str:
        """确认待执行的计划
        
        更新: 2025-12-16 - 支持 TargetedGenerationPlan 和 ScopedGenerationPlan 类型
        更新: 2025-12-16 - 记录最近执行的意图（用于 follow-up）
        """
        if self.pending_plan is None:
            return "当前没有待确认的操作"
        
        plan = self.pending_plan
        self.pending_plan = None
        
        # 检查是否是目标型生成计划
        if isinstance(plan, TargetedGenerationPlan):
            result = self._execute_targeted_generation(plan)
            # 记录最近执行的意图
            self._record_executed_intent(plan.target_node, None, None, None)
            return result
        
        # 检查是否是带范围的生成计划
        if isinstance(plan, ScopedGenerationPlan):
            result = self._execute_scoped_generation(plan)
            # 记录最近执行的意图
            scope = plan.chapter_scope
            mode = "plan" if plan.target_node == "chapter_planning" else "text"
            self._record_executed_intent(
                plan.target_node, 
                mode,
                scope.start if scope else None,
                scope.end if scope else None
            )
            return result
        
        # 普通工具计划
        return self._execute_and_format(plan)
    
    def _record_executed_intent(
        self, 
        target: str, 
        mode: Optional[str],
        chapter_start: Optional[int],
        chapter_end: Optional[int]
    ):
        """记录最近执行的意图（用于 follow-up 参数补全）
        
        Args:
            target: 目标类型
            mode: 模式（plan/text）
            chapter_start: 章节范围起始
            chapter_end: 章节范围结束
        """
        self.conversation_state.set_last_executed_intent(
            target=target,
            mode=mode,
            chapter_start=chapter_start,
            chapter_end=chapter_end,
            was_confirmed=True
        )
    
    def _execute_scoped_generation(self, plan: ScopedGenerationPlan) -> str:
        """执行带范围的生成计划
        
        使用细粒度工具精确执行章节范围生成
        
        开发者: Jamesenh
        开发时间: 2025-12-16
        更新: 2025-12-16 - 使用细粒度工具替代工作流降级
        """
        target_display = NODE_DISPLAY_NAMES.get(plan.target_node, plan.target_node)
        scope = plan.chapter_scope
        
        if plan.can_execute_precisely:
            # 使用细粒度工具精确执行
            if plan.target_node == "chapter_planning":
                # 调用 chapter.plan.generate
                tool_params = {
                    "chapter_scope_start": scope.start,
                    "chapter_scope_end": scope.end,
                    "missing_only": True,
                    "force": False
                }
                
                tool_plan = self.registry.create_plan("chapter.plan.generate", tool_params)
                tool_plan.requires_confirmation = False
                result = self.registry.execute_plan(tool_plan)
                
                if result.success:
                    data = result.data or {}
                    generated = data.get("generated", [])
                    skipped = data.get("skipped", [])
                    
                    response = f"✅ **章节计划生成完成**\n\n"
                    if generated:
                        response += f"📝 已生成: 第 {', '.join(map(str, generated))} 章\n"
                    if skipped:
                        response += f"⏭️ 已跳过: 第 {', '.join(map(str, skipped))} 章（已存在）\n"
                    response += f"\n{result.message or ''}"
                    return response
                else:
                    # 检查是否是缺失依赖
                    data = result.data or {}
                    missing_deps = data.get("missing_deps", [])
                    if missing_deps:
                        return (
                            f"❌ 缺失前置依赖: {', '.join(missing_deps)}\n\n"
                            f"请先生成: {', '.join(missing_deps)}"
                        )
                    return f"❌ 生成失败: {result.error}"
            
            elif plan.target_node == "chapter_text":
                # 调用 chapter.text.generate
                tool_params = {
                    "chapter_scope_start": scope.start,
                    "chapter_scope_end": scope.end,
                    "missing_only": True,
                    "force": False,
                    "sequential": True
                }
                
                tool_plan = self.registry.create_plan("chapter.text.generate", tool_params)
                tool_plan.requires_confirmation = False
                result = self.registry.execute_plan(tool_plan)
                
                if result.success:
                    data = result.data or {}
                    generated = data.get("generated", [])
                    skipped = data.get("skipped", [])
                    total_words = data.get("total_words", 0)
                    
                    response = f"✅ **章节正文生成完成**\n\n"
                    if generated:
                        response += f"📝 已生成: 第 {', '.join(map(str, generated))} 章\n"
                    if skipped:
                        response += f"⏭️ 已跳过: 第 {', '.join(map(str, skipped))} 章（已存在）\n"
                    response += f"📊 总字数: {total_words:,} 字\n"
                    response += f"\n{result.message or ''}"
                    return response
                else:
                    # 检查是否是顺序约束阻塞
                    data = result.data or {}
                    blocked_by = data.get("blocked_by_missing", [])
                    if blocked_by:
                        return (
                            f"❌ **顺序约束阻塞**\n\n"
                            f"第 {', '.join(map(str, blocked_by))} 章正文缺失，无法跳过生成。\n\n"
                            f"**建议**：\n"
                            f"1. 先生成第 1-{blocked_by[-1]} 章正文\n"
                            f"2. 或说「生成第 1-{scope.end} 章正文」补齐全部"
                        )
                    
                    missing_plans = data.get("missing_plans", [])
                    if missing_plans:
                        return (
                            f"❌ 第 {', '.join(map(str, missing_plans))} 章缺少计划\n\n"
                            f"请先使用「生成第 {missing_plans[0]}-{missing_plans[-1]} 章计划」生成章节计划"
                        )
                    
                    return f"❌ 生成失败: {result.error}"
            else:
                return f"⚠️ 不支持的目标类型: {plan.target_node}"
        
        else:
            # 降级执行（向后兼容，但新逻辑应该不会走到这里）
            if plan.target_node == "chapter_planning":
                workflow_plan = self.registry.create_plan(
                    "workflow.run",
                    {"stop_at": "chapter_planning"}
                )
                workflow_plan.requires_confirmation = False
                result = self.registry.execute_plan(workflow_plan)
                
                if result.success:
                    return (
                        f"✅ **全量章节计划** 生成完成\n\n"
                        f"注意：已生成所有章节的计划（非仅 {plan.chapter_scope}）\n\n"
                        f"{result.message or ''}"
                    )
                else:
                    return f"❌ 生成失败: {result.error}"
            else:
                workflow_plan = self.registry.create_plan("workflow.resume", {})
                workflow_plan.requires_confirmation = False
                result = self.registry.execute_plan(workflow_plan)
                
                if result.success:
                    return f"✅ 生成完成\n\n{result.message or ''}"
                else:
                    return f"❌ 生成失败: {result.error}"
    
    def _cancel_pending_plan(self) -> str:
        """取消待执行的计划
        
        更新: 2025-12-16 - 支持 TargetedGenerationPlan 和 ScopedGenerationPlan
        """
        if self.pending_plan is None:
            return "当前没有待取消的操作"
        
        plan = self.pending_plan
        self.pending_plan = None
        
        # 为目标型生成提供替代建议
        if isinstance(plan, TargetedGenerationPlan):
            target_display = NODE_DISPLAY_NAMES.get(plan.target_node, plan.target_node)
            
            if plan.missing_deps:
                missing_display = [NODE_DISPLAY_NAMES.get(d, d) for d in plan.missing_deps]
                return (
                    f"✅ 已取消生成 **{target_display}**\n\n"
                    f"💡 替代建议：\n"
                    f"  - 先单独生成缺失的前置：\n"
                    + "\n".join([f"    • 说「生成{d}」" for d in missing_display]) +
                    f"\n  - 或使用 `/run` 执行完整流程"
                )
            else:
                return f"✅ 已取消生成 **{target_display}**"
        
        # 为带范围的生成提供替代建议
        if isinstance(plan, ScopedGenerationPlan):
            target_display = NODE_DISPLAY_NAMES.get(plan.target_node, plan.target_node)
            return (
                f"✅ 已取消生成 **{plan.chapter_scope}** 的 **{target_display}**\n\n"
                f"💡 你可以尝试：\n"
                f"  - 使用 `/run` 执行完整流程\n"
                f"  - 使用 `/resume` 继续生成\n"
                f"  - 说「生成{target_display}」生成全量内容"
            )
        
        return "✅ 操作已取消"
    
    def _execute_targeted_generation(self, plan: TargetedGenerationPlan) -> str:
        """执行目标型生成计划
        
        调用 workflow.run(stop_at=<target_node>) 执行到目标节点后停止
        
        Args:
            plan: 目标型生成计划
            
        Returns:
            执行结果消息
            
        开发者: Jamesenh
        开发时间: 2025-12-16
        """
        target_display = NODE_DISPLAY_NAMES.get(plan.target_node, plan.target_node)
        
        # 创建带 stop_at 参数的工作流执行计划
        workflow_plan = self.registry.create_plan(
            "workflow.run",
            {"stop_at": plan.target_node}
        )
        workflow_plan.requires_confirmation = False  # 已经确认过了
        
        # 执行工作流
        result = self.registry.execute_plan(workflow_plan)
        
        if result.success:
            return (
                f"✅ **{target_display}** 生成完成\n\n"
                f"{result.message or ''}\n\n"
                f"💡 下一步建议：\n"
                f"  - 使用 `/status` 查看当前状态\n"
                f"  - 继续生成下一阶段（如「生成大纲」）\n"
                f"  - 使用 `/run` 或 `/resume` 执行完整流程"
            )
        else:
            return f"❌ 生成 **{target_display}** 失败: {result.error}"
    
    def _execute_and_format(self, plan) -> str:
        """执行计划并格式化结果"""
        result = self.registry.execute_plan(plan)
        
        if result.success:
            response = f"✅ {result.message or '操作成功'}"
            if result.data:
                # 简单格式化数据
                response += f"\n\n{self._format_data(result.data)}"
            return response
        else:
            return f"❌ 操作失败: {result.error}"
    
    def _format_data(self, data: Dict[str, Any], indent: int = 0) -> str:
        """格式化数据为可读字符串"""
        lines = []
        prefix = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_data(value, indent + 1))
            elif isinstance(value, list):
                if len(value) == 0:
                    lines.append(f"{prefix}{key}: (空)")
                elif len(value) <= 5:
                    lines.append(f"{prefix}{key}: {', '.join(str(v) for v in value)}")
                else:
                    lines.append(f"{prefix}{key}: {len(value)} 项")
            else:
                lines.append(f"{prefix}{key}: {value}")
        
        return "\n".join(lines)
    
    def _parse_args(self, args: str, tool_name: str) -> Dict[str, Any]:
        """解析命令参数"""
        params = {}
        args = args.strip()
        
        if not args:
            return params
        
        # 根据工具类型解析参数
        if tool_name == "graph.whois":
            params["name"] = args
        elif tool_name == "graph.relations":
            parts = args.split("--with")
            params["name"] = parts[0].strip()
            if len(parts) > 1:
                params["with_name"] = parts[1].strip()
        elif tool_name == "graph.events":
            params["character_name"] = args
        elif tool_name == "preference.set":
            params["content"] = args
        elif tool_name == "preference.forget":
            params["keyword"] = args
        elif tool_name == "workflow.rollback":
            try:
                params["chapter_number"] = int(args)
            except ValueError:
                pass
        # 审查与修订工具参数
        elif tool_name in ["review.report", "review.generate_fix", "review.apply", "review.status"]:
            try:
                params["chapter_number"] = int(args)
            except ValueError:
                pass
        elif tool_name == "review.reject":
            parts = args.split(maxsplit=1)
            if parts:
                try:
                    params["chapter_number"] = int(parts[0])
                    if len(parts) > 1:
                        params["reason"] = parts[1]
                except ValueError:
                    pass
        
        return params
    
    def _get_help_message(self) -> str:
        """获取帮助信息
        
        更新: 2025-12-16 - 添加范围解析与澄清说明
        """
        return """📚 **NovelGen Chat 帮助**

**工作流命令:**
  /run         - 开始生成完整小说
  /resume      - 从检查点继续生成
  /status      - 查看项目状态
  /export      - 导出小说为文本
  /rollback N  - 回滚到第 N 章之前

**偏好管理:**
  /setpref <内容>  - 设置写作偏好
  /prefs           - 查看所有偏好
  /forget <关键词> - 删除包含关键词的偏好

**图谱查询:**
  /whois <角色名>              - 查询角色信息
  /relations <角色名>          - 查询角色关系
  /relations <A> --with <B>    - 查询两人关系
  /events <角色名>             - 查询角色事件

**审查与修订:**
  /pending                     - 列出所有 pending 修订
  /review <章节号>             - 查看审查报告
  /fix <章节号>                - 生成修订候选
  /accept <章节号>             - 应用修订（替换原章节）
  /reject <章节号>             - 拒绝修订（解除阻断）

**会话控制:**
  /auto on|off  - 开关自动确认模式
  /yes, /y      - 确认待执行操作
  /no, /n       - 取消待执行操作
  /help         - 显示此帮助
  /quit, /exit  - 退出对话

**自然语言示例:**

  📖 *全流程生成*（触发完整工作流）：
  - "开始生成"
  - "继续生成"
  - "一键生成"

  🎯 *目标型生成*（只生成到指定阶段）：
  - "生成世界观"      → 停在 world_creation
  - "生成人物角色"    → 停在 character_creation（自动补齐缺失前置）
  - "生成大纲"        → 停在 outline_creation
  - "生成章节计划"    → 生成所有章节的详细计划

  📏 *带范围的生成*（系统会识别范围并确认）：
  - "生成前3章的章节计划"
  - "生成第2-5章的章节计划"
  - "生成前三章的章节计划"（支持中文数字）
  - "生成第十章到第十五章"

  ⚠️ *范围限制说明*：
  当前章节计划/正文生成暂不支持精确范围执行，
  系统会在识别到范围时提示限制并提供替代方案。

  ❓ *其他*：
  - "林风是谁？"      → 查询角色
  - "查看当前进度"    → 状态查询
"""


def typewriter_print(
    text: str, 
    chars_per_second: float = 20.0,
    console = None,
    prefix: str = ""
):
    """打字机效果输出文本
    
    逐字符输出文本，模拟打字机效果。使用 Rich Live 实现带格式的打字机效果。
    
    Args:
        text: 要输出的文本（支持 Rich markup）
        chars_per_second: 每秒输出字符数，默认 20 字/秒
        console: Rich Console 实例，如不提供则创建新实例
        prefix: 输出前缀（如 "[bold blue]助手[/bold blue]: "），前缀会立即显示
        
    开发者: Jamesenh
    开发时间: 2025-12-16
    """
    from rich.console import Console
    from rich.text import Text
    from rich.live import Live
    
    if console is None:
        console = Console()
    
    # 计算每字符延迟（秒）
    delay = 1.0 / chars_per_second
    
    # 解析前缀
    if prefix:
        try:
            prefix_text = Text.from_markup(prefix)
        except Exception:
            prefix_text = Text(prefix)
    else:
        prefix_text = Text()
    
    # 解析 Rich markup 获取带样式的 Text 对象
    try:
        full_text = Text.from_markup(text)
    except Exception:
        # 如果 markup 解析失败，使用纯文本
        full_text = Text(text)
    
    # 获取纯文本用于迭代
    plain_text = full_text.plain
    
    # 使用 Live 逐字符更新显示
    # transient=False 让最终结果保留在屏幕上
    with Live(prefix_text.copy(), console=console, refresh_per_second=60, transient=False) as live:
        for i, char in enumerate(plain_text):
            # 从原始 Text 对象中切片以保留样式，并加上前缀
            displayed_text = prefix_text.copy()
            displayed_text.append_text(full_text[:i + 1])
            live.update(displayed_text)
            
            # 换行时延迟更短
            if char == '\n':
                time.sleep(delay * 0.2)
            else:
                time.sleep(delay)


def start_chat_session(project_id: str):
    """启动对话会话
    
    Args:
        project_id: 项目ID
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich import print as rprint
    
    console = Console()
    project_dir = os.path.join("projects", project_id)
    
    # 检查项目是否存在
    if not os.path.exists(project_dir):
        rprint(f"[red]❌ 项目 '{project_id}' 不存在[/red]")
        return
    
    # 创建 Agent
    agent = ChatAgent(project_dir, project_id)
    
    # 显示欢迎信息
    console.print(Panel(
        f"[bold cyan]NovelGen Chat[/bold cyan]\n"
        f"项目: [bold]{project_id}[/bold]\n\n"
        f"输入自然语言或斜杠命令与我交互\n"
        f"输入 /help 查看帮助，/quit 退出",
        title="🤖 AI 助手",
        expand=False
    ))
    
    # 显示项目摘要
    try:
        summary = agent.get_project_summary()
        completed = summary.get("completed_chapters", 0)
        total_words = summary.get("total_words", 0)
        rprint(f"\n📊 当前进度: 已完成 {completed} 章，共 {total_words:,} 字")
        
        # 显示偏好摘要
        prefs = agent.get_preferences_summary(limit=3)
        if prefs:
            rprint(f"📝 写作偏好: {len(prefs)} 条")
    except Exception:
        pass
    
    rprint("")
    
    # 主循环
    while True:
        try:
            user_input = Prompt.ask("[bold green]你[/bold green]")
            
            if not user_input.strip():
                continue
            
            # 处理输入
            if user_input.startswith("/"):
                # 斜杠命令
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                response = agent.handle_slash_command(command, args)
            else:
                # 自然语言
                response = agent.handle_natural_language(user_input)
            
            # 检查退出
            if response == "__EXIT__":
                rprint("\n[dim]再见！[/dim]")
                break
            
            # 显示响应（打字机效果，20 字/秒）
            console.print()  # 空行
            typewriter_print(
                response, 
                chars_per_second=50.0, 
                console=console,
                prefix="[bold blue]助手[/bold blue]: "
            )
            console.print()  # 空行
            
        except KeyboardInterrupt:
            rprint("\n\n[dim]使用 /quit 退出[/dim]")
        except EOFError:
            break
