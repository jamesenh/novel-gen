## Context
NovelGen是一个6步管道的中文AI小说生成系统，当前完全依赖JSON文件进行状态传递。为支持长期项目管理和记忆检索，需要引入数据库持久化层，但必须保持现有架构的简洁性和链独立性。

## Goals / Non-Goals
- Goals: 
  - 建立状态持久化基础设施，为后续记忆检索奠定基础
  - 保持现有生成流程完全不变，确保向后兼容
  - 提供抽象接口层，便于未来存储实现的切换
- Non-Goals:
  - 不改变现有链的输入输出接口
  - 不引入复杂的查询逻辑或AI工具调用
  - 不影响生成性能或增加显著延迟

## Decisions
- Decision: 使用SQLite作为默认数据库，Chroma作为向量存储
  - 理由：本地部署友好，无需外部依赖，适合单用户创作场景
  - 替代方案考虑：PostgreSQL+pgvector（过于复杂,在后期的优化过程中再考虑）、纯文件存储（缺乏查询能力）
- Decision: 通过抽象层隔离存储实现
  - 理由：遵循项目模块化原则，便于未来技术栈迁移
  - 实现：runtime/db.py和runtime/vector_store.py提供统一接口
- Decision: 在orchestrator层面添加持久化钩子
  - 理由：最小化对现有链的侵入，保持链的纯粹性
  - 实现：每个链执行完成后，将结果序列化并存储

## Risks / Trade-offs
- [风险] 数据库依赖可能影响部署简便性 → 缓解：提供降级模式，数据库不可用时仍可正常运行
- [风险] 持久化操作可能增加生成延迟 → 缓解：异步写入，批量操作，性能监控
- [权衡] 存储冗余 vs 查询效率 → 选择：适度冗余，优先保证查询性能和实现简便性

## Migration Plan
1. **准备阶段**：创建数据库抽象层，不影响现有功能
2. **集成阶段**：在orchestrator添加持久化钩子，保持向后兼容
3. **验证阶段**：端到端测试，确保数据正确存储且不影响生成
4. **回滚计划**：如遇问题，可通过配置禁用持久化功能

## Data Models
### EntityStateSnapshot
```python
class EntityStateSnapshot(BaseModel):
    """实体在特定时间点的状态快照"""
    project_id: str
    entity_type: str  # "character", "location", "item"
    entity_id: str
    chapter_index: Optional[int] = None
    scene_index: Optional[int] = None
    timestamp: datetime
    state_data: Dict[str, Any]  # JSON格式的状态数据
    version: int = 1
```

### StoryMemoryChunk
```python
class StoryMemoryChunk(BaseModel):
    """文本记忆块"""
    chunk_id: str
    project_id: str
    chapter_index: Optional[int] = None
    scene_index: Optional[int] = None
    content: str  # 原始文本内容
    content_type: str  # "scene", "dialogue", "description"
    entities_mentioned: List[str] = []  # 提及的实体ID
    tags: List[str] = []  # 内容标签
    embedding_id: Optional[str] = None  # 向量存储中的ID
    created_at: datetime
```

### SceneMemoryContext
```python
class SceneMemoryContext(BaseModel):
    """场景记忆上下文，用于传递给生成链"""
    project_id: str
    chapter_index: Optional[int] = None
    scene_index: Optional[int] = None
    entity_states: List[EntityStateSnapshot] = []
    relevant_memories: List[StoryMemoryChunk] = []
    timeline_context: Optional[Dict[str, Any]] = None
    retrieval_timestamp: datetime
```

## Open Questions
- 如何处理数据库版本迁移和向后兼容性？
- 向量存储的chunk大小策略如何设定最优？
- 是否需要为大型项目提供数据清理和归档机制？
