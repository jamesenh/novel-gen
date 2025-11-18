## ADDED Requirements
### Requirement: Force-controlled Chapter Text Generation
The orchestrator MUST support force-controlled reuse and regeneration behavior specifically for step6 chapter text generation.

#### Scenario: Reuse existing chapter text when force is False
- **WHEN** 调用 `step6_generate_chapter_text(chapter_number, force=False)`
- **AND** projects/{project_name}/chapters 目录下存在对应的 `chapter_{chapter_number:03d}.json` 文件且能被 GeneratedChapter 模型解析
- **THEN** orchestrator MUST 直接复用该章节对象，跳过场景级 LLM 生成调用
- **AND** 在控制台输出说明已复用的提示（包含章节编号和文件路径）

#### Scenario: Force regenerate chapter text when force is True
- **WHEN** 调用 `step6_generate_chapter_text(chapter_number, force=True)`
- **AND** 无论 `chapter_{chapter_number:03d}.json` 是否存在
- **THEN** orchestrator MUST 忽略现有文件，重新生成本章所有场景文本并覆盖写入
- **AND** 在控制台输出“强制重算”的提示

#### Scenario: Apply force semantics in batch chapter generation
- **WHEN** 调用 `generate_all_chapters(force=False)`（或等效批量生成入口）
- **AND** 某些章节的 `chapter_{chapter_number:03d}.json` 已存在且可解析
- **THEN** orchestrator MUST 对这些章节复用现有文本，仅为缺失章节调用 step6 生成
- **AND** 当 `force=True` 时，系统 MUST 为所有章节重新生成文本并覆盖旧文件
