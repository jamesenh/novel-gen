"""
细粒度工具回归测试
测试 add-chat-fine-grained-tooling 变更的核心契约：
1. 范围不会扩张 - 请求第 2-5 章只处理 2-5 章
2. missing_only 只补缺 - 已存在的不覆盖
3. force 会覆盖 - 显式指定时覆盖已存在内容
4. sequential 阻断跳章 - 跳章生成会被阻断

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-16
"""
import os
import json
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from novelgen.tools.registry import ToolResult
from novelgen.tools.chapter_tools import create_chapter_tools
from novelgen.tools.outline_tools import create_outline_tools
from novelgen.tools.project_tools import create_project_tools
from novelgen.tools.settings_tools import create_settings_tools
from novelgen.models import (
    WorldSetting, ThemeConflict, CharactersConfig, Character,
    Outline, ChapterSummary, ChapterPlan, ScenePlan,
    GeneratedChapter, GeneratedScene
)


class TestFixtures:
    """测试夹具工厂"""
    
    @staticmethod
    def create_world() -> WorldSetting:
        """创建测试用世界观"""
        return WorldSetting(
            world_name="测试世界",
            time_period="现代",
            geography="中原大陆",
            social_system="封建王朝",
            technology_level="古代冷兵器时代",
            culture_customs="尊师重道",
            power_system="内功修炼",
            special_rules="天赋决定上限"
        )
    
    @staticmethod
    def create_theme() -> ThemeConflict:
        """创建测试用主题"""
        return ThemeConflict(
            core_theme="成长",
            sub_themes=["友情", "信任"],
            main_conflict="自我超越",
            sub_conflicts=["家族恩怨", "门派纷争"],
            tone="热血励志"
        )
    
    @staticmethod
    def create_characters() -> CharactersConfig:
        """创建测试用角色"""
        return CharactersConfig(
            protagonist=Character(
                name="主角",
                role="protagonist",
                gender="男",
                appearance="身材修长，目光坚定",
                personality="勇敢坚韧",
                background="普通农家子弟",
                motivation="保护家人"
            ),
            antagonist=None,
            supporting_characters=[]
        )
    
    @staticmethod
    def create_outline(num_chapters: int = 5) -> Outline:
        """创建测试用大纲"""
        chapters = []
        for i in range(1, num_chapters + 1):
            chapters.append(ChapterSummary(
                chapter_number=i,
                chapter_title=f"第{i}章标题",
                summary=f"第{i}章摘要",
                key_events=[f"事件{i}"]
            ))
        return Outline(
            story_premise="测试故事前提",
            beginning="故事开端",
            development="故事发展",
            climax="故事高潮",
            resolution="故事结局",
            chapters=chapters,
            is_complete=True,
            current_phase="complete"
        )
    
    @staticmethod
    def create_chapter_plan(chapter_num: int) -> ChapterPlan:
        """创建测试用章节计划"""
        return ChapterPlan(
            chapter_number=chapter_num,
            chapter_title=f"第{chapter_num}章标题",
            scenes=[
                ScenePlan(
                    scene_number=1,
                    location="地点A",
                    characters=["主角"],
                    purpose="推进剧情",
                    key_actions=["动作1", "动作2"],
                    estimated_words=500,
                    scene_type="发展",
                    intensity="中"
                )
            ]
        )
    
    @staticmethod
    def create_chapter_text(chapter_num: int) -> GeneratedChapter:
        """创建测试用章节正文"""
        return GeneratedChapter(
            chapter_number=chapter_num,
            chapter_title=f"第{chapter_num}章标题",
            scenes=[
                GeneratedScene(
                    scene_number=1,
                    content=f"第{chapter_num}章的测试内容...",
                    word_count=100
                )
            ],
            total_words=100
        )


@pytest.fixture
def temp_project_dir():
    """创建临时项目目录"""
    temp_dir = tempfile.mkdtemp()
    project_id = "test_project"
    project_dir = os.path.join(temp_dir, project_id)
    os.makedirs(project_dir)
    
    yield project_dir, project_id
    
    # 清理
    shutil.rmtree(temp_dir)


@pytest.fixture
def project_with_prereqs(temp_project_dir):
    """创建带有前置条件的项目（世界观、角色、大纲）"""
    project_dir, project_id = temp_project_dir
    
    # 保存世界观
    world = TestFixtures.create_world()
    with open(os.path.join(project_dir, "world.json"), 'w', encoding='utf-8') as f:
        json.dump(world.model_dump(), f, ensure_ascii=False)
    
    # 保存主题
    theme = TestFixtures.create_theme()
    with open(os.path.join(project_dir, "theme.json"), 'w', encoding='utf-8') as f:
        json.dump(theme.model_dump(), f, ensure_ascii=False)
    
    # 保存角色
    characters = TestFixtures.create_characters()
    with open(os.path.join(project_dir, "characters.json"), 'w', encoding='utf-8') as f:
        json.dump(characters.model_dump(), f, ensure_ascii=False)
    
    # 保存大纲（5章）
    outline = TestFixtures.create_outline(5)
    with open(os.path.join(project_dir, "outline.json"), 'w', encoding='utf-8') as f:
        json.dump(outline.model_dump(), f, ensure_ascii=False)
    
    # 创建 chapters 目录
    chapters_dir = os.path.join(project_dir, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)
    
    return project_dir, project_id


class TestScopeNoExpansion:
    """测试范围不会扩张
    
    核心契约：请求生成第 2-5 章，只会处理 2-5 章，不会自动扩展到 1-5 章
    """
    
    def test_chapter_plan_scope_exact(self, project_with_prereqs):
        """测试章节计划生成范围精确"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        tools = create_chapter_tools(project_dir, project_id)
        plan_tool = next(t for t in tools if t.name == "chapter.plan.generate")
        
        # Mock LLM 调用
        mock_plan = TestFixtures.create_chapter_plan(2)
        with patch('novelgen.chains.chapters_plan_chain.generate_chapter_plan', return_value=mock_plan):
            # 只请求第 2-3 章
            result = plan_tool.handler(
                chapter_scope_start=2,
                chapter_scope_end=3,
                force=True,
                missing_only=False
            )
        
        assert result.success
        generated = result.data.get("generated", [])
        
        # 验证只生成了 2-3 章，没有扩展到第 1 章
        assert 2 in generated
        assert 3 in generated
        assert 1 not in generated
        assert 4 not in generated
        
        # 验证文件系统
        assert not os.path.exists(os.path.join(chapters_dir, "chapter_001_plan.json"))
        assert os.path.exists(os.path.join(chapters_dir, "chapter_002_plan.json"))
        assert os.path.exists(os.path.join(chapters_dir, "chapter_003_plan.json"))
        assert not os.path.exists(os.path.join(chapters_dir, "chapter_004_plan.json"))
    
    def test_chapter_text_scope_exact(self, project_with_prereqs):
        """测试章节正文生成范围精确"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 先创建所有章节计划（1-5章）
        for i in range(1, 6):
            plan = TestFixtures.create_chapter_plan(i)
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}_plan.json"), 'w', encoding='utf-8') as f:
                json.dump(plan.model_dump(), f, ensure_ascii=False)
        
        # 创建第 1 章正文（模拟已完成）
        ch1 = TestFixtures.create_chapter_text(1)
        with open(os.path.join(chapters_dir, "chapter_001.json"), 'w', encoding='utf-8') as f:
            json.dump(ch1.model_dump(), f, ensure_ascii=False)
        
        tools = create_chapter_tools(project_dir, project_id)
        text_tool = next(t for t in tools if t.name == "chapter.text.generate")
        
        # Mock 场景生成
        def mock_scene(*args, **kwargs):
            return GeneratedScene(scene_number=1, content="测试内容", word_count=100)
        
        with patch('novelgen.chains.scene_text_chain.generate_scene_text', side_effect=mock_scene):
            # 请求第 2-3 章（第 1 章已存在）
            result = text_tool.handler(
                chapter_scope_start=2,
                chapter_scope_end=3,
                force=False,
                missing_only=True,
                sequential=True
            )
        
        assert result.success
        generated = result.data.get("generated", [])
        
        # 验证只生成了 2-3 章
        assert 2 in generated
        assert 3 in generated
        assert 1 not in generated  # 第 1 章不应被触碰
        assert 4 not in generated


class TestMissingOnlySemantics:
    """测试 missing_only 语义
    
    核心契约：missing_only=True 时，只生成不存在的章节，已存在的不覆盖
    """
    
    def test_plan_missing_only_skips_existing(self, project_with_prereqs):
        """测试章节计划 missing_only 跳过已存在"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建第 2 章计划（已存在）
        existing_plan = TestFixtures.create_chapter_plan(2)
        existing_plan.chapter_title = "原始标题"
        with open(os.path.join(chapters_dir, "chapter_002_plan.json"), 'w', encoding='utf-8') as f:
            json.dump(existing_plan.model_dump(), f, ensure_ascii=False)
        
        tools = create_chapter_tools(project_dir, project_id)
        plan_tool = next(t for t in tools if t.name == "chapter.plan.generate")
        
        new_plan = TestFixtures.create_chapter_plan(1)
        new_plan.chapter_title = "新生成的标题"
        
        with patch('novelgen.chains.chapters_plan_chain.generate_chapter_plan', return_value=new_plan):
            # 请求 1-3 章，missing_only=True
            result = plan_tool.handler(
                chapter_scope_start=1,
                chapter_scope_end=3,
                force=False,
                missing_only=True
            )
        
        assert result.success
        generated = result.data.get("generated", [])
        skipped = result.data.get("skipped", [])
        
        # 验证第 2 章被跳过
        assert 2 in skipped
        assert 2 not in generated
        
        # 验证第 1、3 章被生成
        assert 1 in generated
        assert 3 in generated
        
        # 验证第 2 章内容未被覆盖
        with open(os.path.join(chapters_dir, "chapter_002_plan.json"), 'r', encoding='utf-8') as f:
            saved_plan = json.load(f)
        assert saved_plan["chapter_title"] == "原始标题"
    
    def test_text_missing_only_skips_existing(self, project_with_prereqs):
        """测试章节正文 missing_only 跳过已存在"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建章节计划 1-3
        for i in range(1, 4):
            plan = TestFixtures.create_chapter_plan(i)
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}_plan.json"), 'w', encoding='utf-8') as f:
                json.dump(plan.model_dump(), f, ensure_ascii=False)
        
        # 创建第 1、2 章正文（已存在）
        for i in range(1, 3):
            ch = TestFixtures.create_chapter_text(i)
            ch.chapter_title = f"原始第{i}章"
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}.json"), 'w', encoding='utf-8') as f:
                json.dump(ch.model_dump(), f, ensure_ascii=False)
        
        tools = create_chapter_tools(project_dir, project_id)
        text_tool = next(t for t in tools if t.name == "chapter.text.generate")
        
        def mock_scene(*args, **kwargs):
            return GeneratedScene(scene_number=1, content="新内容", word_count=100)
        
        with patch('novelgen.chains.scene_text_chain.generate_scene_text', side_effect=mock_scene):
            # 请求 1-3 章，missing_only=True
            result = text_tool.handler(
                chapter_scope_start=1,
                chapter_scope_end=3,
                force=False,
                missing_only=True,
                sequential=True
            )
        
        assert result.success
        generated = result.data.get("generated", [])
        skipped = result.data.get("skipped", [])
        
        # 验证 1、2 章被跳过
        assert 1 in skipped
        assert 2 in skipped
        
        # 验证第 3 章被生成
        assert 3 in generated
        
        # 验证 1、2 章内容未被覆盖
        with open(os.path.join(chapters_dir, "chapter_001.json"), 'r', encoding='utf-8') as f:
            ch1 = json.load(f)
        assert ch1["chapter_title"] == "原始第1章"


class TestForceSemantics:
    """测试 force 语义
    
    核心契约：force=True 时，覆盖已存在的内容
    """
    
    def test_plan_force_overwrites_existing(self, project_with_prereqs):
        """测试章节计划 force 覆盖已存在"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建第 1 章计划（已存在，原始内容）
        existing_plan = TestFixtures.create_chapter_plan(1)
        existing_plan.chapter_title = "原始标题"
        with open(os.path.join(chapters_dir, "chapter_001_plan.json"), 'w', encoding='utf-8') as f:
            json.dump(existing_plan.model_dump(), f, ensure_ascii=False)
        
        tools = create_chapter_tools(project_dir, project_id)
        plan_tool = next(t for t in tools if t.name == "chapter.plan.generate")
        
        new_plan = TestFixtures.create_chapter_plan(1)
        new_plan.chapter_title = "强制覆盖的新标题"
        
        with patch('novelgen.chains.chapters_plan_chain.generate_chapter_plan', return_value=new_plan):
            # 请求第 1 章，force=True
            result = plan_tool.handler(
                chapter_scope_start=1,
                chapter_scope_end=1,
                force=True,
                missing_only=False
            )
        
        assert result.success
        generated = result.data.get("generated", [])
        
        # 验证第 1 章被生成（覆盖）
        assert 1 in generated
        
        # 验证内容被覆盖
        with open(os.path.join(chapters_dir, "chapter_001_plan.json"), 'r', encoding='utf-8') as f:
            saved_plan = json.load(f)
        assert saved_plan["chapter_title"] == "强制覆盖的新标题"
    
    def test_text_force_overwrites_existing(self, project_with_prereqs):
        """测试章节正文 force 覆盖已存在"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建第 1 章计划和正文
        plan = TestFixtures.create_chapter_plan(1)
        with open(os.path.join(chapters_dir, "chapter_001_plan.json"), 'w', encoding='utf-8') as f:
            json.dump(plan.model_dump(), f, ensure_ascii=False)
        
        existing_ch = TestFixtures.create_chapter_text(1)
        existing_ch.chapter_title = "原始第1章"
        with open(os.path.join(chapters_dir, "chapter_001.json"), 'w', encoding='utf-8') as f:
            json.dump(existing_ch.model_dump(), f, ensure_ascii=False)
        
        tools = create_chapter_tools(project_dir, project_id)
        text_tool = next(t for t in tools if t.name == "chapter.text.generate")
        
        def mock_scene(*args, **kwargs):
            return GeneratedScene(scene_number=1, content="强制覆盖的新内容", word_count=200)
        
        with patch('novelgen.chains.scene_text_chain.generate_scene_text', side_effect=mock_scene):
            # 请求第 1 章，force=True
            result = text_tool.handler(
                chapter_scope_start=1,
                chapter_scope_end=1,
                force=True,
                missing_only=False,
                sequential=True
            )
        
        assert result.success
        generated = result.data.get("generated", [])
        
        # 验证第 1 章被覆盖
        assert 1 in generated
        
        # 验证内容被覆盖
        with open(os.path.join(chapters_dir, "chapter_001.json"), 'r', encoding='utf-8') as f:
            saved_ch = json.load(f)
        assert saved_ch["scenes"][0]["content"] == "强制覆盖的新内容"


class TestSequentialConstraint:
    """测试 sequential 顺序约束
    
    核心契约：sequential=True 时，如果前面章节缺失，阻止跳章生成
    """
    
    def test_text_sequential_blocks_skipping(self, project_with_prereqs):
        """测试章节正文顺序约束阻止跳章"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建章节计划 1-5
        for i in range(1, 6):
            plan = TestFixtures.create_chapter_plan(i)
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}_plan.json"), 'w', encoding='utf-8') as f:
                json.dump(plan.model_dump(), f, ensure_ascii=False)
        
        # 注意：没有创建任何章节正文，即第 1 章缺失
        
        tools = create_chapter_tools(project_dir, project_id)
        text_tool = next(t for t in tools if t.name == "chapter.text.generate")
        
        # 尝试生成第 3 章（跳过 1、2）
        result = text_tool.handler(
            chapter_scope_start=3,
            chapter_scope_end=3,
            force=False,
            missing_only=True,
            sequential=True  # 启用顺序约束
        )
        
        # 应该失败，因为前面章节缺失
        assert not result.success
        assert "顺序约束" in result.error or "blocked_by_missing" in str(result.data)
        
        # 验证返回了阻塞信息
        blocked = result.data.get("blocked_by_missing", [])
        assert 1 in blocked
        assert 2 in blocked
    
    def test_text_sequential_allows_next(self, project_with_prereqs):
        """测试章节正文顺序约束允许紧接着的章节"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建章节计划 1-3
        for i in range(1, 4):
            plan = TestFixtures.create_chapter_plan(i)
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}_plan.json"), 'w', encoding='utf-8') as f:
                json.dump(plan.model_dump(), f, ensure_ascii=False)
        
        # 创建第 1、2 章正文
        for i in range(1, 3):
            ch = TestFixtures.create_chapter_text(i)
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}.json"), 'w', encoding='utf-8') as f:
                json.dump(ch.model_dump(), f, ensure_ascii=False)
        
        tools = create_chapter_tools(project_dir, project_id)
        text_tool = next(t for t in tools if t.name == "chapter.text.generate")
        
        def mock_scene(*args, **kwargs):
            return GeneratedScene(scene_number=1, content="第3章内容", word_count=100)
        
        with patch('novelgen.chains.scene_text_chain.generate_scene_text', side_effect=mock_scene):
            # 生成第 3 章（前面都完成了）
            result = text_tool.handler(
                chapter_scope_start=3,
                chapter_scope_end=3,
                force=False,
                missing_only=True,
                sequential=True
            )
        
        # 应该成功
        assert result.success
        generated = result.data.get("generated", [])
        assert 3 in generated
    
    def test_text_sequential_false_allows_skipping(self, project_with_prereqs):
        """测试 sequential=False 允许跳章"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建章节计划 1-5
        for i in range(1, 6):
            plan = TestFixtures.create_chapter_plan(i)
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}_plan.json"), 'w', encoding='utf-8') as f:
                json.dump(plan.model_dump(), f, ensure_ascii=False)
        
        # 没有任何章节正文
        
        tools = create_chapter_tools(project_dir, project_id)
        text_tool = next(t for t in tools if t.name == "chapter.text.generate")
        
        def mock_scene(*args, **kwargs):
            return GeneratedScene(scene_number=1, content="第3章内容", word_count=100)
        
        with patch('novelgen.chains.scene_text_chain.generate_scene_text', side_effect=mock_scene):
            # 生成第 3 章，sequential=False
            result = text_tool.handler(
                chapter_scope_start=3,
                chapter_scope_end=3,
                force=False,
                missing_only=True,
                sequential=False  # 禁用顺序约束
            )
        
        # 应该成功（允许跳章）
        assert result.success
        generated = result.data.get("generated", [])
        assert 3 in generated


class TestDependencyValidation:
    """测试前置依赖验证"""
    
    def test_plan_requires_outline(self, temp_project_dir):
        """测试章节计划需要大纲"""
        project_dir, project_id = temp_project_dir
        
        # 不创建任何前置文件
        tools = create_chapter_tools(project_dir, project_id)
        plan_tool = next(t for t in tools if t.name == "chapter.plan.generate")
        
        result = plan_tool.handler(
            chapter_scope_start=1,
            chapter_scope_end=1,
            force=False,
            missing_only=True
        )
        
        assert not result.success
        assert "大纲" in result.error or "outline" in str(result.data)
    
    def test_text_requires_plan(self, project_with_prereqs):
        """测试章节正文需要章节计划"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 不创建任何章节计划
        
        tools = create_chapter_tools(project_dir, project_id)
        text_tool = next(t for t in tools if t.name == "chapter.text.generate")
        
        result = text_tool.handler(
            chapter_scope_start=1,
            chapter_scope_end=1,
            force=False,
            missing_only=True,
            sequential=True
        )
        
        assert not result.success
        assert "计划" in result.error or "missing_plans" in str(result.data)


class TestProjectTools:
    """测试项目工具"""
    
    def test_project_status(self, project_with_prereqs):
        """测试项目状态"""
        project_dir, project_id = project_with_prereqs
        
        tools = create_project_tools(project_dir, project_id)
        status_tool = next(t for t in tools if t.name == "project.status")
        
        result = status_tool.handler(detail=False)
        
        assert result.success
        # 检查步骤状态结构
        assert "steps" in result.data
        assert result.data["steps"]["world"]["exists"] == True  # 世界观存在
        assert result.data["steps"]["outline"]["exists"] == True  # 大纲存在
    
    def test_validate_prereqs_chapter_plan(self, project_with_prereqs):
        """测试章节计划前置验证"""
        project_dir, project_id = project_with_prereqs
        
        # 创建 theme_conflict.json（project_with_prereqs 没有创建）
        theme = TestFixtures.create_theme()
        with open(os.path.join(project_dir, "theme_conflict.json"), 'w', encoding='utf-8') as f:
            json.dump(theme.model_dump(), f, ensure_ascii=False)
        
        tools = create_project_tools(project_dir, project_id)
        validate_tool = next(t for t in tools if t.name == "project.validate_prereqs")
        
        result = validate_tool.handler(target="chapter_plan")
        
        assert result.success
        # 检查实际返回结构
        assert result.data["satisfied"] == True  # 前置都满足
    
    def test_list_artifacts(self, project_with_prereqs):
        """测试列出产物"""
        project_dir, project_id = project_with_prereqs
        chapters_dir = os.path.join(project_dir, "chapters")
        
        # 创建一些章节计划
        for i in range(1, 3):
            plan = TestFixtures.create_chapter_plan(i)
            with open(os.path.join(chapters_dir, f"chapter_{i:03d}_plan.json"), 'w', encoding='utf-8') as f:
                json.dump(plan.model_dump(), f, ensure_ascii=False)
        
        tools = create_project_tools(project_dir, project_id)
        list_tool = next(t for t in tools if t.name == "project.list_artifacts")
        
        result = list_tool.handler(kind="plan")
        
        assert result.success
        # 检查实际返回结构 - plan_chapters 是章节编号列表
        plan_chapters = result.data.get("plan_chapters", [])
        assert 1 in plan_chapters
        assert 2 in plan_chapters


class TestSettingsTools:
    """测试设置工具"""
    
    def test_settings_get_and_update(self, project_with_prereqs):
        """测试获取和更新设置"""
        project_dir, project_id = project_with_prereqs
        
        # 创建符合 Settings 模型的初始设置
        settings = {
            "project_name": project_id,
            "author": "Jamesenh",
            "world_description": "测试世界观描述",
            "initial_chapters": 5,
            "max_chapters": 10
        }
        with open(os.path.join(project_dir, "settings.json"), 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False)
        
        tools = create_settings_tools(project_dir, project_id)
        get_tool = next(t for t in tools if t.name == "settings.get")
        update_tool = next(t for t in tools if t.name == "settings.update")
        
        # 获取设置
        result = get_tool.handler()
        assert result.success
        assert result.data["initial_chapters"] == 5
        
        # 更新设置
        result = update_tool.handler(patch={"initial_chapters": 8}, persist=True)
        assert result.success
        
        # 验证更新
        result = get_tool.handler()
        assert result.data["initial_chapters"] == 8


class TestOutlineTools:
    """测试大纲工具"""
    
    def test_outline_generate_requires_prereqs(self, temp_project_dir):
        """测试大纲生成需要前置"""
        project_dir, project_id = temp_project_dir
        
        tools = create_outline_tools(project_dir, project_id)
        gen_tool = next(t for t in tools if t.name == "outline.generate")
        
        result = gen_tool.handler(num_chapters=5, force=False)
        
        assert not result.success
        assert "world" in str(result.data).lower() or "世界" in result.error
    
    def test_outline_extend(self, project_with_prereqs):
        """测试大纲扩展"""
        project_dir, project_id = project_with_prereqs
        
        # 更新大纲为未完成状态
        outline_file = os.path.join(project_dir, "outline.json")
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
        outline_data["is_complete"] = False
        outline_data["current_phase"] = "development"
        with open(outline_file, 'w', encoding='utf-8') as f:
            json.dump(outline_data, f, ensure_ascii=False)
        
        # 创建 theme_conflict（outline.extend 需要）
        theme = TestFixtures.create_theme()
        with open(os.path.join(project_dir, "theme_conflict.json"), 'w', encoding='utf-8') as f:
            json.dump(theme.model_dump(), f, ensure_ascii=False)
        
        tools = create_outline_tools(project_dir, project_id)
        extend_tool = next(t for t in tools if t.name == "outline.extend")
        
        # 创建扩展后的大纲（6章）
        extended_outline = TestFixtures.create_outline(6)
        
        with patch('novelgen.chains.outline_chain.extend_outline', return_value=extended_outline):
            result = extend_tool.handler(additional_chapters=1, force=False)
        
        assert result.success
        assert result.data["total_count"] == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
