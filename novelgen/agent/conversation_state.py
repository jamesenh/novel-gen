"""
会话上下文状态管理模块

提供:
1. ChatMessage - 单条消息模型
2. ConversationState - 会话状态管理（含裁剪/摘要/落盘）
3. PendingClarification - 澄清闭环状态

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """单条会话消息
    
    记录用户或助手的一次发言，包含结构化元信息
    """
    role: Literal["user", "assistant"] = Field(description="消息角色")
    content: str = Field(description="消息内容")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    # 可选结构化元信息
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="可选元信息：last_intent, last_scope, confirmation_result 等"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 LLM 输入）"""
        return {
            "role": self.role,
            "content": self.content,
        }
    
    def to_jsonl(self) -> str:
        """转换为 JSONL 格式（用于落盘）"""
        data = {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }
        # 只保存必要的 meta 字段
        safe_meta = {}
        for key in ["last_intent", "last_scope", "confirmation_result"]:
            if key in self.meta:
                safe_meta[key] = self.meta[key]
        if safe_meta:
            data["meta"] = safe_meta
        return json.dumps(data, ensure_ascii=False)


class PendingClarification(BaseModel):
    """待澄清状态
    
    保存上一轮产生的待澄清意图及相关信息，
    用于下一轮消费澄清回答
    """
    original_input: str = Field(description="用户原始输入")
    parsed_intent_dict: Dict[str, Any] = Field(description="上一轮解析的意图（序列化后）")
    questions: List[str] = Field(default_factory=list, description="澄清问题列表")
    options: List[List[str]] = Field(default_factory=list, description="每个问题的选项列表")
    clarification_count: int = Field(default=1, description="已澄清次数")
    max_clarification_attempts: int = Field(default=3, description="最大澄清次数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    def is_exhausted(self) -> bool:
        """是否超过澄清次数上限"""
        return self.clarification_count >= self.max_clarification_attempts
    
    def increment_count(self):
        """增加澄清次数"""
        self.clarification_count += 1


class LastExecutedIntent(BaseModel):
    """最近一次执行的意图
    
    用于 follow-up 场景的范围沿用
    """
    target: str = Field(description="目标类型（如 chapter_plan, chapter_text）")
    mode: Optional[str] = Field(default=None, description="模式（plan/text）")
    chapter_start: Optional[int] = Field(default=None, description="章节范围起始")
    chapter_end: Optional[int] = Field(default=None, description="章节范围结束")
    executed_at: datetime = Field(default_factory=datetime.now, description="执行时间")
    was_confirmed: bool = Field(default=True, description="是否经过确认")


class ConversationState(BaseModel):
    """会话状态管理
    
    管理对话历史、裁剪策略、澄清闭环状态
    """
    messages: List[ChatMessage] = Field(default_factory=list, description="消息历史")
    summary: Optional[str] = Field(default=None, description="长会话摘要（可选）")
    
    # 裁剪配置
    max_turns: int = Field(default=10, description="最大保留轮次")
    max_chars: int = Field(default=4000, description="最大保留字符数")
    max_summary_chars: int = Field(default=500, description="摘要最大字符数")
    
    # 澄清闭环状态
    pending_clarification: Optional[PendingClarification] = Field(
        default=None, 
        description="待澄清状态"
    )
    
    # 最近执行的意图（用于 follow-up）
    last_executed_intent: Optional[LastExecutedIntent] = Field(
        default=None,
        description="最近一次确认并执行的意图"
    )
    
    # 落盘配置
    persist_enabled: bool = Field(default=False, description="是否启用落盘")
    persist_path: Optional[str] = Field(default=None, description="落盘文件路径")
    persist_max_lines: int = Field(default=1000, description="落盘最大行数")
    
    def add_message(self, role: Literal["user", "assistant"], content: str, meta: Optional[Dict[str, Any]] = None):
        """添加消息并自动裁剪
        
        Args:
            role: 消息角色
            content: 消息内容
            meta: 可选元信息
        """
        message = ChatMessage(
            role=role,
            content=content,
            meta=meta or {}
        )
        self.messages.append(message)
        
        # 自动裁剪
        self._trim_history()
        
        # 落盘（如果启用）
        if self.persist_enabled and self.persist_path:
            self._persist_message(message)
    
    def add_user_message(self, content: str, meta: Optional[Dict[str, Any]] = None):
        """添加用户消息"""
        self.add_message("user", content, meta)
    
    def add_assistant_message(self, content: str, meta: Optional[Dict[str, Any]] = None):
        """添加助手消息"""
        self.add_message("assistant", content, meta)
    
    def get_history_for_llm(self, include_summary: bool = True) -> List[Dict[str, str]]:
        """获取用于 LLM 的历史消息
        
        Args:
            include_summary: 是否包含摘要
            
        Returns:
            消息列表（role + content）
        """
        result = []
        
        # 添加摘要（如果有）
        if include_summary and self.summary:
            result.append({
                "role": "system",
                "content": f"[之前对话摘要] {self.summary}"
            })
        
        # 添加最近消息
        for msg in self.messages:
            result.append(msg.to_dict())
        
        return result
    
    def get_recent_turns(self, n: int = 3) -> List[ChatMessage]:
        """获取最近 N 轮对话
        
        Args:
            n: 轮次数
            
        Returns:
            最近 N 轮的消息列表
        """
        # 一轮 = 一对 user + assistant 消息
        # 从后往前找
        turns = []
        user_msg = None
        assistant_msg = None
        
        for msg in reversed(self.messages):
            if msg.role == "assistant" and assistant_msg is None:
                assistant_msg = msg
            elif msg.role == "user" and assistant_msg is not None:
                user_msg = msg
                turns.append((user_msg, assistant_msg))
                user_msg = None
                assistant_msg = None
                
                if len(turns) >= n:
                    break
        
        # 反转回正序
        turns.reverse()
        
        # 展平为消息列表
        result = []
        for u, a in turns:
            result.append(u)
            result.append(a)
        
        return result
    
    def _trim_history(self):
        """裁剪历史消息
        
        策略：
        1. 优先保留最近 max_turns 轮
        2. 同时保证总字符数不超过 max_chars
        3. 若仍超限：从最旧消息开始移除
        """
        if not self.messages:
            return
        
        # 计算当前字符数
        total_chars = sum(len(msg.content) for msg in self.messages)
        
        # 轮次限制：一轮 = user + assistant，但为简化，按消息数限制
        max_messages = self.max_turns * 2
        
        # 如果消息数超过限制，从头部移除
        while len(self.messages) > max_messages:
            removed = self.messages.pop(0)
            total_chars -= len(removed.content)
        
        # 字符数限制：从头部移除直到满足限制
        while total_chars > self.max_chars and len(self.messages) > 2:
            removed = self.messages.pop(0)
            total_chars -= len(removed.content)
    
    def _persist_message(self, message: ChatMessage):
        """持久化单条消息到文件
        
        使用 JSONL 格式追加写入
        """
        if not self.persist_path:
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            
            # 检查文件行数，超过上限时滚动
            if os.path.exists(self.persist_path):
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                if len(lines) >= self.persist_max_lines:
                    # 保留后半部分
                    keep_lines = lines[-(self.persist_max_lines // 2):]
                    with open(self.persist_path, "w", encoding="utf-8") as f:
                        f.writelines(keep_lines)
            
            # 追加写入
            with open(self.persist_path, "a", encoding="utf-8") as f:
                # 脱敏处理：替换疑似敏感信息
                line = message.to_jsonl()
                line = self._sanitize_content(line)
                f.write(line + "\n")
                
        except Exception as e:
            # 落盘失败不阻断主流程
            print(f"⚠️ 会话历史落盘失败: {e}")
    
    def _sanitize_content(self, content: str) -> str:
        """脱敏处理
        
        替换疑似敏感信息（如 API Key）
        """
        import re
        # 替换疑似 API Key 的模式
        patterns = [
            (r'(OPENAI_API_KEY|API_KEY|SECRET_KEY|PASSWORD)=\S+', r'\1=***'),
            (r'sk-[a-zA-Z0-9]{20,}', 'sk-***'),
            (r'Bearer [a-zA-Z0-9._-]+', 'Bearer ***'),
        ]
        result = content
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
    
    def set_pending_clarification(
        self, 
        original_input: str, 
        parsed_intent_dict: Dict[str, Any],
        questions: List[str],
        options: List[List[str]]
    ):
        """设置待澄清状态
        
        Args:
            original_input: 用户原始输入
            parsed_intent_dict: 解析的意图（序列化后）
            questions: 澄清问题列表
            options: 每个问题的选项列表
        """
        self.pending_clarification = PendingClarification(
            original_input=original_input,
            parsed_intent_dict=parsed_intent_dict,
            questions=questions,
            options=options
        )
    
    def clear_pending_clarification(self):
        """清除待澄清状态"""
        self.pending_clarification = None
    
    def set_last_executed_intent(
        self,
        target: str,
        mode: Optional[str] = None,
        chapter_start: Optional[int] = None,
        chapter_end: Optional[int] = None,
        was_confirmed: bool = True
    ):
        """设置最近执行的意图
        
        Args:
            target: 目标类型
            mode: 模式
            chapter_start: 章节范围起始
            chapter_end: 章节范围结束
            was_confirmed: 是否经过确认
        """
        self.last_executed_intent = LastExecutedIntent(
            target=target,
            mode=mode,
            chapter_start=chapter_start,
            chapter_end=chapter_end,
            was_confirmed=was_confirmed
        )
    
    def has_pending_clarification(self) -> bool:
        """是否有待澄清状态"""
        return self.pending_clarification is not None
    
    def is_awaiting_clarification(self) -> bool:
        """是否处于等待澄清回答状态"""
        return self.has_pending_clarification()


class ConversationConfig(BaseModel):
    """会话配置（从环境变量读取）
    
    配置项：
    - CHAT_MAX_TURNS: 最大保留轮次（默认 10）
    - CHAT_MAX_CHARS: 最大保留字符数（默认 4000）
    - CHAT_PERSIST_ENABLED: 是否启用落盘（默认 false）
    - CHAT_MAX_CLARIFICATION_ATTEMPTS: 最大澄清次数（默认 3）
    """
    max_turns: int = Field(default=10)
    max_chars: int = Field(default=4000)
    max_summary_chars: int = Field(default=500)
    persist_enabled: bool = Field(default=False)
    persist_max_lines: int = Field(default=1000)
    max_clarification_attempts: int = Field(default=3)
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # 从环境变量读取配置
        import os
        
        if os.getenv("CHAT_MAX_TURNS"):
            self.max_turns = int(os.getenv("CHAT_MAX_TURNS"))
        if os.getenv("CHAT_MAX_CHARS"):
            self.max_chars = int(os.getenv("CHAT_MAX_CHARS"))
        if os.getenv("CHAT_MAX_SUMMARY_CHARS"):
            self.max_summary_chars = int(os.getenv("CHAT_MAX_SUMMARY_CHARS"))
        if os.getenv("CHAT_PERSIST_ENABLED"):
            self.persist_enabled = os.getenv("CHAT_PERSIST_ENABLED", "").lower() in ("true", "1", "yes", "on")
        if os.getenv("CHAT_PERSIST_MAX_LINES"):
            self.persist_max_lines = int(os.getenv("CHAT_PERSIST_MAX_LINES"))
        if os.getenv("CHAT_MAX_CLARIFICATION_ATTEMPTS"):
            self.max_clarification_attempts = int(os.getenv("CHAT_MAX_CLARIFICATION_ATTEMPTS"))
    
    def create_conversation_state(self, project_dir: str, project_id: str) -> ConversationState:
        """创建会话状态实例
        
        Args:
            project_dir: 项目目录
            project_id: 项目ID
            
        Returns:
            配置好的 ConversationState 实例
        """
        persist_path = None
        if self.persist_enabled:
            persist_path = os.path.join(project_dir, "chat_history.jsonl")
        
        return ConversationState(
            max_turns=self.max_turns,
            max_chars=self.max_chars,
            max_summary_chars=self.max_summary_chars,
            persist_enabled=self.persist_enabled,
            persist_path=persist_path,
            persist_max_lines=self.persist_max_lines
        )
