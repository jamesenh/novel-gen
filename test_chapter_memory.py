#!/usr/bin/env python3
"""测试章节记忆基础设施功能"""

import os
import json
import tempfile
import shutil
from novelgen.runtime.orchestrator import NovelOrchestrator
from novelgen.models import ChapterMemoryEntry, GeneratedChapter, GeneratedScene, ChapterSummary


def test_chapter_memory_infrastructure():
    """测试章节记忆基础设施的完整流程"""
    
    # 创建临时项目目录
    temp_dir = tempfile.mkdtemp()
    project_name = "test_memory"
    
    try:
        # 创建编排器实例
        orchestrator = NovelOrchestrator(project_name=project_name, base_dir=temp_dir, verbose=False)
        
        print("="*60)
        print("测试章节记忆基础设施")
        print("="*60)
        
        # 测试1: 记忆文件不存在时返回空列表
        print("\n1. 测试记忆文件不存在时的行为...")
        entries = orchestrator._load_chapter_memory_entries()
        assert entries == [], "记忆文件不存在时应返回空列表"
        print("✓ 通过")
        
        # 测试2: 追加记忆条目
        print("\n2. 测试追加记忆条目...")
        memory_entry = ChapterMemoryEntry(
            chapter_number=1,
            chapter_title="第一章：开始",
            timeline_anchor="第一天",
            location_summary="主角家中",
            key_events=["主角觉醒", "收到神秘信件"],
            character_states={"主角": "能力觉醒，充满困惑"},
            unresolved_threads=["神秘信件的来源"],
            summary="主角在平凡的一天中突然觉醒特殊能力，并收到一封改变命运的信件。"
        )
        
        orchestrator._append_chapter_memory_entry(memory_entry)
        entries = orchestrator._load_chapter_memory_entries()
        assert len(entries) == 1, "应该有一条记忆记录"
        assert entries[0].chapter_number == 1, "章节编号应该正确"
        print("✓ 通过")
        
        # 测试3: 更新记忆条目
        print("\n3. 测试更新记忆条目...")
        updated_entry = ChapterMemoryEntry(
            chapter_number=1,
            chapter_title="第一章：觉醒之日",
            timeline_anchor="第一天",
            location_summary="主角家中",
            key_events=["主角觉醒", "收到神秘信件", "遇见导师"],
            character_states={"主角": "能力觉醒，开始训练"},
            unresolved_threads=["神秘信件的来源", "导师的真实身份"],
            summary="主角觉醒能力后，在导师指导下开始了解新的世界。"
        )
        
        orchestrator._append_chapter_memory_entry(updated_entry)
        entries = orchestrator._load_chapter_memory_entries()
        assert len(entries) == 1, "应该仍然只有一条记录"
        assert entries[0].chapter_title == "第一章：觉醒之日", "标题应该更新"
        assert len(entries[0].key_events) == 3, "关键事件应该更新"
        print("✓ 通过")
        
        # 测试4: 获取最近记忆
        print("\n4. 测试获取最近记忆...")
        # 添加第二章记忆
        memory_entry_2 = ChapterMemoryEntry(
            chapter_number=2,
            chapter_title="第二章：训练",
            timeline_anchor="第三天",
            location_summary="训练场",
            key_events=["基础训练", "第一次实战"],
            character_states={"主角": "掌握基础技能"},
            unresolved_threads=["导师的真实身份"],
            summary="主角开始系统性的能力训练。"
        )
        
        orchestrator._append_chapter_memory_entry(memory_entry_2)
        
        # 测试获取第3章之前的记忆（应该返回第1、2章）
        recent_memories = orchestrator._get_recent_chapter_memory(chapter_number=3)
        assert len(recent_memories) == 2, "应该返回两条记忆记录"
        assert recent_memories[0].chapter_number == 1, "应该按章节顺序排列"
        assert recent_memories[1].chapter_number == 2, "应该按章节顺序排列"
        
        # 测试限制数量
        recent_memories_limited = orchestrator._get_recent_chapter_memory(chapter_number=3, limit=1)
        assert len(recent_memories_limited) == 1, "限制数量应该生效"
        assert recent_memories_limited[0].chapter_number == 2, "应该返回最近的章节"
        print("✓ 通过")
        
        # 测试5: 记忆格式化
        print("\n5. 测试记忆格式化...")
        formatted = orchestrator._format_memory_entries(recent_memories)
        assert isinstance(formatted, str), "应该返回字符串"
        assert "第一章" in formatted, "应该包含第一章信息"
        assert "第二章" in formatted, "应该包含第二章信息"
        
        # 验证JSON格式正确
        parsed = json.loads(formatted)
        assert len(parsed) == 2, "JSON应该包含两条记录"
        print("✓ 通过")
        
        # 测试6: 上下文载荷构建
        print("\n6. 测试上下文载荷构建...")
        context_payload = orchestrator._build_chapter_context_payload(3)
        assert isinstance(context_payload, str), "应该返回字符串"
        parsed_context = json.loads(context_payload)
        assert len(parsed_context) == 2, "应该包含两条记忆记录"
        print("✓ 通过")
        
        # 测试7: 分阶段依赖验证 - 逻辑有效性
        print("\n7. 测试分阶段依赖验证...")
        from novelgen.models import ChapterDependency
        
        # 创建有效依赖的章节摘要
        valid_summary = ChapterSummary(
            chapter_number=3,
            chapter_title="第三章",
            summary="测试章节",
            key_events=[],
            dependencies=[
                ChapterDependency(
                    dependency_type="事件",
                    description="第一章完成",
                    chapter_number=1
                )
            ]
        )
        
        # 应该通过逻辑验证（不依赖未来章节）
        try:
            orchestrator._ensure_chapter_dependencies_met(valid_summary)
            print("✓ 逻辑有效性验证通过")
        except Exception as e:
            raise AssertionError(f"有效依赖应该通过验证: {e}")
        
        # 创建无效依赖（依赖未来章节）
        invalid_summary = ChapterSummary(
            chapter_number=2,
            chapter_title="第二章",
            summary="测试章节",
            key_events=[],
            dependencies=[
                ChapterDependency(
                    dependency_type="事件",
                    description="第三章完成",
                    chapter_number=3
                )
            ]
        )
        
        # 应该失败逻辑验证
        try:
            orchestrator._ensure_chapter_dependencies_met(invalid_summary)
            raise AssertionError("依赖未来章节应该验证失败")
        except ValueError as e:
            assert "未来章节" in str(e), "应该明确指出未来章节错误"
            print("✓ 未来章节依赖验证正确失败")
        
        print("\n" + "="*60)
        print("所有测试通过！章节记忆基础设施功能正常。")
        print("="*60)
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_memory_injection_to_generation():
    """测试记忆数据注入到章节计划生成步骤"""
    
    temp_dir = tempfile.mkdtemp()
    project_name = "test_memory_injection"
    
    try:
        orchestrator = NovelOrchestrator(project_name=project_name, base_dir=temp_dir, verbose=False)
        
        print("="*60)
        print("测试记忆数据注入到生成步骤")
        print("="*60)
        
        # 预先添加记忆数据
        memory_entry = ChapterMemoryEntry(
            chapter_number=1,
            chapter_title="第一章：觉醒",
            timeline_anchor="第一天",
            location_summary="主角家中",
            key_events=["主角觉醒能力"],
            character_states={"主角": "能力觉醒，困惑"},
            unresolved_threads=["能力来源"],
            summary="主角觉醒了特殊能力。"
        )
        
        orchestrator._append_chapter_memory_entry(memory_entry)
        
        # 测试构建第二章的上下文载荷
        context_payload = orchestrator._build_chapter_context_payload(2)
        parsed_context = json.loads(context_payload)
        
        assert len(parsed_context) == 1, "应该包含第一章的记忆"
        assert parsed_context[0]["chapter_number"] == 1, "应该是第一章的记忆"
        assert "觉醒" in parsed_context[0]["chapter_title"], "应该包含正确的标题"
        
        print("✓ 记忆数据正确注入到生成步骤")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_chapter_memory_infrastructure()
    test_memory_injection_to_generation()
    print("\n🎉 所有记忆基础设施测试完成！")
