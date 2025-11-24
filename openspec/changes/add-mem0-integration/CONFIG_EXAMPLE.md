# Mem0 配置示例

本文档展示如何配置 Mem0 以复用现有的 ChromaDB 实例。

## 核心原理

Mem0 将使用项目现有的 ChromaDB 实例，但通过独立的 `collection_name` 隔离数据：

```
ChromaDB 实例 (data/chroma/)
├── novel_memories (现有)     # 场景文本、摘要向量
└── mem0_memories (新增)       # Mem0 用户偏好和实体状态
```

## 配置方式

### 方式 1：代码配置（推荐）

在 `novelgen/config.py` 中添加 Mem0 配置：

```python
class Mem0Config(BaseModel):
    """Mem0 配置"""
    enabled: bool = Field(default=False, description="是否启用 Mem0")
    vector_store_provider: str = Field(default="chroma", description="向量存储提供商")
    collection_name: str = Field(default="mem0_memories", description="Mem0 Collection 名称")
    embedding_model_dims: int = Field(default=1536, description="Embedding 维度")

class ProjectConfig:
    # ... 现有配置 ...
    
    @property
    def mem0_config(self) -> Mem0Config:
        """获取 Mem0 配置"""
        return Mem0Config(
            enabled=os.getenv("MEM0_ENABLED", "false").lower() == "true",
            # ChromaDB 路径自动从现有配置获取
            # 无需用户手动配置
        )
```

### 方式 2：环境变量配置

在 `.env` 文件中添加：

```bash
# Mem0 配置（可选，默认禁用）
MEM0_ENABLED=true  # 设为 true 启用 Mem0
```

## 初始化代码示例

在 `novelgen/runtime/mem0_manager.py` 中：

```python
from mem0 import Memory
from novelgen.config import ProjectConfig

class Mem0Manager:
    def __init__(self, project_config: ProjectConfig):
        self.config = project_config.mem0_config
        self.memory_client = None
        
        if self.config.enabled:
            self._initialize()
    
    def _initialize(self):
        """初始化 Mem0 客户端，复用现有 ChromaDB"""
        try:
            # 从项目配置获取 ChromaDB 路径
            chroma_path = self.project_config.get_vector_store_dir()
            
            # 配置 Mem0 使用现有的 ChromaDB
            mem0_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "path": str(chroma_path),
                        "collection_name": "mem0_memories",  # 独立 collection
                        "embedding_model_dims": 1536,
                    }
                },
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": self.project_config.llm_model,
                        "api_key": os.getenv("OPENAI_API_KEY"),
                        # 如果配置了自定义 BASE_URL，也需要传入
                        "base_url": os.getenv("OPENAI_BASE_URL"),
                    }
                },
                # 使用与项目一致的 Embedding 配置
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": self.project_config.embedding_config.model_name,
                        "api_key": os.getenv("OPENAI_API_KEY"),
                        "base_url": os.getenv("OPENAI_BASE_URL"),
                    }
                }
            }
            
            self.memory_client = Memory.from_config(mem0_config)
            logger.info("✅ Mem0 已初始化（复用现有 ChromaDB）")
            
        except Exception as e:
            logger.warning(f"⚠️ Mem0 初始化失败，降级到 SQLite: {e}")
            self.memory_client = None
            self.config.enabled = False
```

## 使用示例

### 用户偏好存储

```python
# 示例：主动添加用户偏好（预留功能）
# 注意：当前版本不从修订过程中自动提取偏好
mem0_manager.add_user_preference(
    preference_type="writing_style",
    content="避免使用过多形容词，对话需简洁有力",
    source="manual"  # 主动设置，而非从修订过程中提取
)
```

### 实体状态管理

```python
# 为角色创建 Agent Memory
mem0_manager.add_entity_state(
    content="张三获得了一把断剑，决心修复它",
    agent_id="demo_001_张三",
    metadata={"chapter": 5, "scene": 2}
)

# 检索角色最新状态
state = mem0_manager.get_entity_state(
    query="张三的装备和状态",
    agent_id="demo_001_张三"
)
```

## 数据隔离验证

检查 ChromaDB 中的 Collections：

```python
import chromadb

client = chromadb.PersistentClient(path="data/chroma")
collections = client.list_collections()

for col in collections:
    print(f"Collection: {col.name}")
    print(f"  Count: {col.count()}")
    print(f"  Metadata: {col.metadata}")

# 期望输出：
# Collection: novel_memories
#   Count: 1234  # 场景文本向量
#   Metadata: {'description': 'NovelGen故事记忆向量存储'}
#
# Collection: mem0_memories
#   Count: 56    # Mem0 记忆数据
#   Metadata: {'hnsw:space': 'cosine'}
```

## 降级行为

如果 Mem0 初始化失败或运行时出错：

1. **自动降级**：系统自动回退到 SQLite/ChromaDB（现有逻辑）
2. **日志记录**：记录警告日志但不中断流程
3. **功能保留**：核心小说生成功能不受影响

```python
# 在 orchestrator.py 中的降级逻辑
if self.mem0_manager and self.mem0_manager.is_enabled():
    try:
        preferences = self.mem0_manager.search_user_preferences(query)
    except Exception as e:
        logger.warning(f"Mem0 查询失败，使用默认配置: {e}")
        preferences = []  # 降级为空偏好
```

## 性能考虑

- **查询频率**：低（仅在章节生成前/后）
- **资源竞争**：通过独立 collection 避免与现有向量检索冲突
- **监控**：使用 `scripts/check_mem0_health.py` 定期检查性能指标

## 未来迁移路径

如果未来需要独立的向量数据库：

```python
# 只需修改配置即可迁移到 Qdrant
mem0_config = {
    "vector_store": {
        "provider": "qdrant",  # 从 chroma 改为 qdrant
        "config": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "mem0_memories",
        }
    },
    # ... 其他配置不变
}
```

**数据迁移**：使用 `scripts/migrate_mem0_chroma_to_qdrant.py` 工具。

