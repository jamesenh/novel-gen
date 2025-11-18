## ADDED Requirements
### Requirement: Derive Previous Summary from Generated Scenes
Scene generation MUST use actual summaries of the immediately preceding scene instead of static plan descriptions.

#### Scenario: Summarize prior scene output
- **WHEN** 生成第k个场景（k>1）
- **THEN** 系统应先对第k-1场景文本运行摘要链并将结果作为previous_summary
- **AND** 场景1缺乏前置内容时，previous_summary必须反映“本章开篇”而非空字符串

### Requirement: Provide Multi-Chapter Context
Scene generation MUST ingest a `chapter_context` payload that aggregates the latest N chapter summaries plus state diffs.

#### Scenario: Include chapter_context in prompt
- **WHEN** 调用scene_text_chain
- **THEN** prompt输入应包含chapter_context字段，内容含最近N章的概述、关键角色状态变化、未解决悬念
- **AND** 系统指令需明确“生成文本不得与chapter_context中的事实冲突，若必须引入新设定须解释合理原因”
