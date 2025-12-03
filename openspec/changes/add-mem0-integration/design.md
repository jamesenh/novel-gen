# Mem0 Integration Design

## Context

NovelGen 是一个基于 LangChain/LangGraph 的中文小说自动生成系统。当前使用三种存储机制：
1. **JSON 文件** - 人类可读的中间结果
2. **SQLite** - 结构化的实体快照和记忆块元数据
3. **ChromaDB** - 语义向量检索

当前架构的痛点：
- 实体状态快照（`EntityStateSnapshot`）只是堆叠历史记录，无法自动合并冲突
- 缺乏用户偏好学习机制，无法"记住"作者的修改意图
- 手动管理记忆的复杂度高，容易遗漏或重复

Mem0 是一个专为 LLM 应用设计的记忆层，提供：
- 自动去重和冲突解决
- 多层记忆（User/Agent/Session）
- 时间衰减和相关性排序
- 混合检索（向量 + 元数据）

## Goals / Non-Goals

### Goals
- 阶段一：实现用户偏好学习（User Memory），记录作者的写作风格和反馈
- 阶段二：替换实体快照逻辑（Entity Memory），用 Mem0 管理角色动态状态
- 保持向后兼容，Mem0 作为可选功能（通过配置开关控制）
- 降级策略：Mem0 失败时自动回退到现有的 SQLite 逻辑

### Non-Goals
- 完全移除 SQLite 或 ChromaDB（它们仍作为备份和降级方案）
- 迁移现有项目的历史数据到 Mem0（仅对新生成内容生效）
- 实现 Mem0 的所有高级特性（如 Graph Memory）

## Decisions

### Decision 1: 复用现有 ChromaDB 作为 Mem0 的向量存储

**选择**：使用项目现有的 **ChromaDB** 作为 Mem0 的向量存储后端，实现零额外部署。

**理由**：
- **零部署成本**：项目已有 ChromaDB 实例，无需新增 Qdrant 或其他向量库
- **统一基础设施**：Mem0 和现有的 `VectorStoreManager` 共享同一个 ChromaDB
- **简化运维**：减少需要维护的服务数量
- **向量库隔离**：通过不同的 `collection_name` 隔离 Mem0 的记忆数据和现有的场景文本向量

**实现**：
```python
class Mem0Config(BaseModel):
    enabled: bool = Field(default=False, description="是否启用 Mem0")
    vector_store_provider: str = Field(default="chroma", description="向量存储提供商（当前仅支持 chroma）")
    chroma_path: str = Field(default="data/chroma", description="ChromaDB 存储路径（复用现有路径）")
    collection_name: str = Field(default="mem0_memories", description="Mem0 专用的 Collection 名称")
    embedding_model_dims: int = Field(default=1536, description="Embedding 维度（与项目配置一致）")
```

**ChromaDB Collection 隔离策略**：
- 现有向量检索：`collection_name="novel_memories"` （场景文本、摘要）
- Mem0 记忆存储：`collection_name="mem0_memories"` （用户偏好、实体状态）
- 两者共享同一个 ChromaDB 实例，但数据完全隔离

### Decision 2: User Memory 的存储粒度

**选择**：以 `user_id="author_{project_name}"` 为粒度存储偏好。

**理由**：
- Mem0 的 User Memory 设计就是面向单一用户的个性化记忆
- 不同项目可能有不同的风格要求（例如：`demo_001` 偏黑暗，`demo_002` 偏轻松）
- 使用 `user_id` 隔离不同项目的用户偏好

**示例**：
- 项目 `demo_001` → `user_id="author_demo_001"`
- 项目 `demo_002` → `user_id="author_demo_002"`

### Decision 3: Entity Memory 的映射策略

**选择**：为每个主要角色创建独立的 `agent_id`，使用 Mem0 的 Agent Memory。

**理由**：
- Mem0 的 Agent Memory 适合存储"具有身份的实体"的状态
- 角色是小说生成中最重要的实体，状态变化最复杂
- 使用 `agent_id="{project_id}_{character_name}"` 确保唯一性

**示例**：
- 主角"张三" → `agent_id="demo_001_张三"`
- 反派"李四" → `agent_id="demo_001_李四"`

### Decision 4: 与现有 SQLite/ChromaDB 的关系

**选择**：Mem0 作为**增强层**，而非替换层。

**架构**：
```
生成链 (LangChain)
    ↓
优先查询: Mem0 (智能记忆)
    ↓ (失败时降级)
降级查询: SQLite + ChromaDB (传统记忆)
    ↓
返回上下文
```

**实现策略**：
1. 尝试从 Mem0 检索（如果启用且连接正常）
2. 如果 Mem0 返回空或失败，回退到 SQLite/ChromaDB
3. 新生成的内容同时写入 Mem0 和 SQLite（双写保证数据完整性）

## Risks / Trade-offs

### Risk 1: ChromaDB 共享可能的性能影响
- **风险**：Mem0 和现有向量检索共享 ChromaDB，可能在高负载时产生资源竞争
- **缓解**：
  - 使用独立的 `collection_name` 完全隔离数据
  - Mem0 查询频率低（仅在章节生成前/后），不会与场景文本检索冲突
  - 通过监控工具（`scripts/check_mem0_health.py`）定期检查性能
  - 如果未来性能成为瓶颈，可轻松迁移到独立的 Qdrant 实例

### Risk 2: 数据一致性问题
- **风险**：双写（Mem0 + SQLite）可能导致数据不同步
- **缓解**：
  - Mem0 作为主查询源，SQLite 作为降级备份
  - 如果 Mem0 写入失败，仍然保留 SQLite 写入逻辑
  - 提供数据同步工具（`scripts/sync_mem0_to_sqlite.py`）

### Risk 3: 性能开销
- **风险**：增加 Mem0 查询可能增加延迟
- **缓解**：
  - Mem0 检索是异步且并行的（与 SQLite 查询不冲突）
  - 只在关键节点（场景生成前）查询 Mem0
  - 可通过配置调整 Mem0 查询超时（`mem0_timeout=5s`）

## Migration Plan

### 阶段一：用户记忆（User Memory）
1. 添加 `novelgen/runtime/mem0_manager.py` 模块
2. 在 `novelgen/config.py` 中添加 `Mem0Config`
3. **[已变更]** ~~在 `orchestrator.py` 的修订逻辑中调用 `mem0_manager.add_user_preference()`~~ → 预留用户偏好功能框架，但不从修订过程中提取（修订是针对具体章节/场景的一致性校验，不应作为长期写作偏好）
4. 在 `scene_text_chain.py` 中调用 `mem0_manager.search_user_preferences()` 并注入 Prompt（预留功能）
5. 编写单元测试验证用户偏好存储和检索功能框架

### 阶段二：实体记忆（Entity Memory）
1. 在 `mem0_manager.py` 中添加实体状态管理方法
2. 修改 `memory_context_chain.py`，优先从 Mem0 检索角色状态
3. 在章节生成后，将角色状态更新写入 Mem0（使用 `agent_id`）
4. 编写集成测试验证实体状态的读写和一致性

### 回滚方案
- 如果 Mem0 集成出现严重问题，设置 `config.mem0_enabled=False` 即可回退到原有逻辑
- 所有 Mem0 写入都有对应的 SQLite 备份，数据不会丢失

## Open Questions

1. **是否需要支持 Mem0 的 Graph Memory 特性？**
   - 决策：**暂不支持**。Graph Memory 适合复杂的关系推理，但当前项目重点是状态管理和偏好学习。未来可扩展。

2. **用户偏好的自动过期时间？**
   - 决策：**不设置硬过期**。Mem0 自带时间衰减机制（Recency），旧偏好会自动降权。

3. **是否需要迁移历史项目数据到 Mem0？**
   - 决策：**不需要**。Mem0 仅对新生成内容生效。历史数据仍由 SQLite/ChromaDB 管理。

