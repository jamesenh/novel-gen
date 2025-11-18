## Why

阶段1–3已经完成了数据持久化基础设施（persistence）和记忆检索链（memory_context_chain），scene_text_chain 仍然只依赖 previous_summary 和 chapter_context，对结构化记忆（SceneMemoryContext）缺乏统一的规范约束。

这导致：
- 角色状态（HP、位置、关系、flag）仍可能与数据库中的最新状态快照不一致
- 重要承诺、伏笔、关系变化已经存入记忆库，但场景生成提示词未必显式使用
- memory_context_chain 的价值难以在最终文本中稳定体现

需要一个面向“阶段4：scene_text_chain 接入记忆上下文”的规范级提案，明确 scene_text_chain 如何消费 SceneMemoryContext，并在缺失记忆时如何优雅降级。

## What Changes

- 为 `scene-text-generation` 能力新增“记忆上下文集成”类需求：
  - 要求 scene_text_chain 接受 SceneMemoryContext 作为输入之一
  - 要求在 Prompt 中显式使用 `entity_states`、`recent_events`、`relevant_memories` 等字段
- 规范当 SceneMemoryContext 部分缺失或不可用时的降级行为，保证与当前流程向后兼容
- 明确 scene_text_chain 与前序变更：
  - `add-persistence-phase1`（持久化基础设施）
  - `add-memory-context-chain`（记忆检索链与 SceneMemoryContext 模型）
  - `validate-stage2-data-layer`（数据层查询与验证）
 之间的依赖关系

## Impact

- Affected specs:
  - `scene-text-generation`
- Affected code（预期影响范围，供实现阶段使用）：
  - `novelgen/chains/scene_text_chain.py`：
    - 链输入结构扩展以接受 SceneMemoryContext
    - Prompt 中增加基于 entity_states / recent_events / relevant_memories 的约束说明
  - `novelgen/runtime/orchestrator.py`：
    - 在调用 scene_text_chain 前，读取对应场景的 SceneMemoryContext JSON（如存在）并注入
  - `novelgen/runtime/memory_tools.py`（如有需要）：
    - 可能提供帮助函数，用于从磁盘/DB 读取指定场景的 SceneMemoryContext

- Non-goals（本提案不做的事情）：
  - 不在本阶段引入在线 function call 写作（对应阶段5）
  - 不修改 memory_context_chain 的行为，只将其输出接入 scene_text_chain
  - 不引入新的数据库或向量库实现，仅消费既有抽象层接口
