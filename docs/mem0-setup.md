# Mem0 集成设置指南

## 简介

Mem0 是一个专为 LLM 应用设计的智能记忆层，提供自动去重、冲突解决和时间衰减机制。本项目集成 Mem0 实现：

1. **用户记忆（User Memory）**：学习作者的写作偏好和反馈
2. **实体记忆（Entity Memory）**：管理角色的动态状态，自动合并和更新

## 核心特性

### ✅ 零额外部署
- 复用项目现有的 ChromaDB 实例
- 无需部署 Qdrant 或其他向量数据库
- 通过独立的 `collection_name` 隔离 Mem0 数据

### ✅ 智能记忆管理
- 自动去重：相似的偏好会被自动合并
- 冲突解决：自动处理矛盾的状态信息
- 时间衰减：旧的记忆自动降权

### ✅ 向后兼容
- Mem0 作为可选功能，默认禁用
- 启用后，SQLite 和 ChromaDB 仍作为降级备份
- 禁用 Mem0 不影响现有功能

## 快速开始

### 1. 启用 Mem0

在项目根目录的 `.env` 文件中添加：

```bash
# 启用 Mem0
MEM0_ENABLED=true

# OpenAI API Key（必需，用于 Embedding）
OPENAI_API_KEY=your_openai_api_key_here
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
✅ 数据库持久化已启用: projects/demo_001/data/novel.db
✅ 向量存储已启用: projects/demo_001/data/vectors
✅ Mem0 记忆层已启用: Mem0 运行正常
✅ LangGraph 工作流已初始化
```

## 配置选项

### 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `MEM0_ENABLED` | 是否启用 Mem0 | `false` | 否 |
| `OPENAI_API_KEY` | OpenAI API Key（用于 Embedding） | - | 是（启用时） |

### 高级配置

如果需要更细粒度的控制，可以在 `ProjectConfig` 中自定义 `Mem0Config`：

```python
from novelgen.config import ProjectConfig
from novelgen.models import Mem0Config

# 自定义 Mem0 配置
config = ProjectConfig(project_dir="projects/demo_001")
config.mem0_config = Mem0Config(
    enabled=True,
    chroma_path=config.get_vector_store_dir(),  # 复用现有 ChromaDB
    collection_name="custom_mem0_memories",      # 自定义 collection 名称
    embedding_model_dims=1536,                   # Embedding 维度
    timeout=10,                                  # 查询超时（秒）
)
```

## ChromaDB 数据隔离

Mem0 和现有向量检索共享同一个 ChromaDB 实例，但数据完全隔离：

```
ChromaDB 实例 (data/vectors/)
├── novel_memories (现有场景文本、摘要)
└── mem0_memories  (Mem0 用户偏好、实体状态)
```

## 工作原理

### 用户记忆（User Memory）

**记录时机**（预留功能）：
- **当前版本**：不从章节修订过程中自动提取用户偏好（修订是针对具体章节的一致性校验，不应作为长期写作偏好）
- **未来支持**：通过主动设置、UI 交互等方式添加用户偏好
- 示例：通过 API 主动设置「对话需简洁有力，避免过多形容词」

**使用时机**：
- 场景生成前，检索相关的用户偏好
- 将偏好注入到 `chapter_context` 中，指导 LLM 生成符合用户风格的文本

**示例输出**：
```
【用户写作偏好】
以下是用户设定的写作偏好，请在生成时参考：
- [writing_style] 喜欢使用细腻的心理描写，避免过于直白的叙述
- [tone] 整体基调偏向悬疑和紧张感
- [character_development] 角色性格应该逐渐演变，避免突变
```

### 实体记忆（Entity Memory）

**记录时机**：
- 每章生成后，从 `ChapterMemoryEntry` 中提取 `character_states`
- 将每个角色的状态更新到 Mem0

**使用时机**：
- 场景生成前，优先从 Mem0 检索角色的最新状态
- 如果 Mem0 查询失败，回退到 SQLite 的 `EntityStateSnapshot`

**自动合并**：
- Mem0 会自动合并相似的状态描述
- 例如：「张三变得更加谨慎」 + 「张三开始警惕周围的人」 → 「张三变得谨慎且警惕」

## 数据管理

### 查看 Mem0 数据

使用提供的工具脚本：

```bash
# 检查 Mem0 健康状态
uv run python scripts/check_mem0_health.py

# 导出 Mem0 数据到 JSON
uv run python scripts/export_mem0_to_json.py --project demo_001

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

## 性能优化

### 查询超时

默认查询超时为 5 秒，可以根据网络情况调整：

```python
config.mem0_config.timeout = 10  # 增加到 10 秒
```

### 批量操作

Mem0 支持批量添加记忆，可以减少网络开销：

```python
# 在 mem0_manager.py 中使用 client.add() 时
# 可以传递多个 messages 实现批量添加
```

## 故障排查

### Mem0 初始化失败

**症状**：
```
⚠️ Mem0 初始化失败: The api_key client option must be set
```

**解决方案**：
1. 确认 `.env` 文件中设置了 `OPENAI_API_KEY`
2. 检查 API Key 是否有效

### Mem0 查询超时

**症状**：
```
⚠️ 检索用户偏好失败: Request timed out.
```

**解决方案**：
1. 增加 `timeout` 配置
2. 检查网络连接
3. 系统会自动降级到 SQLite，不影响主流程

### 数据不同步

**症状**：Mem0 和 SQLite 数据不一致

**解决方案**：
1. Mem0 作为主查询源，SQLite 作为降级备份
2. 使用 `scripts/sync_mem0_to_sqlite.py` 同步数据（待实现）

## 常见问题

### Q: Mem0 会增加多少延迟？

A: Mem0 查询是异步且并行的，通常在 100-500ms 范围内。如果超时，系统会自动降级到 SQLite。

### Q: 如何迁移现有项目的数据到 Mem0？

A: 暂不支持历史数据迁移。Mem0 仅对新生成内容生效，历史数据仍由 SQLite/ChromaDB 管理。

### Q: 可以同时使用 Mem0 和 SQLite 吗？

A: 是的。Mem0 启用时，系统会同时写入 Mem0 和 SQLite（双写策略），确保数据完整性。

### Q: Mem0 是否支持 Graph Memory？

A: 当前版本暂不支持。未来如果需要复杂的关系推理，可以考虑扩展。

## 相关文档

- [Mem0 官方文档](https://docs.mem0.ai/)
- [项目 OpenSpec 提案](../openspec/changes/add-mem0-integration/proposal.md)
- [迁移指南](./mem0-migration.md)

## 贡献与反馈

如果在使用 Mem0 时遇到问题或有改进建议，请提交 Issue 或 PR。

