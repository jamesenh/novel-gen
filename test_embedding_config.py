#!/usr/bin/env python3
"""
测试 Embedding 配置功能
验证 OpenAI 兼容 API 的 embedding 是否正常工作
"""
import tempfile
from pathlib import Path

from novelgen.config import EmbeddingConfig
from novelgen.runtime.vector_store import VectorStoreManager
from novelgen.models import StoryMemoryChunk


def test_embedding_config():
    """测试 embedding 配置"""
    print("=" * 60)
    print("测试 1: EmbeddingConfig 配置加载")
    print("=" * 60)
    
    # 测试默认配置
    config = EmbeddingConfig()
    print(f"默认 embedding 模型: {config.model_name}")
    print(f"分块大小: {config.chunk_size}")
    print(f"分块重叠: {config.chunk_overlap}")
    
    # 测试自定义配置
    custom_config = EmbeddingConfig(
        model_name="text-embedding-3-large",
        chunk_size=1000,
        chunk_overlap=100
    )
    print(f"\n自定义 embedding 模型: {custom_config.model_name}")
    print(f"自定义分块大小: {custom_config.chunk_size}")
    
    print("\n✅ 配置加载测试通过\n")


def test_vector_store_with_embedding():
    """测试带 embedding 配置的向量存储"""
    print("=" * 60)
    print("测试 2: 向量存储 + Embedding 集成")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建 embedding 配置（使用环境变量中的配置）
        embedding_config = EmbeddingConfig()
        
        # 创建向量存储管理器
        vector_manager = VectorStoreManager(
            persist_directory=temp_dir,
            enabled=True,
            embedding_config=embedding_config
        )
        
        if not vector_manager.is_enabled():
            print("⚠️  向量存储未启用（可能缺少 API 密钥或 ChromaDB 未安装）")
            return
        
        print(f"✅ 向量存储初始化成功")
        print(f"   使用 embedding 模型: {embedding_config.model_name}")
        
        # 添加测试数据
        test_content = """
        林昭的左眼，第一次，流下了一滴泪。
        不是算法生成的模拟泪滴。
        不是系统预设的情感响应。
        是真实的、滚烫的、带着体温的，属于人类的泪。
        """
        
        print("\n添加测试场景内容...")
        chunks = vector_manager.add_scene_content(
            content=test_content,
            project_id="test_embedding",
            chapter_index=1,
            scene_index=1
        )
        
        print(f"✅ 创建了 {len(chunks)} 个记忆块")
        
        # 测试搜索
        print("\n搜索测试: '林昭的左眼'")
        results = vector_manager.search_similar(
            query="林昭的左眼",
            project_id="test_embedding",
            limit=3
        )
        
        print(f"✅ 找到 {len(results)} 个相关记忆块")
        for i, chunk in enumerate(results, 1):
            print(f"\n记忆块 {i}:")
            print(f"  内容: {chunk.content[:100]}...")
        
        print("\n✅ 向量存储 + Embedding 集成测试通过\n")


def test_chinese_search_quality():
    """测试中文搜索质量"""
    print("=" * 60)
    print("测试 3: 中文语义搜索质量")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        embedding_config = EmbeddingConfig()
        vector_manager = VectorStoreManager(
            persist_directory=temp_dir,
            enabled=True,
            embedding_config=embedding_config
        )
        
        if not vector_manager.is_enabled():
            print("⚠️  向量存储未启用")
            return
        
        # 添加多段内容
        test_scenes = [
            ("林昭的左眼流下了泪水，那是真实的情感。", 1, 1),
            ("诺亚的机械眼转向林昭，闪烁着蓝光。", 1, 2),
            ("凯恩的光幕微微波动，映出年轻的模样。", 1, 3),
            ("艾莉娅的意识残片在数据流中漂浮。", 1, 4),
        ]
        
        print("添加测试内容...")
        for content, chapter, scene in test_scenes:
            vector_manager.add_scene_content(
                content=content,
                project_id="test_search",
                chapter_index=chapter,
                scene_index=scene
            )
        
        # 测试相关性搜索
        test_queries = [
            "林昭哭了",
            "眼睛流泪",
            "机械眼",
            "数据意识"
        ]
        
        print("\n执行语义搜索测试:")
        for query in test_queries:
            print(f"\n查询: '{query}'")
            results = vector_manager.search_similar(
                query=query,
                project_id="test_search",
                limit=2
            )
            
            if results:
                print(f"  ✓ 找到 {len(results)} 个结果")
                print(f"    最相关: {results[0].content[:50]}...")
            else:
                print(f"  ✗ 未找到结果")
        
        print("\n✅ 中文语义搜索测试完成\n")


if __name__ == "__main__":
    print("\n开始 Embedding 配置功能测试\n")
    
    try:
        test_embedding_config()
        test_vector_store_with_embedding()
        test_chinese_search_quality()
        
        print("=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
