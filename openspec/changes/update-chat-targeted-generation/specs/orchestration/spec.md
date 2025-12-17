## ADDED Requirements

### Requirement: Support stop_at Execution for Partial Workflow Runs

The orchestration layer MUST support stopping a workflow run at a specified node name (`stop_at`) to enable partial execution for interactive and tool-driven use cases.

#### Scenario: Stop workflow after reaching stop_at node

- **WHEN** 调用编排器运行工作流并指定 `stop_at="character_creation"`
- **THEN** 系统 MUST 按照依赖顺序执行到 `character_creation`（包含必要前置或跳过已完成步骤）
- **AND** 在 `character_creation` 执行完成后 MUST 立即停止并返回当前状态
- **AND** MUST NOT 继续执行后续节点（如 `outline_creation`、章节生成等）

