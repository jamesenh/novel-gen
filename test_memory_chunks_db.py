"""
测试 memory_chunks 数据库写入功能
不依赖LLM，直接测试数据库层
"""
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from novelgen.runtime.db import DatabaseManager
from novelgen.runtime.vector_store import VectorStoreManager
from novelgen.models import StoryMemoryChunk


def test_memory_chunks_db_write():
    """测试记忆块写入数据库"""
    
    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix="test_db_"))
    db_path = temp_dir / "test.db"
    vector_dir = temp_dir / "vectors"
    
    print(f"\n📁 测试目录: {temp_dir}")
    
    try:
        # 1. 初始化数据库
        db_manager = DatabaseManager(db_path, enabled=True)
        print("✅ 数据库初始化成功")
        
        # 2. 初始化向量存储
        vector_manager = VectorStoreManager(vector_dir, enabled=True)
        print("✅ 向量存储初始化成功")
        
        # 3. 模拟场景内容
        scene_content = "这是第一章第一场景的内容。" * 30  # 确保会被分块
        
        # 4. 使用向量管理器添加场景内容（会返回StoryMemoryChunk对象）
        chunks = vector_manager.add_scene_content(
            content=scene_content,
            project_id="test_project",
            chapter_index=1,
            scene_index=1
        )
        
        print(f"\n📦 向量存储创建了 {len(chunks)} 个记忆块")
        
        # 5. 同时保存到数据库
        if chunks:
            for chunk in chunks:
                result = db_manager.save_memory_chunk(chunk)
                if not result:
                    print(f"❌ 保存记忆块失败: {chunk.chunk_id}")
                    return False
            
            print(f"✅ 已将 {len(chunks)} 个记忆块保存到数据库")
        
        # 6. 验证数据库中的数据
        print("\n🔍 验证数据库记录...")
        with db_manager.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM memory_chunks WHERE project_id = ?",
                ("test_project",)
            )
            count = cursor.fetchone()[0]
            
            if count != len(chunks):
                print(f"❌ 数据库记录数不匹配: 期望 {len(chunks)}，实际 {count}")
                return False
            
            print(f"✅ 数据库记录数正确: {count}")
            
            # 查看详细记录
            cursor = conn.execute(
                """SELECT chunk_id, chapter_index, scene_index, 
                   substr(content, 1, 50) as preview,
                   content_type, embedding_id
                   FROM memory_chunks 
                   WHERE project_id = ?""",
                ("test_project",)
            )
            
            print("\n📋 数据库记录详情：")
            for row in cursor.fetchall():
                print(f"  - Chunk ID: {row[0][:20]}...")
                print(f"    章节: {row[1]}, 场景: {row[2]}")
                print(f"    内容预览: {row[3]}...")
                print(f"    类型: {row[4]}")
                print(f"    向量ID: {row[5][:40] if row[5] else 'None'}...")
                print()
        
        # 7. 使用数据库接口读取记忆块
        retrieved_chunks = db_manager.get_memory_chunks("test_project", chapter_index=1)
        print(f"✅ 通过接口读取到 {len(retrieved_chunks)} 个记忆块")
        
        if len(retrieved_chunks) != len(chunks):
            print(f"❌ 读取数量不匹配")
            return False
        
        # 验证读取的数据正确性
        for chunk in retrieved_chunks:
            assert chunk.project_id == "test_project"
            assert chunk.chapter_index == 1
            assert chunk.scene_index == 1
            assert chunk.content_type == "scene"
            print(f"  ✓ {chunk.chunk_id[:20]}... 验证通过")
        
        print("\n✅ 所有测试通过！memory_chunks 表工作正常")
        
        # 清理
        db_manager.close()
        vector_manager.close()
        
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
    success = test_memory_chunks_db_write()
    exit(0 if success else 1)
