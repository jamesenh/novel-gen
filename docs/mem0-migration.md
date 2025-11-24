# Mem0 迁移指南

## 概述

本指南说明如何从纯 SQLite/ChromaDB 架构迁移到 Mem0 增强模式。

## 迁移策略

### 渐进式迁移（推荐）

Mem0 采用"增强而非替换"的设计，支持渐进式迁移：

1. **阶段 1：测试环境启用**
   - 在新项目中启用 Mem0
   - 验证功能是否正常
   - 评估性能影响

2. **阶段 2：现有项目逐步启用**
   - 选择 1-2 个现有项目启用 Mem0
   - 观察记忆学习效果
   - 收集用户反馈

3. **阶段 3：全面推广**
   - 默认启用 Mem0
   - 保留 SQLite 作为降级方案

## 迁移步骤

### 1. 环境准备

确保已安装 `mem0ai` 依赖：

```bash
# 使用 uv
uv pip install mem0ai

# 或使用 pip
pip install mem0ai
```

### 2. 配置环境变量

在 `.env` 文件中添加：

```bash
# 启用 Mem0
MEM0_ENABLED=true

# OpenAI API Key（必需）
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 运行健康检查

```bash
uv run python scripts/check_mem0_health.py
```

预期输出：

```
✅ Mem0 运行正常
  - ChromaDB 路径: projects/demo_001/data/vectors
  - Collection: mem0_memories
```

### 4. 开始新项目

```bash
uv run python main.py
```

Mem0 会自动开始工作：

- **用户偏好**：预留功能框架，当前需主动设置（不从修订过程中自动提取）
- **角色状态**：从章节生成中自动更新

### 5. 验证效果

生成 2-3 章后，检查 Mem0 是否学习到偏好：

```bash
uv run python scripts/export_mem0_to_json.py --project demo_001
```

查看导出的 JSON 文件，确认：
- 用户偏好是否被正确记录
- 角色状态是否被自动更新

## 历史数据处理

### 不需要迁移历史数据

Mem0 设计为"前向兼容"：

- **历史项目**：继续使用 SQLite/ChromaDB，数据完整保留
- **新内容**：自动写入 Mem0（同时也写入 SQLite 作为备份）

### 如果确实需要迁移（可选）

虽然不推荐，但如果确实需要将历史数据导入 Mem0，可以：

1. **导出 SQLite 快照**：
   ```bash
   uv run python scripts/export_sqlite_to_json.py --project demo_001
   ```

2. **手动转换为 Mem0 格式**：
   ```python
   from novelgen.runtime.mem0_manager import Mem0Manager
   from novelgen.models import Mem0Config
   
   # 初始化 Mem0
   config = Mem0Config(enabled=True, chroma_path="projects/demo_001/data/vectors")
   manager = Mem0Manager(config=config, project_id="demo_001")
   
   # 逐条添加历史数据
   for entity_snapshot in historical_data:
       manager.add_entity_state(
           entity_id=entity_snapshot['entity_id'],
           entity_type=entity_snapshot['entity_type'],
           state_description=entity_snapshot['state_data'],
           chapter_index=entity_snapshot['chapter_index'],
       )
   ```

## 回滚策略

如果 Mem0 出现问题，可以快速回滚：

### 1. 禁用 Mem0

在 `.env` 中：

```bash
MEM0_ENABLED=false
```

### 2. 系统自动降级

- 所有查询回退到 SQLite
- 所有数据继续正常保存
- **无数据丢失**

### 3. 清理 Mem0 数据（可选）

如果需要完全移除 Mem0 数据：

```bash
# 清理指定项目的 Mem0 记忆
uv run python scripts/clear_mem0_memory.py --project demo_001

# 或手动删除 ChromaDB collection
rm -rf projects/demo_001/data/vectors/chroma.sqlite3
```

## 数据一致性保证

### 双写策略

Mem0 启用时，系统采用"双写"策略：

```
新内容生成
  ├─> 写入 Mem0（智能记忆）
  └─> 写入 SQLite（降级备份）
```

### 查询优先级

```
场景生成前
  ├─> 优先从 Mem0 检索（智能合并的状态）
  ├─> 如果失败，降级到 SQLite
  └─> 如果都失败，使用空上下文
```

## 性能影响

### 延迟

- Mem0 查询：+100-500ms（异步，不阻塞主流程）
- SQLite 查询：+10-50ms
- 总体影响：<5%

### 存储空间

- Mem0 使用 ChromaDB 存储，额外空间需求：+10-20% (vs 纯 SQLite)
- 但数据更加结构化，检索效率更高

### 网络开销

- Mem0 需要调用 OpenAI Embedding API
- 平均每次查询：2-5 个 API 调用
- 成本：约 $0.0001/次 (text-embedding-3-small)

## 常见问题

### Q: 迁移会丢失数据吗？

A: **不会**。Mem0 采用"增强"策略，所有数据继续保存到 SQLite。

### Q: 如果 Mem0 失败，系统还能工作吗？

A: **能**。系统会自动降级到 SQLite，不影响主流程。

### Q: 可以只在部分项目启用 Mem0 吗？

A: **暂不支持**。`MEM0_ENABLED` 是全局配置。如果需要按项目启用，可以修改 `ProjectConfig.__init__` 逻辑。

### Q: Mem0 和 SQLite 数据不同步怎么办？

A: Mem0 作为主查询源，SQLite 作为降级备份。如果发现不同步，可以：
1. 清空 Mem0 数据，重新生成
2. 使用 `scripts/sync_mem0_to_sqlite.py`（待实现）

## 相关文档

- [Mem0 设置指南](./mem0-setup.md)
- [OpenSpec 提案](../openspec/changes/add-mem0-integration/proposal.md)
- [配置示例](../openspec/changes/add-mem0-integration/CONFIG_EXAMPLE.md)

## 反馈与支持

如果在迁移过程中遇到问题，请：
1. 查看日志输出（搜索 "Mem0" 关键词）
2. 运行健康检查脚本
3. 提交 Issue 描述问题

