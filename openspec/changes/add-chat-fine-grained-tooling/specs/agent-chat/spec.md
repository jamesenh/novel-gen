## ADDED Requirements

### Requirement: Prefer Fine-grained Tools for Scoped Chapter Requests

When a natural language request includes a parsed `ChapterScope` and targets chapter plan/text generation, the chat agent MUST prefer fine-grained tooling to execute the scope precisely, instead of falling back to full workflow execution or “constraint-aware downgrade”.

#### Scenario: Scoped chapter planning executes precisely

- **WHEN** 用户输入 “生成第2-5章的章节计划”
- **AND** 系统成功解析章节范围为 `chapters=2..5`
- **THEN** Agent MUST 生成并执行 ToolPlan，调用 `chapter.plan.generate(chapter_scope=2..5, ...)`
- **AND** MUST 回显将要执行的范围与副作用（将落盘哪些文件）

#### Scenario: Scoped chapter text respects sequential constraint

- **WHEN** 用户输入 “生成第5章正文”
- **AND** 系统解析章节约束为 `chapters=[5]`
- **THEN** Agent MUST 调用 `chapter.text.generate(chapter_numbers=[5], sequential=true, ...)`
- **AND** 若工具返回被阻塞（缺失 1..4），Agent MUST 提示用户选择“顺序补齐到第5章/取消”

