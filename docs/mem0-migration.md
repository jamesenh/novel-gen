# Mem0 迁移指南

## 概述

本指南说明如何从旧版架构（SQLite + 独立 VectorStore）迁移到新的 Mem0 统一记忆层。

> **重要更新（2025-11-25）**：Mem0 现在是唯一的记忆层，不再支持 SQLite 降级模式。

## 架构变化

### 旧架构

```
记忆存储
├── DatabaseManager (SQLite)
│   ├── entity_snapshots 表
│   └── memory_chunks 表
└── VectorStoreManager (ChromaDB)
    └── 场景内容向量
```

### 新架构

```
记忆存储
└── Mem0Manager (唯一记忆层)
    ├── 用户偏好 (User Memory)
    ├── 实体状态 (Entity Memory)
    └── 场景内容 (内部使用 ChromaDB)
```

## 迁移步骤

### 1. 环境准备

确保已安装最新依赖：

```bash
# 使用 uv
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `.env` 文件中添加：

```bash
# 启用 Mem0（必需）
MEM0_ENABLED=true

# OpenAI API Key（必需）
OPENAI_API_KEY=your_openai_api_key_here

# 可选配置
# EMBEDDING_MODEL_NAME=text-embedding-3-small
```

### 3. 验证配置

```bash
uv run python scripts/check_mem0_health.py
```

预期输出：

```
✅ Mem0 运行正常
  - ChromaDB 路径: projects/demo_001/data/vectors
  - Collection: mem0_memories
```

### 4. 运行项目

```bash
uv run python main.py
```

## 代码变化

### NovelOrchestrator 变化

**旧代码**：
```python
# 初始化多个管理器
self.db_manager = DatabaseManager(db_path, enabled=True)
self.vector_manager = VectorStoreManager(vector_dir, enabled=True)
self.mem0_manager = Mem0Manager(config, project_id, embedding_config)
```

**新代码**：
```python
# 只初始化 Mem0
self.mem0_manager = Mem0Manager(
    config=self.config.mem0_config,
    project_id=project_name,
    embedding_config=self.config.embedding_config
)
```

### 保存实体状态

**旧代码**：
```python
def _save_entity_snapshot(self, ...):
    if self.db_manager and self.db_manager.is_enabled():
        self.db_manager.save_entity_snapshot(snapshot)
```

**新代码**：
```python
def _save_entity_state(self, ...):
    self.mem0_manager.add_entity_state(
        entity_id=entity_id,
        entity_type=entity_type,
        state_description=state_description,
        chapter_index=chapter_index,
    )
```

### 保存场景内容

**旧代码**：
```python
def _save_scene_content_to_vector(self, ...):
    if self.vector_manager and self.vector_manager.is_enabled():
        chunks = self.vector_manager.add_scene_content(...)
        if self.db_manager:
            for chunk in chunks:
                self.db_manager.save_memory_chunk(chunk)
```

**新代码**：
```python
def _save_scene_content(self, ...):
    chunks = self.mem0_manager.add_scene_content(
        content=content,
        chapter_index=chapter_index,
        scene_index=scene_index,
    )
```

### 检索记忆

**旧代码**：
```python
# 从 VectorStoreManager 检索
chunks = vector_manager.search_memory_with_filters(...)

# 从 DatabaseManager 检索状态
snapshot = db_manager.get_latest_entity_state(...)
```

**新代码**：
```python
# 统一从 Mem0 检索
chunks = mem0_manager.search_memory_with_filters(...)
states = mem0_manager.get_entity_state(...)
```

## 已删除的文件

以下文件已被删除：

- `novelgen/runtime/db.py` - SQLite 数据库管理器
- `novelgen/runtime/db_migrations.py` - 数据库迁移
- `novelgen/runtime/vector_store.py` - 独立向量存储管理器
- `novelgen/runtime/test_db.py` - 数据库测试
- `novelgen/runtime/test_vector_store.py` - 向量存储测试
- `novelgen/runtime/test_orchestrator_integration.py` - 旧集成测试
- `novelgen/runtime/reindex_tools.py` - 向量重建工具

## 已删除的配置

以下配置项已被移除：

- `ProjectConfig.persistence_enabled`
- `ProjectConfig.vector_store_enabled`
- `ProjectConfig.db_path`
- `ProjectConfig.get_db_path()`
- `Settings.persistence_enabled`
- `Settings.vector_store_enabled`
- `NovelGenerationState.db_manager`
- `NovelGenerationState.vector_manager`

## 历史数据处理

### JSON 文件（保留）

以下文件仍然保留并正常工作：

- `world.json` - 世界观设定
- `theme_conflict.json` - 主题冲突
- `characters.json` - 角色配置
- `outline.json` - 大纲
- `chapters/chapter_XXX.json` - 章节内容
- `chapter_memory.json` - 章节记忆

### SQLite 数据库（不再使用）

项目目录下的 `data/novel.db` 文件不再被使用。如果需要，可以手动删除：

```bash
rm projects/demo_001/data/novel.db
```

### ChromaDB 数据（继续使用）

Mem0 会继续使用 `data/vectors` 目录存储向量数据，但使用不同的 collection。

## 常见问题

### Q: 旧项目还能运行吗？

A: 能，但需要启用 Mem0。JSON 文件仍然正常工作，SQLite 数据不再被读取。

### Q: 如何迁移旧项目的 SQLite 数据？

A: 不需要迁移。Mem0 会在运行时自动初始化角色状态。如果需要历史状态，可以手动从 SQLite 导出并调用 `mem0_manager.add_entity_state()` 导入。

### Q: 为什么移除了降级模式？

A: 简化架构，减少维护复杂性。Mem0 是成熟的记忆层，不需要额外的降级机制。

### Q: 如果 Mem0 初始化失败怎么办？

A: 程序会抛出 `Mem0InitializationError` 异常并退出。检查：
1. `MEM0_ENABLED=true` 是否设置
2. `OPENAI_API_KEY` 是否有效
3. 网络连接是否正常

## 相关文档

- [Mem0 设置指南](./mem0-setup.md)
- [OpenSpec 提案](../openspec/changes/add-mem0-integration/proposal.md)

## 反馈与支持

如果在迁移过程中遇到问题，请：
1. 查看日志输出（搜索 "Mem0" 关键词）
2. 运行健康检查脚本
3. 提交 Issue 描述问题
