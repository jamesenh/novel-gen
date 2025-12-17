"""
对话式 Agent 模块
提供 ng chat 命令的核心功能，支持自然语言驱动生成/查询/回滚等动作

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
更新: 2025-12-16 - 添加会话上下文管理
"""

from novelgen.agent.chat import ChatAgent
from novelgen.agent.conversation_state import (
    ChatMessage,
    ConversationState,
    ConversationConfig,
    PendingClarification,
    LastExecutedIntent,
)

__all__ = [
    "ChatAgent",
    "ChatMessage",
    "ConversationState", 
    "ConversationConfig",
    "PendingClarification",
    "LastExecutedIntent",
]
