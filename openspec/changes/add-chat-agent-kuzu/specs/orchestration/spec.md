## ADDED Requirements

### Requirement: Update Knowledge Graph After Chapter Completion

The orchestration system MUST update the embedded knowledge graph layer after each chapter is generated and its chapter memory entry is persisted.

#### Scenario: Trigger graph update after chapter_memory write

- **WHEN** 某章生成完成并写入 `chapter_memory.json`
- **THEN** 编排器 MUST 调用 GraphUpdater 将该章的结构化信息写入 Kùzu
- **AND** 若图谱层不可用或写入失败，编排器 MUST 记录警告并继续后续流程（不阻断生成）


