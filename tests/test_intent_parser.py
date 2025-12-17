"""
意图识别与范围解析测试

测试 novelgen/agent/intent_parser.py 中的功能：
1. 章节范围解析（中文数字与阿拉伯数字）
2. LLM 意图识别（使用 mock）
3. 规则解析
4. 歧义检测与澄清
5. 真实 LLM 调用测试（需要 OPENAI_API_KEY）

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from novelgen.agent.intent_parser import (
    # 数据结构
    ChapterScope, ParsedIntent, IntentTarget, IntentMode,
    ClarificationQuestion, LLMIntentOutput,
    # 中文数字转换
    chinese_to_arabic,
    # 章节范围解析
    parse_chapter_scope,
    # 规则解析
    parse_intent_by_rules,
    # LLM 解析
    parse_intent_by_llm,
    create_llm_intent_chain,
    # 混合解析
    parse_intent,
    _merge_intents,
)


# 检查是否有可用的 OpenAI API Key
HAS_OPENAI_KEY = bool(os.environ.get("OPENAI_API_KEY"))


class TestChineseToArabic:
    """测试中文数字转阿拉伯数字"""
    
    def test_single_digits(self):
        """测试个位数"""
        assert chinese_to_arabic("一") == 1
        assert chinese_to_arabic("二") == 2
        assert chinese_to_arabic("三") == 3
        assert chinese_to_arabic("四") == 4
        assert chinese_to_arabic("五") == 5
        assert chinese_to_arabic("六") == 6
        assert chinese_to_arabic("七") == 7
        assert chinese_to_arabic("八") == 8
        assert chinese_to_arabic("九") == 9
    
    def test_ten(self):
        """测试十"""
        assert chinese_to_arabic("十") == 10
    
    def test_teens(self):
        """测试十几"""
        assert chinese_to_arabic("十一") == 11
        assert chinese_to_arabic("十二") == 12
        assert chinese_to_arabic("十五") == 15
        assert chinese_to_arabic("十九") == 19
    
    def test_tens(self):
        """测试几十"""
        assert chinese_to_arabic("二十") == 20
        assert chinese_to_arabic("三十") == 30
        assert chinese_to_arabic("五十") == 50
        assert chinese_to_arabic("九十") == 90
    
    def test_tens_with_units(self):
        """测试几十几"""
        assert chinese_to_arabic("二十一") == 21
        assert chinese_to_arabic("三十五") == 35
        assert chinese_to_arabic("九十九") == 99
    
    def test_hundred(self):
        """测试百位数"""
        assert chinese_to_arabic("一百") == 100
        assert chinese_to_arabic("二百") == 200
    
    def test_hundred_with_tens(self):
        """测试一百几十"""
        assert chinese_to_arabic("一百二十") == 120
        assert chinese_to_arabic("一百五十") == 150
    
    def test_hundred_with_tens_and_units(self):
        """测试一百几十几"""
        assert chinese_to_arabic("一百二十三") == 123
        assert chinese_to_arabic("二百四十五") == 245
    
    def test_hundred_with_zero(self):
        """测试一百零几"""
        assert chinese_to_arabic("一百零一") == 101
        assert chinese_to_arabic("一百零五") == 105
    
    def test_arabic_passthrough(self):
        """测试阿拉伯数字直接返回"""
        assert chinese_to_arabic("5") == 5
        assert chinese_to_arabic("15") == 15
        assert chinese_to_arabic("123") == 123
    
    def test_invalid_input(self):
        """测试无效输入"""
        assert chinese_to_arabic("") is None
        assert chinese_to_arabic("abc") is None
        assert chinese_to_arabic("你好") is None
    
    def test_alternative_characters(self):
        """测试繁体/大写数字"""
        assert chinese_to_arabic("壹") == 1
        assert chinese_to_arabic("贰") == 2
        assert chinese_to_arabic("叁") == 3
        assert chinese_to_arabic("两") == 2


class TestParseChapterScope:
    """测试章节范围解析"""
    
    def test_first_n_chapters_arabic(self):
        """测试「前N章」（阿拉伯数字）"""
        scope = parse_chapter_scope("生成前3章的章节计划")
        assert scope is not None
        assert scope.start == 1
        assert scope.end == 3
    
    def test_first_n_chapters_chinese(self):
        """测试「前N章」（中文数字）"""
        scope = parse_chapter_scope("生成前三章的章节计划")
        assert scope is not None
        assert scope.start == 1
        assert scope.end == 3
    
    def test_single_chapter_arabic(self):
        """测试「第N章」（阿拉伯数字）"""
        scope = parse_chapter_scope("生成第5章")
        assert scope is not None
        assert scope.start == 5
        assert scope.end == 5
        assert scope.is_single
    
    def test_single_chapter_chinese(self):
        """测试「第N章」（中文数字）"""
        scope = parse_chapter_scope("生成第十章")
        assert scope is not None
        assert scope.start == 10
        assert scope.end == 10
    
    def test_range_with_dash_arabic(self):
        """测试「第M-N章」（阿拉伯数字）"""
        scope = parse_chapter_scope("生成第2-5章的章节计划")
        assert scope is not None
        assert scope.start == 2
        assert scope.end == 5
    
    def test_range_with_to_arabic(self):
        """测试「第M到N章」（阿拉伯数字）"""
        scope = parse_chapter_scope("生成2到5章的章节计划")
        assert scope is not None
        assert scope.start == 2
        assert scope.end == 5
    
    def test_range_chinese_numerals(self):
        """测试中文数字范围「第十二章到第十五章」"""
        scope = parse_chapter_scope("生成第十二章到第十五章")
        assert scope is not None
        assert scope.start == 12
        assert scope.end == 15
    
    def test_range_short_chinese(self):
        """测试简短中文数字范围「三到五章」"""
        scope = parse_chapter_scope("生成三到五章")
        assert scope is not None
        assert scope.start == 3
        assert scope.end == 5
    
    def test_chapter_to_chapter(self):
        """测试「第M章到第N章」格式"""
        scope = parse_chapter_scope("从第3章到第7章")
        assert scope is not None
        assert scope.start == 3
        assert scope.end == 7
    
    def test_no_chapter_scope(self):
        """测试无章节范围的输入"""
        scope = parse_chapter_scope("生成大纲")
        assert scope is None
    
    def test_chapter_scope_count(self):
        """测试章节数量计算"""
        scope = parse_chapter_scope("前5章")
        assert scope is not None
        assert scope.count == 5
    
    def test_chapter_scope_str(self):
        """测试章节范围字符串表示"""
        scope = parse_chapter_scope("第3章")
        assert str(scope) == "第3章"
        
        scope = parse_chapter_scope("前5章")
        assert str(scope) == "第1-5章"


class TestParseIntentByRules:
    """测试规则解析"""
    
    def test_full_workflow_start(self):
        """测试「开始生成」识别为全流程"""
        intent = parse_intent_by_rules("开始生成")
        assert intent.target == IntentTarget.FULL_WORKFLOW
    
    def test_full_workflow_continue(self):
        """测试「继续生成」识别为全流程"""
        intent = parse_intent_by_rules("继续生成")
        assert intent.target == IntentTarget.FULL_WORKFLOW
    
    def test_target_world(self):
        """测试「生成世界观」"""
        intent = parse_intent_by_rules("生成世界观")
        assert intent.target == IntentTarget.WORLD
    
    def test_target_characters(self):
        """测试「生成人物角色」"""
        intent = parse_intent_by_rules("生成人物角色")
        assert intent.target == IntentTarget.CHARACTERS
    
    def test_target_outline(self):
        """测试「生成大纲」"""
        intent = parse_intent_by_rules("生成大纲")
        assert intent.target == IntentTarget.OUTLINE
    
    def test_target_chapter_plan(self):
        """测试「生成章节计划」"""
        intent = parse_intent_by_rules("生成章节计划")
        assert intent.target == IntentTarget.CHAPTER_PLAN
    
    def test_status_query(self):
        """测试状态查询"""
        intent = parse_intent_by_rules("查看进度")
        assert intent.target == IntentTarget.STATUS
    
    def test_help_query(self):
        """测试帮助查询"""
        intent = parse_intent_by_rules("帮助")
        assert intent.target == IntentTarget.HELP
    
    def test_chapter_plan_with_scope(self):
        """测试带范围的章节计划"""
        intent = parse_intent_by_rules("生成前3章的章节计划")
        assert intent.target == IntentTarget.CHAPTER_PLAN
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 1
        assert intent.chapter_scope.end == 3

    def test_export_single_chapter(self):
        """测试导出单章：导出小说第一章"""
        intent = parse_intent_by_rules("导出小说第一章")
        assert intent.target == IntentTarget.EXPORT
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 1
        assert intent.chapter_scope.end == 1
        assert not intent.needs_clarification()

    def test_export_all(self):
        """测试导出整本：导出小说"""
        intent = parse_intent_by_rules("导出小说")
        assert intent.target == IntentTarget.EXPORT
        assert intent.chapter_scope is None
        assert not intent.needs_clarification()
    
    def test_ambiguous_single_chapter(self):
        """测试歧义场景：生成第3章"""
        intent = parse_intent_by_rules("生成第3章")
        # 应识别为歧义（计划 vs 正文）
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 3
        assert intent.is_ambiguous or len(intent.clarification_questions) > 0
    
    def test_mode_plan(self):
        """测试模式识别：计划"""
        intent = parse_intent_by_rules("生成前3章的章节计划")
        assert intent.mode == IntentMode.PLAN
    
    def test_mode_text(self):
        """测试模式识别：正文"""
        intent = parse_intent_by_rules("生成章节正文")
        assert intent.mode == IntentMode.TEXT


class TestLLMIntentParsing:
    """测试 LLM 意图识别（使用 mock）"""
    
    @pytest.fixture
    def mock_llm_chain(self):
        """创建 mock LLM chain"""
        chain = Mock()
        return chain
    
    def test_llm_parse_chapter_plan_with_scope(self, mock_llm_chain):
        """测试 LLM 解析带范围的章节计划"""
        mock_llm_chain.invoke.return_value = LLMIntentOutput(
            target="chapter_plan",
            mode="plan",
            chapter_start=1,
            chapter_end=3,
            is_ambiguous=False,
            confidence=0.9
        )
        
        intent = parse_intent_by_llm("生成前3章的章节计划", mock_llm_chain)
        
        assert intent is not None
        assert intent.target == IntentTarget.CHAPTER_PLAN
        assert intent.mode == IntentMode.PLAN
        assert intent.chapter_scope.start == 1
        assert intent.chapter_scope.end == 3
        assert intent.confidence == 0.9
        assert intent.source == "llm"
    
    def test_llm_parse_ambiguous_input(self, mock_llm_chain):
        """测试 LLM 识别歧义输入"""
        mock_llm_chain.invoke.return_value = LLMIntentOutput(
            target="chapter_plan",
            mode="unspecified",
            chapter_start=3,
            chapter_end=3,
            is_ambiguous=True,
            ambiguity_reason="无法确定是生成章节计划还是章节正文",
            suggested_question="你想生成第3章的章节计划还是章节正文？",
            confidence=0.5
        )
        
        intent = parse_intent_by_llm("生成第3章", mock_llm_chain)
        
        assert intent is not None
        assert intent.is_ambiguous
        assert len(intent.clarification_questions) > 0
    
    def test_llm_failure_returns_none(self, mock_llm_chain):
        """测试 LLM 失败时返回 None"""
        mock_llm_chain.invoke.side_effect = Exception("API Error")
        
        intent = parse_intent_by_llm("生成大纲", mock_llm_chain)
        
        assert intent is None


class TestMergeIntents:
    """测试意图融合"""
    
    def test_prefer_rule_scope(self):
        """测试优先使用规则解析的范围"""
        llm_intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            mode=IntentMode.PLAN,
            chapter_scope=ChapterScope(start=1, end=5),  # LLM 解析错误
            confidence=0.8,
            original_input="生成前3章的章节计划",
            source="llm"
        )
        
        rule_intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            mode=IntentMode.PLAN,
            chapter_scope=ChapterScope(start=1, end=3),  # 规则解析正确
            confidence=1.0,
            original_input="生成前3章的章节计划",
            source="rule"
        )
        
        merged = _merge_intents(llm_intent, rule_intent)
        
        # 范围应使用规则的
        assert merged.chapter_scope.start == 1
        assert merged.chapter_scope.end == 3
        assert merged.source == "hybrid"
    
    def test_prefer_llm_target(self):
        """测试优先使用 LLM 的目标识别"""
        llm_intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            mode=IntentMode.PLAN,
            confidence=0.8,
            original_input="规划一下前三章",
            source="llm"
        )
        
        rule_intent = ParsedIntent(
            target=IntentTarget.UNKNOWN,  # 规则无法识别
            mode=IntentMode.UNSPECIFIED,
            confidence=0.3,
            original_input="规划一下前三章",
            source="rule"
        )
        
        merged = _merge_intents(llm_intent, rule_intent)
        
        # 目标应使用 LLM 的
        assert merged.target == IntentTarget.CHAPTER_PLAN
    
    def test_merge_ambiguity(self):
        """测试歧义标记合并"""
        llm_intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            is_ambiguous=True,
            clarification_questions=[ClarificationQuestion(
                question="Q1",
                options=[]
            )],
            original_input="test",
            source="llm"
        )
        
        rule_intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            is_ambiguous=False,
            clarification_questions=[],
            original_input="test",
            source="rule"
        )
        
        merged = _merge_intents(llm_intent, rule_intent)
        
        # 歧义应取并集
        assert merged.is_ambiguous
        assert len(merged.clarification_questions) == 1


class TestParseIntent:
    """测试混合解析"""
    
    def test_rule_only_mode(self):
        """测试仅规则模式"""
        intent = parse_intent("生成世界观", use_llm=False)
        
        assert intent.target == IntentTarget.WORLD
        assert intent.source == "rule"
    
    def test_llm_fallback_on_failure(self):
        """测试 LLM 失败时回退到规则"""
        with patch('novelgen.agent.intent_parser.parse_intent_by_llm', return_value=None):
            intent = parse_intent("生成大纲", use_llm=True)
            
            assert intent.target == IntentTarget.OUTLINE
            assert intent.source == "rule"


class TestParsedIntent:
    """测试 ParsedIntent 类"""
    
    def test_needs_clarification_ambiguous(self):
        """测试歧义时需要澄清"""
        intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            is_ambiguous=True,
            original_input="test"
        )
        assert intent.needs_clarification()
    
    def test_needs_clarification_questions(self):
        """测试有问题时需要澄清"""
        intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            clarification_questions=[ClarificationQuestion(
                question="test?",
                options=[]
            )],
            original_input="test"
        )
        assert intent.needs_clarification()
    
    def test_no_clarification_needed(self):
        """测试无需澄清"""
        intent = ParsedIntent(
            target=IntentTarget.WORLD,
            original_input="生成世界观"
        )
        assert not intent.needs_clarification()
    
    def test_echo_message(self):
        """测试回显消息生成"""
        intent = ParsedIntent(
            target=IntentTarget.CHAPTER_PLAN,
            mode=IntentMode.PLAN,
            chapter_scope=ChapterScope(start=1, end=3),
            original_input="生成前3章的章节计划"
        )
        
        echo = intent.get_echo_message()
        
        assert "章节计划" in echo
        assert "计划" in echo
        assert "第1-3章" in echo


class TestDialogRegressionCases:
    """对话回归测试用例
    
    覆盖 proposal 中的验收场景
    """
    
    def test_case_first_3_chapters_plan(self):
        """回归：生成前3章的章节计划"""
        intent = parse_intent_by_rules("生成前3章的章节计划")
        
        assert intent.target == IntentTarget.CHAPTER_PLAN
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 1
        assert intent.chapter_scope.end == 3
    
    def test_case_chapter_2_to_5(self):
        """回归：生成第2-5章的章节计划"""
        intent = parse_intent_by_rules("生成第2-5章的章节计划")
        
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 2
        assert intent.chapter_scope.end == 5
    
    def test_case_chapter_2_to_5_alternative(self):
        """回归：生成2到5章的章节计划"""
        intent = parse_intent_by_rules("生成2到5章的章节计划")
        
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 2
        assert intent.chapter_scope.end == 5
    
    def test_case_chinese_first_3_chapters(self):
        """回归：生成前三章的章节计划（中文数字）"""
        intent = parse_intent_by_rules("生成前三章的章节计划")
        
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 1
        assert intent.chapter_scope.end == 3
    
    def test_case_chinese_chapter_10(self):
        """回归：生成第十章（中文数字）"""
        intent = parse_intent_by_rules("生成第十章")
        
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 10
        assert intent.chapter_scope.end == 10
    
    def test_case_chinese_chapter_12_to_15(self):
        """回归：生成第十二章到第十五章（中文数字）"""
        intent = parse_intent_by_rules("生成第十二章到第十五章")
        
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 12
        assert intent.chapter_scope.end == 15
    
    def test_case_single_chapter_ambiguous(self):
        """回归：生成第3章（必须澄清）"""
        intent = parse_intent_by_rules("生成第3章")
        
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.start == 3
        # 应标记为歧义或有澄清问题
        assert intent.is_ambiguous or len(intent.clarification_questions) > 0
    
    def test_case_continue_to_chapter_5(self):
        """回归：继续生成到第5章"""
        intent = parse_intent_by_rules("继续生成到第5章")
        
        # 应识别到范围约束
        assert intent.chapter_scope is not None
        assert intent.chapter_scope.end == 5


@pytest.mark.skipif(not HAS_OPENAI_KEY, reason="需要 OPENAI_API_KEY 环境变量")
class TestRealLLMIntentParsing:
    """真实 LLM 意图识别测试
    
    这些测试会真实调用 LLM API，需要设置 OPENAI_API_KEY 环境变量。
    使用 pytest -m "not skipif" 或在有 API Key 的环境中运行。
    
    开发者: Jamesenh
    开发时间: 2025-12-16
    """
    
    @pytest.fixture(scope="class")
    def llm_chain(self):
        """创建真实 LLM 意图识别链（类级别复用）"""
        return create_llm_intent_chain()
    
    def test_real_llm_chapter_plan_with_scope(self, llm_chain):
        """真实 LLM 测试：生成前3章的章节计划"""
        intent = parse_intent_by_llm("生成前3章的章节计划", llm_chain)
        
        assert intent is not None, "LLM 意图识别返回 None"
        assert intent.source == "llm"
        
        # 验证目标识别
        assert intent.target in [IntentTarget.CHAPTER_PLAN, IntentTarget.FULL_WORKFLOW], \
            f"期望识别为章节计划，实际为 {intent.target}"
        
        # 验证范围识别
        if intent.chapter_scope:
            assert intent.chapter_scope.start == 1, f"期望起始章节为1，实际为 {intent.chapter_scope.start}"
            assert intent.chapter_scope.end == 3, f"期望结束章节为3，实际为 {intent.chapter_scope.end}"
        
        print(f"\n✅ LLM 识别结果: target={intent.target}, scope={intent.chapter_scope}, confidence={intent.confidence}")
    
    def test_real_llm_world_generation(self, llm_chain):
        """真实 LLM 测试：生成世界观"""
        intent = parse_intent_by_llm("生成世界观", llm_chain)
        
        assert intent is not None, "LLM 意图识别返回 None"
        assert intent.target == IntentTarget.WORLD, f"期望识别为世界观，实际为 {intent.target}"
        
        print(f"\n✅ LLM 识别结果: target={intent.target}, confidence={intent.confidence}")
    
    def test_real_llm_ambiguous_single_chapter(self, llm_chain):
        """真实 LLM 测试：歧义场景 - 生成第3章"""
        intent = parse_intent_by_llm("生成第3章", llm_chain)
        
        assert intent is not None, "LLM 意图识别返回 None"
        
        # 验证章节识别
        if intent.chapter_scope:
            assert intent.chapter_scope.start == 3, f"期望章节为3，实际为 {intent.chapter_scope.start}"
        
        # 歧义场景应该有较低置信度或标记为歧义
        print(f"\n✅ LLM 识别结果: target={intent.target}, is_ambiguous={intent.is_ambiguous}, confidence={intent.confidence}")
        if intent.clarification_questions:
            print(f"   澄清问题: {intent.clarification_questions[0].question}")
    
    def test_real_llm_chinese_numerals(self, llm_chain):
        """真实 LLM 测试：中文数字范围"""
        intent = parse_intent_by_llm("生成第十二章到第十五章的章节计划", llm_chain)
        
        assert intent is not None, "LLM 意图识别返回 None"
        
        # 验证中文数字解析
        if intent.chapter_scope:
            assert intent.chapter_scope.start == 12, f"期望起始章节为12，实际为 {intent.chapter_scope.start}"
            assert intent.chapter_scope.end == 15, f"期望结束章节为15，实际为 {intent.chapter_scope.end}"
        
        print(f"\n✅ LLM 识别结果: target={intent.target}, scope={intent.chapter_scope}")
    
    def test_real_llm_full_workflow(self, llm_chain):
        """真实 LLM 测试：全流程生成"""
        intent = parse_intent_by_llm("开始生成小说", llm_chain)
        
        assert intent is not None, "LLM 意图识别返回 None"
        assert intent.target == IntentTarget.FULL_WORKFLOW, f"期望识别为全流程，实际为 {intent.target}"
        
        print(f"\n✅ LLM 识别结果: target={intent.target}, confidence={intent.confidence}")
    
    def test_real_llm_status_query(self, llm_chain):
        """真实 LLM 测试：状态查询"""
        intent = parse_intent_by_llm("查看当前进度", llm_chain)
        
        assert intent is not None, "LLM 意图识别返回 None"
        assert intent.target == IntentTarget.STATUS, f"期望识别为状态查询，实际为 {intent.target}"
        
        print(f"\n✅ LLM 识别结果: target={intent.target}, confidence={intent.confidence}")
    
    def test_real_llm_vague_input(self, llm_chain):
        """真实 LLM 测试：模糊输入"""
        intent = parse_intent_by_llm("把后面几章规划一下", llm_chain)
        
        assert intent is not None, "LLM 意图识别返回 None"
        
        # 模糊输入应该标记为歧义或有澄清问题
        print(f"\n✅ LLM 识别结果: target={intent.target}, is_ambiguous={intent.is_ambiguous}")
        if intent.ambiguity_reason:
            print(f"   歧义原因: {intent.ambiguity_reason}")
        if intent.clarification_questions:
            print(f"   澄清问题: {intent.clarification_questions[0].question}")
    
    def test_real_llm_hybrid_parsing(self, llm_chain):
        """真实 LLM 测试：混合解析模式"""
        # 使用混合解析
        intent = parse_intent("生成前三章的章节计划", use_llm=True, llm_chain=llm_chain)
        
        assert intent is not None, "混合解析返回 None"
        assert intent.source in ["llm", "hybrid", "rule"], f"意外的解析来源: {intent.source}"
        
        # 验证范围（规则解析应该更准确）
        assert intent.chapter_scope is not None, "应该识别到章节范围"
        assert intent.chapter_scope.start == 1
        assert intent.chapter_scope.end == 3
        
        print(f"\n✅ 混合解析结果: source={intent.source}, target={intent.target}, scope={intent.chapter_scope}")
