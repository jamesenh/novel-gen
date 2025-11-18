#!/usr/bin/env python3
"""测试 step6 章节文本生成的 force 复用/重算语义"""

import os
import json
from datetime import datetime

import novelgen.runtime.orchestrator as orchestrator_module
from novelgen.runtime.orchestrator import NovelOrchestrator
from novelgen.models import (
    WorldSetting,
    CharactersConfig,
    Character,
    Outline,
    ChapterSummary,
    ChapterPlan,
    ScenePlan,
    GeneratedScene,
    ChapterMemoryEntry,
    ConsistencyReport,
    SceneMemoryContext,
)


CALL_COUNTS = {
    "scene": 0,
    "memory": 0,
    "consistency": 0,
}

LAST_SCENE_MEMORY_CONTEXT = None


def _bootstrap_minimal_project(orchestrator: NovelOrchestrator, chapter_number: int = 1):
    """构造最小可运行的项目状态，避免真实调用 LLM"""
    # world.json
    world = WorldSetting(
        world_name="测试世界",
        time_period="近未来",
        geography="一座城市",
        social_system="联邦制",
        power_system=None,
        technology_level="高科技",
        culture_customs="多元文化",
        special_rules=None,
    )
    orchestrator.save_json(world, orchestrator.config.world_file)

    # characters.json
    protagonist = Character(
        name="测试主角",
        role="主角",
        age=18,
        gender="未知",
        appearance="普通外貌",
        personality="坚定",
        background="普通学生",
        motivation="探索世界",
        abilities=None,
        relationships=None,
    )
    characters = CharactersConfig(
        protagonist=protagonist,
        antagonist=None,
        supporting_characters=[],
    )
    orchestrator.save_json(characters, orchestrator.config.characters_file)

    # outline.json，包含一个章节摘要
    chapter_summary = ChapterSummary(
        chapter_number=chapter_number,
        chapter_title="测试章节一",
        summary="这是一个用于测试的章节摘要",
        key_events=["事件1"],
        timeline_anchor=None,
        dependencies=[],
    )
    outline = Outline(
        story_premise="测试前提",
        beginning="测试开端",
        development="测试发展",
        climax="测试高潮",
        resolution="测试结局",
        chapters=[chapter_summary],
    )
    orchestrator.save_json(outline, orchestrator.config.outline_file)

    # chapter_XXX_plan.json
    scene_plan = ScenePlan(
        scene_number=1,
        location="测试地点",
        characters=["测试主角"],
        purpose="测试目的",
        key_actions=["测试动作"],
        estimated_words=200,
        scene_type="日常",
        intensity="低",
        developer_name="Jamesenh",
        developer_date="2025-11-15",
    )
    chapter_plan = ChapterPlan(
        chapter_number=chapter_number,
        chapter_title=chapter_summary.chapter_title,
        scenes=[scene_plan],
    )
    plan_file = os.path.join(
        orchestrator.config.chapters_dir,
        f"chapter_{chapter_number:03d}_plan.json",
    )
    orchestrator.save_json(chapter_plan, plan_file)


def _install_stubs():
    """为 orchestrator 中用到的外部链安装桩，避免真实 LLM 调用"""

    def fake_generate_scene_text(
        scene_plan: ScenePlan,
        world_setting: WorldSetting,
        characters: CharactersConfig,
        previous_summary: str = "",
        chapter_context: str = "",
        scene_memory_context=None,
        verbose: bool = False,
        llm_config=None,
    ) -> GeneratedScene:
        global LAST_SCENE_MEMORY_CONTEXT
        CALL_COUNTS["scene"] += 1
        LAST_SCENE_MEMORY_CONTEXT = scene_memory_context
        return GeneratedScene(
            scene_number=scene_plan.scene_number,
            content=f"fake scene content #{CALL_COUNTS['scene']}",
            word_count=100,
        )

    def fake_summarize_scene(scene: GeneratedScene) -> str:
        return f"摘要: {scene.content[:20]}"

    def fake_summarize_scenes(scenes):
        return "; ".join([s.content[:10] for s in scenes])

    def fake_generate_chapter_memory_entry(
        chapter,
        outline_summary,
        scene_summaries,
        aggregated_summary,
        verbose: bool = False,
        llm_config=None,
    ) -> ChapterMemoryEntry:
        CALL_COUNTS["memory"] += 1
        return ChapterMemoryEntry(
            chapter_number=chapter.chapter_number,
            chapter_title=chapter.chapter_title,
            timeline_anchor=None,
            location_summary=None,
            key_events=["测试事件"],
            character_states={},
            unresolved_threads=[],
            summary=aggregated_summary,
        )

    def fake_run_consistency_check(
        chapter_number: int,
        context_payload: str,
        chapter_text: str,
        verbose: bool = False,
        llm_config=None,
    ) -> ConsistencyReport:
        CALL_COUNTS["consistency"] += 1
        return ConsistencyReport(
            chapter_number=chapter_number,
            issues=[],
            summary="一致性良好",
            context_snapshot="",
        )

    orchestrator_module.generate_scene_text = fake_generate_scene_text
    orchestrator_module.summarize_scene = fake_summarize_scene
    orchestrator_module.summarize_scenes = fake_summarize_scenes
    orchestrator_module.generate_chapter_memory_entry = fake_generate_chapter_memory_entry
    orchestrator_module.run_consistency_check = fake_run_consistency_check


def test_step6_force_reuse_and_regeneration():
    """验证 step6 在 force=False/True 下的复用与重算行为"""
    _install_stubs()

    project_name = "test_step6_force"
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
    _bootstrap_minimal_project(orchestrator, chapter_number=1)

    chapter_file = os.path.join(
        orchestrator.config.chapters_dir,
        "chapter_001.json",
    )
    if os.path.exists(chapter_file):
        os.remove(chapter_file)

    # 第一次生成（force=False）：应调用场景生成链
    CALL_COUNTS["scene"] = 0
    CALL_COUNTS["memory"] = 0
    CALL_COUNTS["consistency"] = 0
    chapter_first = orchestrator.step6_generate_chapter_text(chapter_number=1, force=False)
    assert chapter_first.chapter_number == 1
    assert CALL_COUNTS["scene"] > 0
    assert os.path.exists(chapter_file)

    scene_calls_after_first = CALL_COUNTS["scene"]

    # 第二次调用（force=False）：应复用已生成章节，不再调用场景生成链
    chapter_second = orchestrator.step6_generate_chapter_text(chapter_number=1, force=False)
    assert chapter_second.chapter_number == 1
    assert CALL_COUNTS["scene"] == scene_calls_after_first

    # 第三次调用（force=True）：应重新生成章节文本，场景调用次数增加
    chapter_third = orchestrator.step6_generate_chapter_text(chapter_number=1, force=True)
    assert chapter_third.chapter_number == 1
    assert CALL_COUNTS["scene"] > scene_calls_after_first


def test_generate_all_chapters_force_semantics():
    """验证 generate_all_chapters 在 force 语义下的复用与重算行为"""
    _install_stubs()

    project_name = "test_generate_all_force"
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
    _bootstrap_minimal_project(orchestrator, chapter_number=1)

    chapter_file = os.path.join(
        orchestrator.config.chapters_dir,
        "chapter_001.json",
    )
    if os.path.exists(chapter_file):
        os.remove(chapter_file)

    # 第一次批量生成（force=False）：应真正生成一次章节文本
    CALL_COUNTS["scene"] = 0
    CALL_COUNTS["memory"] = 0
    CALL_COUNTS["consistency"] = 0
    orchestrator.generate_all_chapters(force=False)
    first_scene_calls = CALL_COUNTS["scene"]
    assert first_scene_calls > 0
    assert os.path.exists(chapter_file)

    # 第二次批量生成（force=False）：应复用已生成章节文本，不再增加场景生成次数
    orchestrator.generate_all_chapters(force=False)
    assert CALL_COUNTS["scene"] == first_scene_calls

    # 第三次批量生成（force=True）：应为现有章节重新生成文本，场景次数增加
    orchestrator.generate_all_chapters(force=True)
    assert CALL_COUNTS["scene"] > first_scene_calls


def test_step6_without_scene_memory_context_passes_none():
    """当不存在场景记忆文件时，应以 None 作为 scene_memory_context 调用链"""
    _install_stubs()

    project_name = "test_step6_no_memory"
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
    _bootstrap_minimal_project(orchestrator, chapter_number=1)

    global LAST_SCENE_MEMORY_CONTEXT
    LAST_SCENE_MEMORY_CONTEXT = "sentinel"

    memory_file = os.path.join(
        orchestrator.project_dir,
        "scene_1_1_memory.json",
    )
    if os.path.exists(memory_file):
        os.remove(memory_file)

    orchestrator.step6_generate_chapter_text(chapter_number=1, force=True)

    assert LAST_SCENE_MEMORY_CONTEXT is None


def test_step6_with_scene_memory_context_loads_and_passes_object():
    """当存在场景记忆文件时，应加载为 SceneMemoryContext 并传递给链"""
    _install_stubs()

    project_name = "test_step6_with_memory"
    orchestrator = NovelOrchestrator(project_name=project_name, verbose=False)
    _bootstrap_minimal_project(orchestrator, chapter_number=1)

    global LAST_SCENE_MEMORY_CONTEXT
    LAST_SCENE_MEMORY_CONTEXT = None

    memory_file = os.path.join(
        orchestrator.project_dir,
        "scene_1_1_memory.json",
    )
    payload = {
        "project_id": project_name,
        "chapter_index": 1,
        "scene_index": 1,
        "entity_states": [],
        "relevant_memories": [],
        "timeline_context": None,
        "retrieval_timestamp": datetime.now().isoformat(),
    }
    with open(memory_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    orchestrator.step6_generate_chapter_text(chapter_number=1, force=True)

    assert isinstance(LAST_SCENE_MEMORY_CONTEXT, SceneMemoryContext)
    assert LAST_SCENE_MEMORY_CONTEXT.chapter_index == 1
    assert LAST_SCENE_MEMORY_CONTEXT.scene_index == 1


if __name__ == "__main__":
    test_step6_force_reuse_and_regeneration()
    test_generate_all_chapters_force_semantics()
