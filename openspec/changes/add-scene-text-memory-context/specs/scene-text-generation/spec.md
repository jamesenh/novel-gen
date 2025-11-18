## ADDED Requirements

### Requirement: Integrate Scene Memory Context into Scene Generation
场景文本生成链 scene_text_chain MUST 接受结构化的 SceneMemoryContext 作为输入，并将其作为 previous_summary 与 chapter_context 之外的关键约束来源，用于保证角色状态和长期伏笔的一致性与连贯性。

#### Scenario: Use entity_states as authoritative state source
- **WHEN** 调用 scene_text_chain 且提供了 SceneMemoryContext.entity_states
- **THEN** 生成的场景文本 MUST 尊重其中给出的实体状态（例如HP、位置、关系标记、重要flag等）
- **AND** 不得在没有合理剧情过程的前提下推翻这些状态（例如已死亡角色突然复活、已离场角色突然出现在不合理地点）
- **AND** 新引入的状态变化（受伤、关系恶化、立下新约定等）必须在这些既有状态基础上进行自然延展

#### Scenario: Use recent_events and relevant_memories for narrative coherence
- **WHEN** SceneMemoryContext.recent_events 和 relevant_memories 字段非空
- **THEN** scene_text_chain 的 Prompt MUST 在上下文中纳入最近关键事件和高相关记忆片段的精简表示
- **AND** 生成的文本 MUST 体现这些事件与记忆对当前场景的影响（例如兑现承诺、回应伏笔、延续冲突）
- **AND** 不得无视或直接否定这些记忆中已确立的事实，除非在剧情中给出清晰且合理的解释

#### Scenario: Combine chapter_context and memory context
- **WHEN** 同时提供 chapter_context 与 SceneMemoryContext
- **THEN** Prompt MUST 明确说明：
  - chapter_context 提供跨章节的宏观走向与未解决悬念
  - SceneMemoryContext 提供当前场景相关的精细状态与片段级记忆
- **AND** 生成逻辑 MUST 同时遵守二者中的约束，不得出现 chapter_context 与 SceneMemoryContext 之间的显式矛盾

#### Scenario: Graceful degradation without memory context
- **WHEN** 对应场景的 SceneMemoryContext JSON 不存在、解析失败，或仅部分字段可用
- **THEN** scene_text_chain MUST 继续工作，并自动退回到仅依赖 previous_summary 与 chapter_context 的模式
- **AND** 缺失的记忆上下文 MUST NOT 改变链的输入/输出接口签名
- **AND** 在实现层面 SHOULD 记录告警日志，方便在后续阶段排查记忆链或持久化层的问题
