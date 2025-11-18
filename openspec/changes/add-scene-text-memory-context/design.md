## Context

阶段1–3已经提供：
- 数据持久化基础设施（数据库 + 向量库抽象层，见 `persistence` capability）
- 记忆检索链 `memory_context_chain`，输出 `SceneMemoryContext` 并落盘到 `projects/<id>/scene_<chapter>_<scene>_memory.json`
- 只读查询与验证工具（阶段2），确认数据模型与查询接口可用

当前 scene_text_chain：
- 只消费 ScenePlan、world/characters 配置、previous_summary、chapter_context
- 尚未对 SceneMemoryContext 有任何规范级依赖

## Goals / Non-Goals

- Goals:
  - 让 scene_text_chain 在规范上“必须”消费 SceneMemoryContext（如存在）
  - 定义如何在 Prompt 中使用 entity_states / recent_events / relevant_memories 保证一致性
  - 给出缺失记忆时的降级策略，避免破坏现有流程
- Non-Goals:
  - 不引入新的 agent / function call 写作流程（对应阶段5）
  - 不改变 memory_context_chain 的输入输出契约
  - 不新增数据库表或向量库集合

## Decisions

- Decision: 通过 orchestrator 读取 SceneMemoryContext JSON 并注入 scene_text_chain，而不是在 scene_text_chain 内部直接访问 DB/向量库。
  - Rationale: 保持链无状态、只依赖 JSON 输入，符合项目“LangChain 不直接操作数据库”的原则。

- Decision: 在 Prompt 中使用“结构化小节 + 精简列表”的方式呈现记忆：
  - entity_states：按实体分组，突出与当前场景强相关的状态字段
  - recent_events：按时间顺序列出最近若干关键事件
  - relevant_memories：选取 top-K 片段并做极简摘要，避免 token 爆炸

- Decision: 缺失 SceneMemoryContext 时完全退回现有行为，仅通过 previous_summary + chapter_context 保证连贯性。

## Risks / Trade-offs

- Risk: Prompt 过长导致 token 压力增大。
  - Mitigation: 在实现阶段限制每类记忆条目数量（如每类 <= 5），并在 Python 端先做裁剪/摘要。

- Risk: 场景中引入的新状态与 SceneMemoryContext 冲突。
  - Mitigation: 在 Prompt 中明确“不得与给定 entity_states 冲突，如需改变状态必须在剧情中给出合理过程”。

## Migration Plan

1. 在不开启持久化/记忆链的项目上，先按现有方式运行，确认基线行为。
2. 在启用持久化 + memory_context_chain 的 demo 项目上：
   - 先运行到阶段3，生成 SceneMemoryContext JSON
   - 再切换到接入记忆上下文的 scene_text_chain 实现
3. 如发现严重问题，可通过配置开关暂时禁用 SceneMemoryContext 注入，退回原有行为。

## Open Questions

- 是否需要为 Prompt 中的记忆部分单独设计模板（如按“硬约束 vs 软线索”分组），还是直接复用现有 consistency check 中的结构？
- token 预算与章节长度之间的权衡是否需要额外的配置项（例如 memory_max_items / memory_max_tokens）？
