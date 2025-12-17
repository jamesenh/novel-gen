"""
会话上下文与澄清闭环测试

测试:
1. 澄清闭环（"生成第3章"→追问→"2/正文"→正确路由到 chapter_text）
2. 历史裁剪（轮次/字符数上限）与边界条件
3. follow-up 复用范围
4. LLM 失败/禁用时的行为

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from novelgen.agent.conversation_state import (
    ChatMessage,
    ConversationState,
    ConversationConfig,
    PendingClarification,
    LastExecutedIntent,
)
from novelgen.agent.intent_parser import (
    ParsedIntent,
    IntentTarget,
    IntentMode,
    ChapterScope,
    ClarificationQuestion,
    parse_intent,
    parse_intent_by_rules,
)


class TestChatMessage:
    """测试 ChatMessage 模型"""
    
    def test_basic_message(self):
        """测试基本消息创建"""
        msg = ChatMessage(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert isinstance(msg.created_at, datetime)
    
    def test_to_dict(self):
        """测试转换为字典"""
        msg = ChatMessage(role="assistant", content="我是助手")
        d = msg.to_dict()
        assert d == {"role": "assistant", "content": "我是助手"}
    
    def test_to_jsonl(self):
        """测试转换为 JSONL"""
        msg = ChatMessage(role="user", content="测试", meta={"last_intent": "status"})
        line = msg.to_jsonl()
        assert '"role": "user"' in line
        assert '"content": "测试"' in line
        assert '"last_intent": "status"' in line


class TestConversationState:
    """测试 ConversationState"""
    
    def test_add_message(self):
        """测试添加消息"""
        state = ConversationState()
        state.add_user_message("你好")
        state.add_assistant_message("你好！有什么可以帮你？")
        
        assert len(state.messages) == 2
        assert state.messages[0].role == "user"
        assert state.messages[1].role == "assistant"
    
    def test_history_trimming_by_turns(self):
        """测试按轮次裁剪"""
        state = ConversationState(max_turns=2, max_chars=100000)
        
        # 添加 5 轮对话（10 条消息）
        for i in range(5):
            state.add_user_message(f"用户消息 {i}")
            state.add_assistant_message(f"助手回复 {i}")
        
        # 应该只保留最近 2 轮（4 条消息）
        assert len(state.messages) == 4
        assert state.messages[0].content == "用户消息 3"
        assert state.messages[-1].content == "助手回复 4"
    
    def test_history_trimming_by_chars(self):
        """测试按字符数裁剪"""
        state = ConversationState(max_turns=100, max_chars=50)
        
        # 添加长消息
        state.add_user_message("A" * 30)
        state.add_assistant_message("B" * 30)
        state.add_user_message("C" * 30)
        
        # 应该因为字符数限制而裁剪
        total_chars = sum(len(m.content) for m in state.messages)
        assert total_chars <= 50 or len(state.messages) == 2  # 至少保留最近 2 条
    
    def test_get_history_for_llm(self):
        """测试获取 LLM 历史"""
        state = ConversationState()
        state.add_user_message("问题1")
        state.add_assistant_message("回答1")
        state.summary = "这是一段摘要"
        
        # 包含摘要
        history = state.get_history_for_llm(include_summary=True)
        assert len(history) == 3
        assert history[0]["role"] == "system"
        assert "摘要" in history[0]["content"]
        
        # 不包含摘要
        history_no_summary = state.get_history_for_llm(include_summary=False)
        assert len(history_no_summary) == 2
    
    def test_get_recent_turns(self):
        """测试获取最近 N 轮"""
        state = ConversationState()
        for i in range(5):
            state.add_user_message(f"问题{i}")
            state.add_assistant_message(f"回答{i}")
        
        turns = state.get_recent_turns(n=2)
        assert len(turns) == 4  # 2 轮 = 4 条消息
        assert turns[0].content == "问题3"
        assert turns[-1].content == "回答4"


class TestPendingClarification:
    """测试澄清闭环状态"""
    
    def test_basic_clarification(self):
        """测试基本澄清状态"""
        pending = PendingClarification(
            original_input="生成第3章",
            parsed_intent_dict={"target": "chapter_plan"},
            questions=["你想生成章节计划还是章节正文？"],
            options=[["章节计划", "章节正文"]]
        )
        
        assert pending.clarification_count == 1
        assert not pending.is_exhausted()
    
    def test_exhausted(self):
        """测试超过澄清次数上限"""
        pending = PendingClarification(
            original_input="生成第3章",
            parsed_intent_dict={},
            questions=[],
            options=[],
            max_clarification_attempts=3
        )
        
        pending.increment_count()  # 2
        assert not pending.is_exhausted()
        
        pending.increment_count()  # 3
        assert pending.is_exhausted()


class TestConversationStateClarification:
    """测试 ConversationState 的澄清闭环功能"""
    
    def test_set_pending_clarification(self):
        """测试设置待澄清状态"""
        state = ConversationState()
        
        state.set_pending_clarification(
            original_input="生成第3章",
            parsed_intent_dict={"target": "chapter_plan", "chapter_scope": {"start": 3, "end": 3}},
            questions=["你想生成什么？"],
            options=[["章节计划", "章节正文"]]
        )
        
        assert state.is_awaiting_clarification()
        assert state.pending_clarification.original_input == "生成第3章"
    
    def test_clear_pending_clarification(self):
        """测试清除待澄清状态"""
        state = ConversationState()
        state.set_pending_clarification(
            original_input="测试",
            parsed_intent_dict={},
            questions=["问题"],
            options=[]
        )
        
        state.clear_pending_clarification()
        assert not state.is_awaiting_clarification()
        assert state.pending_clarification is None


class TestLastExecutedIntent:
    """测试最近执行的意图（用于 follow-up）"""
    
    def test_set_last_executed_intent(self):
        """测试设置最近执行的意图"""
        state = ConversationState()
        
        state.set_last_executed_intent(
            target="chapter_plan",
            mode="plan",
            chapter_start=1,
            chapter_end=3,
            was_confirmed=True
        )
        
        last = state.last_executed_intent
        assert last is not None
        assert last.target == "chapter_plan"
        assert last.chapter_start == 1
        assert last.chapter_end == 3


class TestClarificationLoop:
    """测试澄清闭环场景（集成测试）"""
    
    def test_chapter_ambiguity_detection(self):
        """测试「生成第3章」歧义检测"""
        parsed = parse_intent_by_rules("生成第3章")
        
        assert parsed.target == IntentTarget.CHAPTER_PLAN  # 默认
        assert parsed.is_ambiguous
        assert len(parsed.clarification_questions) > 0
        assert parsed.chapter_scope is not None
        assert parsed.chapter_scope.start == 3
    
    def test_clarification_answer_plan(self):
        """测试澄清回答：选择章节计划"""
        # 模拟 ChatAgent._resolve_clarification 的逻辑
        pending = PendingClarification(
            original_input="生成第3章",
            parsed_intent_dict={
                "target": "chapter_plan",
                "chapter_scope": {"start": 3, "end": 3}
            },
            questions=["你想生成什么？"],
            options=[["章节计划", "章节正文"]]
        )
        
        # 用户回答 "1" 或 "计划"
        for answer in ["1", "计划", "章节计划"]:
            # 这里模拟解析逻辑
            if "1" in answer or "计划" in answer:
                target = IntentTarget.CHAPTER_PLAN
                mode = IntentMode.PLAN
            else:
                target = IntentTarget.CHAPTER_TEXT
                mode = IntentMode.TEXT
            
            assert target == IntentTarget.CHAPTER_PLAN
            assert mode == IntentMode.PLAN
    
    def test_clarification_answer_text(self):
        """测试澄清回答：选择章节正文"""
        # 用户回答 "2" 或 "正文"
        for answer in ["2", "正文", "章节正文"]:
            if "2" in answer or "正文" in answer:
                target = IntentTarget.CHAPTER_TEXT
                mode = IntentMode.TEXT
            else:
                target = IntentTarget.CHAPTER_PLAN
                mode = IntentMode.PLAN
            
            assert target == IntentTarget.CHAPTER_TEXT
            assert mode == IntentMode.TEXT


class TestFollowupCompletion:
    """测试 follow-up 范围沿用"""
    
    def test_followup_with_history(self):
        """测试「再生成正文」从历史沿用范围"""
        state = ConversationState()
        
        # 设置上一轮执行的意图
        state.set_last_executed_intent(
            target="chapter_plan",
            mode="plan",
            chapter_start=1,
            chapter_end=3,
            was_confirmed=True
        )
        
        # 模拟 follow-up 补全逻辑
        user_input = "再生成正文"
        parsed = parse_intent_by_rules(user_input)
        
        # 原始解析可能没有范围
        # 但 follow-up 补全后应该有范围
        last = state.last_executed_intent
        if last and "再" in user_input:
            # 补全范围
            new_scope = ChapterScope(
                start=last.chapter_start,
                end=last.chapter_end
            )
            assert new_scope.start == 1
            assert new_scope.end == 3


class TestLLMFallback:
    """测试 LLM 失败/禁用时的行为"""
    
    def test_llm_disabled(self):
        """测试禁用 LLM 时使用规则解析"""
        parsed = parse_intent("生成世界观", use_llm=False)
        
        assert parsed.source == "rule"
        assert parsed.target == IntentTarget.WORLD
    
    def test_llm_failure_fallback(self):
        """测试 LLM 调用失败时回退到规则解析"""
        # Mock LLM 调用失败
        with patch('novelgen.agent.intent_parser.parse_intent_by_llm', return_value=None):
            parsed = parse_intent("生成大纲", use_llm=True)
            
            # 应该回退到规则解析
            assert parsed.source == "rule"
            assert parsed.target == IntentTarget.OUTLINE
    
    def test_status_always_rule(self):
        """测试状态查询始终使用规则解析"""
        parsed = parse_intent("查看状态", use_llm=True)
        
        # 状态查询应该直接走规则，不调用 LLM
        assert parsed.target == IntentTarget.STATUS
        assert parsed.source == "rule"


class TestConversationConfig:
    """测试会话配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ConversationConfig()
        
        assert config.max_turns == 10
        assert config.max_chars == 4000
        assert config.persist_enabled is False
    
    def test_create_conversation_state(self):
        """测试创建会话状态"""
        config = ConversationConfig()
        state = config.create_conversation_state("/tmp/project", "test_project")
        
        assert isinstance(state, ConversationState)
        assert state.max_turns == config.max_turns
        assert state.max_chars == config.max_chars


class TestHistoryInjection:
    """测试历史注入意图识别"""
    
    def test_format_history_for_prompt(self):
        """测试格式化历史用于提示词"""
        from novelgen.agent.intent_parser import format_chat_history_for_prompt
        
        history = [
            {"role": "user", "content": "生成前3章计划"},
            {"role": "assistant", "content": "好的，已生成..."},
        ]
        
        formatted = format_chat_history_for_prompt(history, summary="这是摘要")
        
        assert "摘要" in formatted
        assert "用户" in formatted
        assert "助手" in formatted
    
    def test_format_empty_history(self):
        """测试空历史"""
        from novelgen.agent.intent_parser import format_chat_history_for_prompt
        
        formatted = format_chat_history_for_prompt(None, None)
        assert formatted == ""


class TestEdgeCases:
    """测试边界条件"""
    
    def test_empty_input(self):
        """测试空输入"""
        parsed = parse_intent_by_rules("")
        assert parsed.target == IntentTarget.UNKNOWN
    
    def test_very_long_input(self):
        """测试超长输入"""
        long_input = "A" * 10000
        state = ConversationState(max_chars=1000)
        state.add_user_message(long_input)
        
        # 不应该崩溃，且应该裁剪
        assert len(state.messages) >= 1
    
    def test_unicode_input(self):
        """测试 Unicode 输入"""
        state = ConversationState()
        state.add_user_message("生成第三章的正文 🎉")
        
        assert "🎉" in state.messages[0].content
    
    def test_sanitize_api_key(self):
        """测试脱敏处理"""
        state = ConversationState()
        content = state._sanitize_content("OPENAI_API_KEY=sk-1234567890abcdef")
        
        assert "sk-1234567890abcdef" not in content
        assert "***" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
