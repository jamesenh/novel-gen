"""
对话式 Agent 目标型生成测试
测试 ng chat 的目标型生成功能，包括意图识别、依赖检查、确认流程等

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

# 导入被测试模块
from novelgen.agent.chat import (
    ChatAgent, IntentType, TargetedGenerationPlan,
    TARGET_KEYWORDS_TO_NODE, NODE_DEPENDENCIES, NODE_DISPLAY_NAMES,
    FULL_WORKFLOW_KEYWORDS
)
from novelgen.tools.registry import ToolResult


class TestIntentClassification:
    """测试意图分类"""
    
    @pytest.fixture
    def mock_agent(self):
        """创建 mock agent（不需要真实项目目录）"""
        with patch.object(ChatAgent, '__init__', lambda x, *args, **kwargs: None):
            agent = ChatAgent.__new__(ChatAgent)
            agent.project_dir = "/fake/project/dir"
            agent.project_id = "test_project"
            agent.registry = Mock()
            agent.conversation_history = []
            agent.pending_plan = None
            return agent
    
    def test_full_workflow_intent_start(self, mock_agent):
        """测试「开始生成」识别为全流程意图"""
        intent = mock_agent._classify_intent("开始生成")
        assert intent == IntentType.GENERATE_FULL
    
    def test_full_workflow_intent_continue(self, mock_agent):
        """测试「继续生成」识别为全流程意图"""
        intent = mock_agent._classify_intent("继续生成")
        assert intent == IntentType.GENERATE_FULL
    
    def test_full_workflow_intent_onekey(self, mock_agent):
        """测试「一键生成」识别为全流程意图"""
        intent = mock_agent._classify_intent("一键生成")
        assert intent == IntentType.GENERATE_FULL
    
    def test_target_intent_world(self, mock_agent):
        """测试「生成世界观」识别为目标型生成"""
        intent = mock_agent._classify_intent("生成世界观")
        assert intent == IntentType.GENERATE_TARGET
    
    def test_target_intent_characters(self, mock_agent):
        """测试「生成人物角色」识别为目标型生成"""
        intent = mock_agent._classify_intent("生成人物角色")
        assert intent == IntentType.GENERATE_TARGET
    
    def test_target_intent_outline(self, mock_agent):
        """测试「生成大纲」识别为目标型生成"""
        intent = mock_agent._classify_intent("生成大纲")
        assert intent == IntentType.GENERATE_TARGET
    
    def test_target_intent_theme_conflict(self, mock_agent):
        """测试「生成主题冲突」识别为目标型生成"""
        intent = mock_agent._classify_intent("生成主题冲突")
        assert intent == IntentType.GENERATE_TARGET
    
    def test_status_intent(self, mock_agent):
        """测试状态查询意图"""
        intent = mock_agent._classify_intent("查看进度")
        assert intent == IntentType.STATUS
    
    def test_help_intent(self, mock_agent):
        """测试帮助意图"""
        intent = mock_agent._classify_intent("帮助")
        assert intent == IntentType.HELP


class TestTargetExtraction:
    """测试目标提取"""
    
    @pytest.fixture
    def mock_agent(self):
        """创建 mock agent"""
        with patch.object(ChatAgent, '__init__', lambda x, *args, **kwargs: None):
            agent = ChatAgent.__new__(ChatAgent)
            return agent
    
    def test_extract_world(self, mock_agent):
        """测试提取世界观目标"""
        target = mock_agent._extract_target_from_input("生成世界观")
        assert target == "world_creation"
    
    def test_extract_characters(self, mock_agent):
        """测试提取人物角色目标"""
        target = mock_agent._extract_target_from_input("生成人物角色")
        assert target == "character_creation"
    
    def test_extract_outline(self, mock_agent):
        """测试提取大纲目标"""
        target = mock_agent._extract_target_from_input("我想生成大纲")
        assert target == "outline_creation"
    
    def test_extract_theme_conflict(self, mock_agent):
        """测试提取主题冲突目标"""
        target = mock_agent._extract_target_from_input("帮我生成主题冲突")
        assert target == "theme_conflict_creation"
    
    def test_extract_chapter_planning(self, mock_agent):
        """测试提取章节计划目标"""
        target = mock_agent._extract_target_from_input("生成章节计划")
        assert target == "chapter_planning"
    
    def test_extract_no_target(self, mock_agent):
        """测试无目标关键词时返回 None"""
        target = mock_agent._extract_target_from_input("继续生成")
        assert target is None
    
    def test_extract_longer_keyword_priority(self, mock_agent):
        """测试优先匹配更长的关键词（人物角色 vs 人物）"""
        # "人物角色" 应优先于 "人物" 匹配
        target = mock_agent._extract_target_from_input("生成人物角色")
        assert target == "character_creation"


class TestDependencyChecking:
    """测试依赖检查"""
    
    @pytest.fixture
    def mock_agent(self):
        """创建 mock agent"""
        with patch.object(ChatAgent, '__init__', lambda x, *args, **kwargs: None):
            agent = ChatAgent.__new__(ChatAgent)
            return agent
    
    def test_world_no_dependencies(self, mock_agent):
        """测试世界观无前置依赖"""
        missing = mock_agent._get_missing_dependencies("world_creation", [])
        assert missing == []
    
    def test_theme_conflict_missing_world(self, mock_agent):
        """测试主题冲突缺少世界观前置"""
        missing = mock_agent._get_missing_dependencies("theme_conflict_creation", [])
        assert missing == ["world_creation"]
    
    def test_theme_conflict_world_completed(self, mock_agent):
        """测试主题冲突前置已满足"""
        missing = mock_agent._get_missing_dependencies(
            "theme_conflict_creation", 
            ["world_creation"]
        )
        assert missing == []
    
    def test_character_missing_all(self, mock_agent):
        """测试角色生成缺少所有前置"""
        missing = mock_agent._get_missing_dependencies("character_creation", [])
        assert missing == ["world_creation", "theme_conflict_creation"]
    
    def test_character_partial_deps(self, mock_agent):
        """测试角色生成部分前置已满足"""
        missing = mock_agent._get_missing_dependencies(
            "character_creation",
            ["world_creation"]
        )
        assert missing == ["theme_conflict_creation"]
    
    def test_outline_all_deps_met(self, mock_agent):
        """测试大纲生成所有前置已满足"""
        missing = mock_agent._get_missing_dependencies(
            "outline_creation",
            ["world_creation", "theme_conflict_creation", "character_creation"]
        )
        assert missing == []


class TestTargetedGenerationFlow:
    """测试目标型生成流程"""
    
    @pytest.fixture
    def mock_agent(self):
        """创建 mock agent with mocked registry"""
        with patch.object(ChatAgent, '__init__', lambda x, *args, **kwargs: None):
            agent = ChatAgent.__new__(ChatAgent)
            agent.project_dir = "/fake/project/dir"
            agent.project_id = "test_project"
            agent.registry = Mock()
            agent.conversation_history = []
            agent.pending_plan = None
            return agent
    
    def test_target_generation_with_missing_deps(self, mock_agent):
        """测试目标型生成显示缺失前置确认"""
        # Mock status 返回：无已完成步骤
        mock_agent.registry.create_plan.return_value = Mock(requires_confirmation=False)
        mock_agent.registry.execute_plan.return_value = ToolResult(
            tool_name="workflow.status",
            success=True,
            data={"completed_steps": []}
        )
        
        # 调用目标型生成
        response = mock_agent._handle_generate_target_intent("生成人物角色")
        
        # 验证返回的确认消息
        assert "目标型生成计划" in response
        assert "人物角色" in response
        assert "缺失前置步骤" in response
        assert "世界观" in response
        assert "主题冲突" in response
        assert "/yes" in response
        
        # 验证 pending_plan 已设置
        assert isinstance(mock_agent.pending_plan, TargetedGenerationPlan)
        assert mock_agent.pending_plan.target_node == "character_creation"
        assert "world_creation" in mock_agent.pending_plan.missing_deps
    
    def test_target_generation_deps_satisfied(self, mock_agent):
        """测试目标型生成前置已满足"""
        # Mock status 返回：世界观和主题冲突已完成
        mock_agent.registry.create_plan.return_value = Mock(requires_confirmation=False)
        mock_agent.registry.execute_plan.return_value = ToolResult(
            tool_name="workflow.status",
            success=True,
            data={"completed_steps": ["world_creation", "theme_conflict_creation"]}
        )
        
        # 调用目标型生成
        response = mock_agent._handle_generate_target_intent("生成人物角色")
        
        # 验证返回的确认消息（无缺失前置）
        assert "目标型生成计划" in response
        assert "人物角色" in response
        assert "所有前置步骤已完成" in response
        assert "/yes" in response
        
        # 验证 pending_plan
        assert isinstance(mock_agent.pending_plan, TargetedGenerationPlan)
        assert mock_agent.pending_plan.missing_deps == []
    
    def test_target_already_exists(self, mock_agent):
        """测试目标产物已存在"""
        # Mock status 返回：角色已生成
        mock_agent.registry.create_plan.return_value = Mock(requires_confirmation=False)
        mock_agent.registry.execute_plan.return_value = ToolResult(
            tool_name="workflow.status",
            success=True,
            data={"completed_steps": [
                "world_creation", 
                "theme_conflict_creation", 
                "character_creation"
            ]}
        )
        
        # 调用目标型生成
        response = mock_agent._handle_generate_target_intent("生成人物角色")
        
        # 验证返回已存在提示
        assert "已存在" in response
        assert "rollback" in response
        
        # 验证没有设置 pending_plan
        assert mock_agent.pending_plan is None


class TestConfirmationFlow:
    """测试确认流程"""
    
    @pytest.fixture
    def mock_agent(self):
        """创建 mock agent"""
        with patch.object(ChatAgent, '__init__', lambda x, *args, **kwargs: None):
            agent = ChatAgent.__new__(ChatAgent)
            agent.project_dir = "/fake/project/dir"
            agent.project_id = "test_project"
            agent.registry = Mock()
            agent.conversation_history = []
            agent.pending_plan = None
            return agent
    
    def test_confirm_targeted_generation(self, mock_agent):
        """测试确认目标型生成执行"""
        # 设置待确认的目标型生成计划
        mock_agent.pending_plan = TargetedGenerationPlan(
            target_node="character_creation",
            missing_deps=["world_creation", "theme_conflict_creation"]
        )
        
        # Mock workflow 执行成功
        mock_agent.registry.create_plan.return_value = Mock(requires_confirmation=False)
        mock_agent.registry.execute_plan.return_value = ToolResult(
            tool_name="workflow.run",
            success=True,
            message="工作流执行完成"
        )
        
        # 确认执行
        response = mock_agent._confirm_pending_plan()
        
        # 验证执行成功
        assert "生成完成" in response
        assert mock_agent.pending_plan is None
        
        # 验证调用了 workflow.run 并带有 stop_at 参数
        mock_agent.registry.create_plan.assert_called_with(
            "workflow.run",
            {"stop_at": "character_creation"}
        )
    
    def test_cancel_targeted_generation_with_suggestions(self, mock_agent):
        """测试取消目标型生成提供替代建议"""
        # 设置待确认的目标型生成计划（有缺失依赖）
        mock_agent.pending_plan = TargetedGenerationPlan(
            target_node="character_creation",
            missing_deps=["world_creation", "theme_conflict_creation"]
        )
        
        # 取消执行
        response = mock_agent._cancel_pending_plan()
        
        # 验证返回替代建议
        assert "已取消" in response
        assert "替代建议" in response
        assert "世界观" in response
        assert mock_agent.pending_plan is None


class TestNodeDependencies:
    """测试节点依赖定义"""
    
    def test_world_creation_no_deps(self):
        """世界观无依赖"""
        assert NODE_DEPENDENCIES["world_creation"] == []
    
    def test_theme_conflict_deps(self):
        """主题冲突依赖世界观"""
        assert NODE_DEPENDENCIES["theme_conflict_creation"] == ["world_creation"]
    
    def test_character_deps(self):
        """角色依赖世界观和主题冲突"""
        assert NODE_DEPENDENCIES["character_creation"] == [
            "world_creation", 
            "theme_conflict_creation"
        ]
    
    def test_outline_deps(self):
        """大纲依赖世界观、主题冲突、角色"""
        assert NODE_DEPENDENCIES["outline_creation"] == [
            "world_creation",
            "theme_conflict_creation",
            "character_creation"
        ]
    
    def test_chapter_planning_deps(self):
        """章节计划依赖所有前置"""
        assert NODE_DEPENDENCIES["chapter_planning"] == [
            "world_creation",
            "theme_conflict_creation",
            "character_creation",
            "outline_creation"
        ]


class TestKeywordMapping:
    """测试关键词映射"""
    
    def test_world_keywords(self):
        """世界观相关关键词"""
        for kw in ["世界观", "世界", "世界设定", "背景", "背景设定"]:
            assert TARGET_KEYWORDS_TO_NODE[kw] == "world_creation"
    
    def test_character_keywords(self):
        """角色相关关键词"""
        for kw in ["人物", "角色", "人物角色", "角色设定", "人物设定", "主角", "配角"]:
            assert TARGET_KEYWORDS_TO_NODE[kw] == "character_creation"
    
    def test_outline_keywords(self):
        """大纲相关关键词"""
        for kw in ["大纲", "故事大纲", "剧情大纲", "章节大纲"]:
            assert TARGET_KEYWORDS_TO_NODE[kw] == "outline_creation"


class TestDisplayNames:
    """测试显示名称"""
    
    def test_all_nodes_have_display_names(self):
        """所有节点都有显示名称"""
        for node in NODE_DEPENDENCIES.keys():
            assert node in NODE_DISPLAY_NAMES
