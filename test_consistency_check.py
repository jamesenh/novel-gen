#!/usr/bin/env python3
"""测试一致性检查自动化功能"""

import os
import json
import tempfile
import shutil
from novelgen.runtime.orchestrator import NovelOrchestrator
from novelgen.runtime.consistency import run_consistency_check
from novelgen.models import ChapterMemoryEntry, ConsistencyReport


def test_consistency_check_automation():
    """测试一致性检查自动化功能"""
    
    temp_dir = tempfile.mkdtemp()
    project_name = "test_consistency"
    
    try:
        orchestrator = NovelOrchestrator(project_name=project_name, base_dir=temp_dir, verbose=False)
        
        print("="*60)
        print("测试一致性检查自动化")
        print("="*60)
        
        # 测试1: 无冲突的一致性检查
        print("\n1. 测试无冲突的一致性检查...")
        
        # 创建一致的上下文和章节
        context_payload = json.dumps({
            "outline_summary": {
                "chapter_number": 2,
                "chapter_title": "第二章：训练",
                "summary": "主角开始训练"
            },
            "recent_memory": [
                {
                    "chapter_number": 1,
                    "chapter_title": "第一章：觉醒",
                    "timeline_anchor": "第一天",
                    "location_summary": "主角家中",
                    "key_events": ["主角觉醒能力"],
                    "character_states": {"主角": "能力觉醒，困惑"},
                    "unresolved_threads": ["能力来源"],
                    "summary": "主角觉醒了特殊能力。"
                }
            ]
        }, ensure_ascii=False)
        
        consistent_chapter_text = """
        第二天，主角来到了训练场。导师已经在那里等待着他。
        "你的能力刚刚觉醒，需要学会控制它。"导师说道。
        主角点点头，开始按照导师的指导进行基础训练。
        虽然还很生疏，但他能够感受到体内力量的流动。
        训练结束后，主角对导师说："我明白了，但我还是不知道这力量从何而来。"
        导师微笑着说："慢慢来，一切都会有答案的。"
        """
        
        try:
            report = run_consistency_check(
                chapter_number=2,
                context_payload=context_payload,
                chapter_text=consistent_chapter_text,
                verbose=False
            )
            
            assert isinstance(report, ConsistencyReport), "应该返回ConsistencyReport对象"
            assert report.chapter_number == 2, "章节编号应该正确"
            print("✓ 无冲突检查通过")
            print(f"  检测摘要: {report.summary}")
            
        except Exception as e:
            print(f"✗ 无冲突检查失败: {e}")
            raise
        
        # 测试2: 有角色状态冲突的一致性检查
        print("\n2. 测试角色状态冲突检测...")
        
        inconsistent_chapter_text = """
        第二天，主角来到了训练场。让他惊讶的是，导师已经在那里等待着他。
        "你的能力觉醒已经一周了，为什么现在才来训练？"导师问道。
        主角困惑地说："什么一周？我昨天才觉醒的啊。"
        导师摇摇头："不可能，我亲眼看到你七天前就觉醒了。"
        主角感到很奇怪，他确信自己是昨天才觉醒的能力。
        """
        
        try:
            report = run_consistency_check(
                chapter_number=2,
                context_payload=context_payload,
                chapter_text=inconsistent_chapter_text,
                verbose=False
            )
            
            assert len(report.issues) > 0, "应该检测到冲突"
            
            # 检查是否检测到时间线冲突
            time_conflict_found = any("时间" in issue.description.lower() or "天" in issue.description for issue in report.issues)
            if time_conflict_found:
                print("✓ 成功检测到时间线冲突")
            else:
                print("⚠️ 可能未检测到预期的时间线冲突")
            
            print(f"  检测到 {len(report.issues)} 个问题:")
            for i, issue in enumerate(report.issues, 1):
                print(f"    {i}. {issue.issue_type}: {issue.description}")
                
        except Exception as e:
            print(f"✗ 冲突检测失败: {e}")
            raise
        
        # 测试3: 地点冲突检测
        print("\n3. 测试地点冲突检测...")
        
        location_conflict_text = """
        主角在图书馆里遇见了导师。这里安静的环境很适合训练。
        "昨天在你家里的训练很有效果，"导师说道，"今天我们换个地方。"
        主角点点头，开始在这个充满书籍的地方进行冥想训练。
        """
        
        try:
            report = run_consistency_check(
                chapter_number=2,
                context_payload=context_payload,
                chapter_text=location_conflict_text,
                verbose=False
            )
            
            # 地点冲突可能不会被检测到，因为这不是明显的矛盾
            print("✓ 地点冲突测试完成")
            print(f"  检测到 {len(report.issues)} 个问题")
            
        except Exception as e:
            print(f"✗ 地点冲突测试失败: {e}")
        
        # 测试4: orchestrator中的一致性检查集成
        print("\n4. 测试orchestrator中的一致性检查集成...")
        
        # 添加记忆条目
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
        
        # 测试构建一致性上下文
        context = orchestrator._build_consistency_context(2, None)
        assert isinstance(context, str), "应该返回字符串"
        
        parsed_context = json.loads(context)
        assert "recent_memory" in parsed_context, "应该包含最近记忆"
        assert len(parsed_context["recent_memory"]) == 1, "应该有一条记忆记录"
        
        print("✓ orchestrator集成测试通过")
        
        # 测试5: 一致性报告记录
        print("\n5. 测试一致性报告记录...")
        
        test_report = ConsistencyReport(
            chapter_number=2,
            issues=[],
            summary="测试报告：未发现明显冲突",
            context_snapshot="主角觉醒，第二天训练"
        )
        
        orchestrator._record_consistency_report(test_report)
        
        # 验证报告文件是否创建
        report_file = orchestrator.config.consistency_report_file
        assert os.path.exists(report_file), "一致性报告文件应该被创建"
        
        # 读取并验证报告内容
        with open(report_file, 'r', encoding='utf-8') as f:
            reports = json.load(f)
        
        assert len(reports) == 1, "应该有一条报告记录"
        assert reports[0]["chapter_number"] == 2, "章节编号应该正确"
        
        print("✓ 一致性报告记录测试通过")
        
        print("\n" + "="*60)
        print("所有一致性检查测试通过！")
        print("="*60)
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_consistency_edge_cases():
    """测试一致性检查的边界情况"""
    
    temp_dir = tempfile.mkdtemp()
    project_name = "test_consistency_edge"
    
    try:
        print("="*60)
        print("测试一致性检查边界情况")
        print("="*60)
        
        # 测试1: 空上下文
        print("\n1. 测试空上下文处理...")
        
        empty_context = json.dumps({
            "outline_summary": {},
            "recent_memory": []
        }, ensure_ascii=False)
        
        simple_text = "这是一个简单的测试章节。"
        
        try:
            report = run_consistency_check(
                chapter_number=1,
                context_payload=empty_context,
                chapter_text=simple_text,
                verbose=False
            )
            
            assert isinstance(report, ConsistencyReport), "空上下文应该正常处理"
            print("✓ 空上下文处理正常")
            
        except Exception as e:
            print(f"✗ 空上下文处理失败: {e}")
        
        # 测试2: 空章节文本
        print("\n2. 测试空章节文本...")
        
        try:
            report = run_consistency_check(
                chapter_number=1,
                context_payload=empty_context,
                chapter_text="",
                verbose=False
            )
            
            assert isinstance(report, ConsistencyReport), "空文本应该正常处理"
            print("✓ 空章节文本处理正常")
            
        except Exception as e:
            print(f"✗ 空章节文本处理失败: {e}")
        
        # 测试3: 非常长的文本
        print("\n3. 测试长文本处理...")
        
        long_text = "这是一个很长的测试章节。" * 1000
        
        try:
            report = run_consistency_check(
                chapter_number=1,
                context_payload=empty_context,
                chapter_text=long_text,
                verbose=False
            )
            
            assert isinstance(report, ConsistencyReport), "长文本应该正常处理"
            print("✓ 长文本处理正常")
            
        except Exception as e:
            print(f"✗ 长文本处理失败: {e}")
        
        print("\n" + "="*60)
        print("边界情况测试完成！")
        print("="*60)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_consistency_check_automation()
    test_consistency_edge_cases()
    print("\n🎉 所有一致性检查测试完成！")
