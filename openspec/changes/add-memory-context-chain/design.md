# 记忆上下文检索链设计文档

## Context
当前系统通过JSON文件在链之间传递信息，缺乏动态的历史记忆检索能力。阶段1和阶段2已建立数据库和向量存储基础设施，现在需要一个智能层来桥接生成链和持久化层，使LLM能够根据场景需求主动检索相关记忆。

## Goals / Non-Goals

### Goals
- 实现独立的记忆检索链，可单独运行和测试
- 使用LLM理解场景需求，生成检索查询
- 整合数据库和向量存储的查询结果
- 输出结构化的`SceneMemoryContext`对象
- 保持与现有架构的一致性（链独立、JSON通信、Pydantic模型）

### Non-Goals
- 不修改现有的`scene_text_chain`（留待阶段4）
- 不实现orchestrator集成（仅定义接口）
- 不实现Function Call机制（阶段5可选特性）
- 不优化检索性能（初期关注正确性）

## Decisions

### 决策1：链的输入输出设计
**决策**：
- **输入**：通过参数传入`ScenePlan`、`CharactersConfig`、`project_id`、`chapter_index`、`scene_index`
- **输出**：`SceneMemoryContext` Pydantic对象，写入JSON文件

**理由**：
- 遵循现有的链设计模式（无状态、JSON通信）
- 输入包含足够的上下文让LLM理解场景需求
- 输出结构化，便于后续链消费

**替代方案**：
- 直接在`scene_text_chain`中内嵌检索逻辑 → 违反链独立性原则
- 使用Function Call动态查询 → 过于复杂，留待阶段5

### 决策2：Prompt设计策略
**决策**：引导LLM分两步思考：
1. 分析场景涉及的实体和事件
2. 生成向量检索的查询关键词

**理由**：
- 结构化思考过程提高检索准确性
- 避免直接让LLM猜测数据库内容
- 查询关键词可用于向量检索

**替代方案**：
- 使用规则提取实体 → 无法处理隐含关系
- 让LLM直接输出SQL/查询 → 增加复杂度，容易出错

### 决策3：工具函数层设计
**决策**：在`runtime/memory_tools.py`中封装便捷接口

**理由**：
- 抽象层隔离链和底层存储
- 便于未来迁移到Function Call模式
- 复用现有的`DatabaseManager`和`VectorStoreManager`

**替代方案**：
- 链直接调用Manager → 耦合度高，不便维护
- 完全不封装 → 代码重复

### 决策4：降级策略
**决策**：
- 向量检索失败 → 返回空记忆列表，继续执行
- 数据库查询失败 → 返回空状态列表，继续执行
- JSON写入失败 → 记录警告，不阻止后续流程

**理由**：
- 记忆检索是增强功能，不应成为阻塞点
- 降级到原有的纯JSON文件模式
- 符合阶段1设计的"不影响主流程"原则

## 与阶段3方案文档的对齐说明

 本变更与《数据库与向量库渐进式落地方案》中的阶段3设计总体目标一致，但在具体数据结构和接口上做了一些演化。为避免读者来回跳转，这里补充说明四个主要差异及最终决策。

### 差异1：SceneMemoryContext 数据结构

 - 阶段3文档中曾给出一个草案结构，包含 `relevant_entities`、`recent_events` 等字段，并假设 `relevant_memories` 使用带打分的 `StoryMemoryHit`。
 - 在阶段1/2 的实现和 `novelgen/models.py` 中，`SceneMemoryContext` 已有稳定定义：
   - `project_id`、`chapter_index`、`scene_index`：标识当前场景
   - `entity_states: List[EntityStateSnapshot]`：实体状态列表
   - `relevant_memories: List[StoryMemoryChunk]`：相关记忆块（不直接暴露打分）
   - `timeline_context: Optional[Dict[str, Any]]`：时间线上下文聚合
   - `retrieval_timestamp: datetime`：检索时间戳
 - **最终决策**：以 `models.py` 中的 Pydantic 定义为唯一真源，不再在本设计文档中重复早期草案结构。阶段3文档中出现的字段差异视为历史设计记录，本变更按照当前模型实现。

### 差异2：记忆检索工具接口

 - 阶段3文档中的初稿接口示例：
   - `get_entity_state(project_id, entity_id, chapter_index, scene_index) -> EntityStateSnapshot | {"found": false}`
   - `get_timeline(project_id, from_chapter, to_chapter, entity_id?) -> List[TimelineEvent]`
   - `search_story_memory(project_id, query, entities, top_k) -> List[StoryMemoryHit]`
 - 本变更在 `runtime/memory_tools.py` 规划的工具函数与规范中的命名保持一致，更贴合当前数据模型：
   - `search_story_memory_tool(...) -> List[StoryMemoryChunk]`：接受查询词、实体过滤、内容类型、标签以及 `top_k` 等参数，底层可以保留相似度分数，但对上层链只暴露语义相关的记忆块列表。
   - `get_entity_state_tool(...) -> Optional[EntityStateSnapshot]`：用 `None` 表示未找到，避免再包装一层 `{found: false}`。
   - `get_recent_timeline_tool(...) -> List[EntityStateSnapshot]`：相比早期的 `get_timeline`，更关注“某章节前后的一段状态窗口”，而不是通用事件流。
 - **最终决策**：以 `memory-context-retrieval` 规范和 `memory_tools` 计划接口为准，将阶段3文档中的函数视为语义上的等价前身：
   - 语义映射关系为：`get_entity_state` ≈ `get_entity_state_tool`，`get_timeline` ≈ `get_recent_timeline_tool`，`search_story_memory` ≈ `search_story_memory_tool`。

 ### 差异3：memory_context_chain 的输入参数

 - 阶段3文档中示例输入为 `{Settings, ChapterPlan, ScenePlan, project_id}`，倾向于把章节级信息一次性塞入链中。
 - 本设计在“决策1”中采用了更精简和聚焦的输入：`ScenePlan`、`CharactersConfig`、`project_id`、`chapter_index`、`scene_index`。
 - **理由**：
   - 绝大部分记忆检索需求可以通过 `ScenePlan` + 标识信息（project/chapter/scene）满足。
   - 精简输入可以减少 Prompt token 开销，也降低链和 orchestrator 之间的耦合度。
   - orchestrator 仍然可以在需要时，将部分 `Settings` 或 `ChapterPlan` 内容预处理后作为额外文本提示注入 Prompt，而不强制所有字段都作为结构化输入传递。
 - **最终决策**：
   - 规范层面仅要求上述最小必需参数，保持链的通用性和无状态特性。
   - 对阶段3文档中更大颗粒度的输入示例，视为一种可选的上层集成方式，而非本变更必须满足的严格接口约束。

 ### 差异4：阶段3最小能力 vs 目标能力范围

 - 阶段3文档的实施步骤建议“先让链只调用 `search_story_memory`，汇总为 `SceneMemoryContext`”，把它作为验证向量检索效果的最低门槛。
 - 本变更在规范中直接定义了更完整的目标形态：同时支持
   - 基于向量库的历史记忆检索（`relevant_memories`）
   - 基于数据库的实体状态查询（`entity_states`）
   - 时间线窗口上下文（通过 `timeline_context` 或相关工具函数聚合）
 - **最终决策**：
   - 规范描述采用“目标能力”的完整版本，确保后续阶段不需要再拆分一次规范。
   - 实际实现可以按阶段3文档的建议，从“只实现 `search_story_memory_tool` 路径”起步；当数据库状态数据和时间线工具就绪后，再逐步填充实体状态和时间线相关字段。
   - 通过“降级策略”（决策4 + `Graceful Degradation` 规范），保证在部分能力尚未实现或依赖不可用时，链仍然可用，只是输出的 `SceneMemoryContext` 信息较少。

 以上说明保证本设计文档在不依赖其他设计文档的情况下，也能完整呈现与阶段3原始方案之间的差异与演化路径。

## Risks / Trade-offs

### 风险1：LLM理解偏差导致检索不相关
**缓解措施**：
- 精心设计Prompt，提供场景计划完整信息
- 初期通过手动检查验证检索质量
- 后续可添加相关性评分机制

### 风险2：检索结果过多或过少
**缓解措施**：
- 使用`top_k`参数控制返回数量（默认10个）
- 支持按content_type、entities、tags过滤
- 后续可根据实际效果调整参数

### 风险3：性能开销
**缓解措施**：
- 初期不优化，关注正确性
- 向量检索本身已足够快（Chroma）
- 后续可添加缓存机制

## Migration Plan

### 实施步骤
1. **Phase 1**：实现工具函数层（1-2小时）
2. **Phase 2**：实现检索链（2-3小时）
3. **Phase 3**：编写测试和手动验证（1-2小时）
4. **Phase 4**：文档更新（30分钟）

### 回滚策略
- 新增功能独立，删除文件即可回滚
- 不影响现有生成流程
- 无数据库schema变更

## Open Questions
- Q: 是否需要实现记忆的相关性评分？
  - A: 阶段3不实现，依赖向量检索的相似度分数

- Q: 是否需要支持跨项目的记忆检索？
  - A: 不需要，始终按project_id过滤

- Q: 检索到的记忆如何去重？
  - A: 阶段3不处理，依赖向量库的ID唯一性
