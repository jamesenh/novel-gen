"""
测试 memory_chunks 表的集成测试
验证场景内容同时保存到向量库和数据库
"""
import os
import tempfile
import shutil
from pathlib import Path

# 设置环境变量启用持久化
os.environ['NOVELGEN_PERSISTENCE_ENABLED'] = 'true'
os.environ['NOVELGEN_VECTOR_STORE_ENABLED'] = 'true'

from novelgen.runtime.orchestrator import NovelOrchestrator


def test_memory_chunks_persistence():
    """测试 memory_chunks 表是否正确写入"""
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="novelgen_test_")
    print(f"\n📁 测试目录: {temp_dir}")
    
    try:
        # 创建orchestrator
        orchestrator = NovelOrchestrator(
            project_name="test_memory_chunks",
            base_dir=temp_dir,
            verbose=False
        )
        
        # 执行基本生成流程
        print("\n🚀 开始生成流程...")
        orchestrator.step1_create_world("一个测试世界观", force=True)
        orchestrator.step2_create_theme_conflict("测试主题", force=True)
        orchestrator.step3_create_characters(force=True)
        orchestrator.step4_create_outline(num_chapters=1, force=True)
        orchestrator.step5_create_chapter_plan(1, force=True)
        orchestrator.step6_generate_chapter_text(1, force=True)
        
        # 检查数据库中的 memory_chunks 表
        if orchestrator.db_manager and orchestrator.db_manager.is_enabled():
            print("\n🔍 检查数据库 memory_chunks 表...")
            
            with orchestrator.db_manager.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM memory_chunks WHERE project_id = ?",
                    ("test_memory_chunks",)
                )
                count = cursor.fetchone()[0]
                print(f"✅ 找到 {count} 条记忆块记录")
                
                if count > 0:
                    # 查看详细信息
                    cursor = conn.execute(
                        """SELECT chunk_id, chapter_index, scene_index, 
                           substr(content, 1, 50) as content_preview,
                           content_type, embedding_id 
                           FROM memory_chunks 
                           WHERE project_id = ? 
                           LIMIT 3""",
                        ("test_memory_chunks",)
                    )
                    
                    print("\n📋 前3条记录预览：")
                    for row in cursor.fetchall():
                        print(f"  - 章节{row[1]} 场景{row[2]}: {row[3]}...")
                        print(f"    类型: {row[4]}, 向量ID: {row[5][:40]}..." if row[5] else "    类型: {row[4]}, 无向量ID")
                    
                    print(f"\n✅ memory_chunks 表写入成功！共 {count} 条记录")
                else:
                    print("\n❌ memory_chunks 表为空，持久化失败！")
                    return False
        else:
            print("\n⚠️ 数据库未启用")
            return False
        
        # 检查向量库
        if orchestrator.vector_manager and orchestrator.vector_manager.is_enabled():
            print("\n🔍 检查向量库...")
            chunks = orchestrator.vector_manager.get_chunks_by_project(
                "test_memory_chunks", chapter_index=1
            )
            print(f"✅ 向量库中找到 {len(chunks)} 个记忆块")
        
        orchestrator.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\n🧹 已清理测试目录")


if __name__ == "__main__":
    success = test_memory_chunks_persistence()
    exit(0 if success else 1)
