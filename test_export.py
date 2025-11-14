"""
测试导出功能
"""
from main import export_chapter_cmd, export_novel_cmd

print("=" * 60)
print("测试1: 导出单个章节")
print("=" * 60)
export_chapter_cmd("test_world_chain", 1)

print("\n" + "=" * 60)
print("测试2: 导出全书")
print("=" * 60)
export_novel_cmd("test_world_chain")

print("\n✅ 测试完成！")

