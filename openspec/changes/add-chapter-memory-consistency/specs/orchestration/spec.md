## ADDED Requirements
### Requirement: Persist Structured Chapter Memory
The orchestrator MUST maintain a structured `chapter_memory.json` ledger that is updated after each chapter generation to capture continuity-critical facts.

#### Scenario: Append chapter memory entry
- **WHEN** step6_generate_chapter_text() 完成
- **THEN** 系统应根据本章场景摘要写入一条记忆记录，字段至少包含时间锚点、地点、主要事件、角色状态、悬念/未决目标
- **AND** 记录应附带章节编号并可供后续步骤查询最近N章

#### Scenario: Feed memory into downstream steps
- **WHEN** 执行 step5_create_chapter_plan 或 step6_generate_chapter_text
- **THEN** orchestrator MUST 注入最近N章的记忆（列表或聚合摘要）到调用链参数中
- **AND** 缺少记忆文件时应优雅回退到空列表

### Requirement: Run Automatic Consistency Check
The orchestrator MUST run a consistency verification step after each chapter is generated, leveraging accumulated chapter memory.

#### Scenario: Evaluate conflicts after generation
- **WHEN** 某章文本生成后
- **THEN** 系统应调用一致性检测链，输入章节上下文（记忆+大纲依赖）与新章节全文
- **AND** 检测结果需包含冲突列表（字段：类型、涉及角色/事件、描述）
- **AND** 一旦发现冲突，必须记录到项目目录的报告文件，供后续修订

#### Scenario: Optional auto-revision hook
- **WHEN** 检测结果标记为可自动修复级别
- **THEN** orchestrator MUST 触发 revision 链或提示用户手动处理，并在日志中回显处理状态
