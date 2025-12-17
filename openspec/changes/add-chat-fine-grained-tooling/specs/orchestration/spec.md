## ADDED Requirements

### Requirement: Expose Chapter-scoped Generation Primitives for Agent Tooling

The orchestration/runtime layer MUST expose reusable primitives that allow generating chapter plans and chapter text for an explicit chapter scope or list, without forcing the caller to run the full LangGraph workflow.

#### Scenario: Plan only specified chapters without running full workflow

- **WHEN** agent-tooling 调用“章节计划范围生成”原语并指定章节列表 `[2,3,4]`
- **THEN** 系统 MUST 仅为这些章节生成/复用计划并落盘
- **AND** MUST NOT 触发对范围外章节的生成

#### Scenario: Generate text for specified chapters with sequential safeguard

- **WHEN** agent-tooling 调用“章节正文范围生成”原语请求章节 `[5]` 且默认顺序保护开启
- **AND** 发现 1..4 正文缺失
- **THEN** 系统 MUST 返回阻塞信息并停止执行
- **AND** MUST NOT 生成第 5 章正文

