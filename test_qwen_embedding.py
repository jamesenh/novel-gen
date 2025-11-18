#!/usr/bin/env python3
"""
测试 Qwen Embedding 模型
"""
import tempfile
from pathlib import Path

from novelgen.config import EmbeddingConfig
from novelgen.runtime.vector_store import VectorStoreManager


def test_qwen_embedding():
    """测试 Qwen embedding 模型"""
    print("=" * 70)
    print("测试 Qwen/Qwen3-Embedding-8B 模型")
    print("=" * 70)
    
    # 创建配置
    embedding_config = EmbeddingConfig()
    print(f"\n📋 配置信息:")
    print(f"   模型: {embedding_config.model_name}")
    print(f"   Base URL: {embedding_config.base_url}")
    print(f"   API Key: {embedding_config.api_key[:20]}...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n🔧 初始化向量存储...")
        
        # 创建向量存储管理器
        vector_manager = VectorStoreManager(
            persist_directory=temp_dir,
            enabled=True,
            embedding_config=embedding_config
        )
        
        if not vector_manager.is_enabled():
            print("❌ 向量存储未启用")
            return False
        
        print("✅ 向量存储初始化成功\n")
        
        # 测试添加内容
        print("📝 添加测试内容...")
        test_content = """
        林昭的左眼，第一次，流下了一滴泪。
        不是算法生成的模拟泪滴。
        是真实的、滚烫的、带着体温的，属于人类的泪。
        """
        
        try:
            chunks = vector_manager.add_scene_content(
                content=test_content,
                project_id="test_qwen",
                chapter_index=1,
                scene_index=1
            )
            
            if chunks:
                print(f"✅ 成功创建 {len(chunks)} 个记忆块")
                for i, chunk in enumerate(chunks, 1):
                    print(f"   块 {i}: {chunk.content[:50]}...")
            else:
                print("❌ 未能创建记忆块")
                return False
                
        except Exception as e:
            print(f"❌ 添加内容失败: {e}")
            return False
        
        # 测试搜索
        print("\n🔍 测试语义搜索...")
        test_queries = [
            "林昭的左眼",
            "眼泪",
            "人类的情感",
        ]
        
        for query in test_queries:
            print(f"\n   查询: '{query}'")
            try:
                results = vector_manager.search_similar(
                    query=query,
                    project_id="test_qwen",
                    limit=2
                )
                
                if results:
                    print(f"   ✅ 找到 {len(results)} 个结果")
                    for i, chunk in enumerate(results, 1):
                        preview = chunk.content.replace('\n', ' ').strip()[:60]
                        print(f"      {i}. {preview}...")
                else:
                    print(f"   ⚠️  未找到结果")
                    
            except Exception as e:
                print(f"   ❌ 搜索失败: {e}")
                return False
        
        print("\n" + "=" * 70)
        print("🎉 Qwen Embedding 测试通过！")
        print("=" * 70)
        return True


if __name__ == "__main__":
    try:
        success = test_qwen_embedding()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
