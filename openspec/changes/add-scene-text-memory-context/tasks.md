## 1. 规范与设计
- [x] 1.1 通读 `scene-text-generation` 现有 spec 与以下变更：`add-persistence-phase1`、`add-memory-context-chain`、`validate-stage2-data-layer`，确认边界
- [x] 1.2 在设计层面敲定 scene_text_chain 输入中如何携带 SceneMemoryContext（直接对象 vs 从 JSON 读取）以及 Prompt 结构

## 2. 实现集成（scene_text_chain + orchestrator）
- [x] 2.1 扩展 scene_text_chain 输入模型：支持接收 SceneMemoryContext（或其路径），保持与现有调用向后兼容
- [x] 2.2 在 `NovelOrchestrator` 中接入阶段3产出的 `scene_<chapter>_<scene>_memory.json`：
  - [x] 2.2.1 在生成场景文本前尝试读取对应 SceneMemoryContext JSON
  - [x] 2.2.2 将解析后的 SceneMemoryContext 传入 scene_text_chain
- [x] 2.3 更新 scene_text_chain Prompt：
  - [x] 2.3.1 在系统指令中明确：人物/实体状态必须服从 SceneMemoryContext.entity_states
  - [x] 2.3.2 在上下文中纳入 recent_events 与 relevant_memories 的精简版本
  - [x] 2.3.3 在 Prompt 中对“当记忆缺失时如何写作”的行为做出指引
- [x] 2.4 确保在关闭持久化或缺失 SceneMemoryContext 时，scene_text_chain 能优雅降级为仅依赖 previous_summary + chapter_context

## 3. 测试与验证
- [x] 3.1 为 scene_text_chain 构造单元测试/集成测试用例：
  - [x] 3.1.1 有完整 SceneMemoryContext 时，Prompt 构造正确且不丢字段
  - [x] 3.1.2 SceneMemoryContext 部分字段缺失时，链仍能工作且行为符合降级规范
- [ ] 3.2 复用/扩展 `test_consistency_check.py` 和相关测试，用一到两个 demo 项目对比：
  - [ ] 3.2.1 无记忆上下文时的一致性基线
  - [ ] 3.2.2 接入 SceneMemoryContext 后，一致性明显改善（至少在角色状态与关键承诺上）
- [x] 3.3 运行 `openspec validate add-scene-text-memory-context --strict` 并修正所有校验问题
