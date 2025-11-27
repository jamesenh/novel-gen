# Mem0 记忆层设置指南

## 简介

Mem0 是本项目的唯一记忆存储层，提供：

1. **用户记忆（User Memory）**：学习作者的写作偏好和反馈
2. **实体记忆（Entity Memory）**：管理角色的动态状态，自动合并和更新
3. **场景内容存储**：存储和检索场景文本内容

> **更新说明（2025-11-25）**：从本版本开始，Mem0 是必需的记忆层，不再支持 SQLite 降级模式。

## 核心特性

### ✅ 统一记忆层
- Mem0 作为唯一的记忆存储层
- 内部使用 ChromaDB 进行向量存储
- 所有记忆操作都通过 Mem0Manager 进行

### ✅ 智能记忆管理
- 自动去重：相似的偏好会被自动合并
- 冲突解决：自动处理矛盾的状态信息
- 时间衰减：旧的记忆自动降权

### ✅ 简化架构
- 移除独立的 SQLite 数据库管理器
- 移除独立的 VectorStore 管理器
- 统一的记忆访问接口

## 快速开始

### 1. 启用 Mem0（必需）

在项目根目录的 `.env` 文件中添加：

```bash
# 启用 Mem0（必需）
MEM0_ENABLED=true

# OpenAI API Key（必需，用于 Embedding）
OPENAI_API_KEY=your_openai_api_key_here

# 可选：自定义 Embedding 模型
# EMBEDDING_MODEL_NAME=text-embedding-3-small
# EMBEDDING_API_KEY=your_key  # 如果与 OPENAI_API_KEY 不同
```

### 2. 运行项目

```bash
# 使用 uv（推荐）
uv run python main.py

# 或使用系统 Python
python main.py
```

### 3. 验证 Mem0 状态

启动时查看日志输出：

```
✅ Mem0 记忆层已启用: Mem0 运行正常
✅ LangGraph 工作流已初始化
```

## 配置选项

### 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `MEM0_ENABLED` | 是否启用 Mem0 | `false` | **是** |
| `OPENAI_API_KEY` | OpenAI API Key（用于 Embedding） | - | **是** |
| `EMBEDDING_MODEL_NAME` | Embedding 模型名称 | `text-embedding-3-small` | 否 |
| `EMBEDDING_BASE_URL` | 自定义 API 端点 | - | 否 |

### 高级配置

如果需要更细粒度的控制，可以在 `ProjectConfig` 中自定义 `Mem0Config`：

```python
from novelgen.config import ProjectConfig
from novelgen.models import Mem0Config

# 自定义 Mem0 配置
config = ProjectConfig(project_dir="projects/demo_001")
config.mem0_config = Mem0Config(
    enabled=True,
    chroma_path=config.get_vector_store_dir(),  # ChromaDB 存储路径
    collection_name="custom_mem0_memories",      # 自定义 collection 名称
    embedding_model_dims=1536,                   # Embedding 维度
    timeout=10,                                  # 查询超时（秒）
)
```

## Mem0Manager API

### 用户偏好

```python
# 添加用户偏好
mem0_manager.add_user_preference(
    preference_type="writing_style",
    content="喜欢使用细腻的心理描写",
    source="manual"
)

# 搜索用户偏好
preferences = mem0_manager.search_user_preferences(
    query="写作风格",
    limit=5
)
```

### 实体状态

```python
# 添加实体状态
mem0_manager.add_entity_state(
    entity_id="张三",
    entity_type="character",
    state_description="在第一章中首次登场，表现出强烈的好奇心",
    chapter_index=1,
)

# 获取实体状态
states = mem0_manager.get_entity_state(
    entity_id="张三",
    query="张三的当前状态",
    limit=3
)

# 批量获取角色状态
snapshots = mem0_manager.get_entity_states_for_characters(
    character_names=["张三", "李四"],
    chapter_index=2,
)
```

### 场景内容

```python
# 添加场景内容
chunks = mem0_manager.add_scene_content(
    content="场景文本内容...",
    chapter_index=1,
    scene_index=1,
)

# 搜索场景内容
results = mem0_manager.search_scene_content(
    query="主角决定离开",
    chapter_index=1,  # 可选
    limit=10
)

# 搜索记忆（带过滤条件）
results = mem0_manager.search_memory_with_filters(
    query="关于战斗的场景",
    content_type="scene",
    entities=["张三"],
    limit=10
)
```

## 工作原理

### 用户记忆（User Memory）

**记录时机**：
- 通过 API 主动设置用户偏好
- 未来支持：通过 UI 交互添加

**使用时机**：
- 场景生成前，检索相关的用户偏好
- 将偏好注入到 `chapter_context` 中

**示例输出**：
```
【用户写作偏好】
以下是用户设定的写作偏好，请在生成时参考：
- [writing_style] 喜欢使用细腻的心理描写，避免过于直白的叙述
- [tone] 整体基调偏向悬疑和紧张感
```

### 实体记忆（Entity Memory）

**记录时机**：
- 角色创建时初始化状态
- 每章生成后，从 `ChapterMemoryEntry` 中提取 `character_states`

**使用时机**：
- 场景生成前，从 Mem0 检索角色的最新状态
- 注入到场景记忆上下文中

**自动合并**：
- Mem0 会自动合并相似的状态描述
- 例如：「张三变得更加谨慎」 + 「张三开始警惕周围的人」 → 「张三变得谨慎且警惕」

### 场景内容存储

**记录时机**：
- 每个场景生成后自动存储到 Mem0
- 内容会被自动分块并向量化

**使用时机**：
- 生成新场景时检索相关历史内容
- 支持语义搜索和过滤

## 数据管理

### 查看 Mem0 数据

使用提供的工具脚本：

```bash
# 检查 Mem0 健康状态
uv run python scripts/check_mem0_health.py

# 导出 Mem0 数据到 JSON
uv run python scripts/export_mem0_to_json.py --project demo_001

# 查询实体状态
uv run python scripts/query_entity.py demo_001 张三 --latest

# 搜索场景记忆
uv run python scripts/query_scene_memory.py demo_001 --search "主角决定"

# 清理 Mem0 数据（测试用）
uv run python scripts/clear_mem0_memory.py --project demo_001
```

### 数据备份

Mem0 数据存储在 ChromaDB 中，备份方式：

1. **备份整个 ChromaDB 目录**：
   ```bash
   cp -r projects/demo_001/data/vectors projects/demo_001/data/vectors.backup
   ```

2. **导出为 JSON**：
   ```bash
   uv run python scripts/export_mem0_to_json.py --project demo_001 --output mem0_backup.json
   ```

## 故障排查

### Mem0 未启用

**症状**：
```
RuntimeError: Mem0 未启用。请设置环境变量 MEM0_ENABLED=true。
```

**解决方案**：
1. 在 `.env` 文件中设置 `MEM0_ENABLED=true`
2. 确保环境变量正确加载

### Mem0 初始化失败

**症状**：
```
Mem0InitializationError: Embedding API Key 未设置
```

**解决方案**：
1. 确认 `.env` 文件中设置了 `OPENAI_API_KEY`
2. 检查 API Key 是否有效

### 查询失败

**症状**：
```
❌ 搜索场景内容失败: Request timed out.
```

**解决方案**：
1. 增加 `timeout` 配置
2. 检查网络连接
3. 检查 API 配额

## 常见问题

### Q: Mem0 是必需的吗？

A: 是的。从 2025-11-25 版本开始，Mem0 是唯一的记忆层，不再支持降级模式。必须设置 `MEM0_ENABLED=true` 才能运行项目。

### Q: 如何迁移旧项目？

A: 旧项目的 JSON 文件（world.json, characters.json 等）仍然可用。Mem0 会在运行时自动初始化角色状态。SQLite 数据库和独立向量存储不再使用。

### Q: Mem0 会增加多少延迟？

A: Mem0 查询通常在 100-500ms 范围内，取决于网络条件和数据量。

### Q: 可以使用其他 Embedding 模型吗？

A: 可以。通过设置 `EMBEDDING_MODEL_NAME` 和 `EMBEDDING_BASE_URL` 环境变量使用自定义模型。

## 相关文档

- [Mem0 官方文档](https://docs.mem0.ai/)
- [项目 OpenSpec 提案](../openspec/changes/add-mem0-integration/proposal.md)

## 贡献与反馈

如果在使用 Mem0 时遇到问题或有改进建议，请提交 Issue 或 PR。
