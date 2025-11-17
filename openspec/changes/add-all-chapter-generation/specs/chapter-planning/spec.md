## ADDED Requirements
### Requirement: Generate Plans for All Chapters from Outline
The system MUST support generating chapter plans for all chapters defined in the current outline without requiring the caller to manually enumerate chapter numbers.

#### Scenario: Plan all chapters by outline
- **WHEN** 用户在已存在的大纲基础上调用章节计划生成功能并指定「生成全部章节」（例如通过 special 参数或不传入章节列表）
- **THEN** 系统应从 outline.json 中读取所有章节的 `chapter_number`
- **AND** 为每个章节生成或复用章节计划（遵守 orchestration 中的 force 语义）
- **AND** 返回按章节编号升序排列的 ChapterPlan 列表
