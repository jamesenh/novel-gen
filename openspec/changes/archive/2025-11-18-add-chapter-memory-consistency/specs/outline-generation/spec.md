## ADDED Requirements
### Requirement: Capture Timeline Anchors and Dependencies
Outline generation MUST enrich each chapter summary with timeline and dependency metadata for downstream validation.

#### Scenario: Emit timeline_anchor per chapter
- **WHEN** 构建chapter_summary
- **THEN** 输出需包含timeline_anchor字段（相对或绝对时间节点），用于表明章内事件在全局时间线中的位置

#### Scenario: Emit dependencies list per chapter
- **WHEN** 章节事件依赖早期章节的结果或特定事件
- **THEN** 应在dependencies字段列出依赖的chapter_number或事件ID，以及依赖类型（如“林玄回到宗门”）
- **AND** 无依赖时可输出空数组但字段必须存在

### Requirement: Validate timeline and dependency consistency
Outline generation MUST ensure timeline anchors progress logically and dependencies refer to valid chapters.

#### Scenario: Timeline monotonicity
- **WHEN** 生成全书大纲
- **THEN** 系统应检查timeline_anchor是否遵循整体顺序（允许适当闪回但须在字段中标注），否则抛出说明错误

#### Scenario: Dependency referencing
- **WHEN** dependencies中引用某章节
- **THEN** 必须验证该章存在且发生在时间线上早于当前章，若不满足需报错或重新生成
