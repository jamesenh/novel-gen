## ADDED Requirements
### Requirement: Parameterized Chapter Scope for Planning and Text Generation
The orchestrator MUST expose a consistent, parameter-driven API to control which chapters are planned and generated at step5/step6.

#### Scenario: Generate all chapters by default
- **WHEN** 用户直接调用 `generate_all_chapters()` 且未显式限制章节范围
- **THEN** orchestrator MUST 读取 outline.json 中的全部章节编号
- **AND** 对每一章依次执行 `step5_create_chapter_plan` 与 `step6_generate_chapter_text`

#### Scenario: Generate subset of chapters by argument
- **WHEN** 用户调用章节相关 API 并传入特定的章节编号列表（例如 `step5_create_chapter_plan([1,2,3])` 或 `generate_all_chapters(chapter_numbers=[1,2,3])`）
- **THEN** orchestrator MUST 仅为这些章节执行章节计划与章节正文生成
- **AND** 其他章节 MUST 不被修改
