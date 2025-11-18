## ADDED Requirements
### Requirement: Consume Chapter Memory Context
Chapter plan generation MUST consume structured chapter memory entries to ensure new plans respect resolved/ongoing plotlines.

#### Scenario: Provide memory to planning chain
- **WHEN** 调用 generate_chapter_plan()
- **THEN** 系统应传入最近N章的记忆（含角色状态、悬念、时间节点）及当前章所依赖的章节ID
- **AND** 规划链必须在输出中标注如何承接/推进这些悬念（例如在purpose或key_actions中描述)

### Requirement: Validate Outline Dependencies Before Planning
Chapter planning MUST enforce per-chapter dependency constraints defined in the outline.

#### Scenario: Block planning when dependencies unmet
- **WHEN** outline.chapters[x].dependencies 中列出的章节尚未生成记忆或标记完成
- **THEN** 系统应抛出可读错误并阻止该章计划生成
- **AND** 错误消息需列出具体未满足的依赖
