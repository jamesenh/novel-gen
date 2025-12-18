# Validation Spec

## Purpose

定义结构化产物在写入项目前的 schema 校验要求、必备元数据字段与可操作的错误输出格式，用于在工作流中提供可追踪、可恢复的验证门禁。
## Requirements
### Requirement: Schema Validation Before Persistence
The system SHALL validate all structured artifacts against schemas before writing them under `projects/<project>/`.

#### Scenario: Invalid artifact is not persisted
- **WHEN** a node produces an invalid `chapter_plan` artifact (schema mismatch)
- **THEN** the system fails the step and does not write the invalid file

### Requirement: Required Metadata Fields
Structured JSON artifacts SHALL include `schema_version`, `generated_at`, and `generator` fields to support traceability and future versioning.

#### Scenario: Chapter plan carries metadata
- **WHEN** the system writes `chapters/chapter_XXX_plan.json`
- **THEN** it includes `schema_version`, `generated_at`, and `generator`

### Requirement: Validation Errors Are Actionable
The system SHALL surface validation failures as structured errors suitable for debugging and recovery.

#### Scenario: Validation failure reports path and reason
- **WHEN** schema validation fails
- **THEN** the system reports the failing field path and the reason for failure

### Requirement: Context Pack 写入/调用前校验
系统 SHALL 在将 `context_pack` 传递给插件或生成器之前，对其进行 schema 校验。

#### Scenario: 无效 context pack 会被拒绝
- **WHEN** 系统构建了一个无效的 `context_pack`（schema 不匹配）
- **THEN** 系统以可定位的错误失败（包含字段路径与原因）
- **AND THEN** 系统不会携带该无效 context pack 去调用插件

### Requirement: 生成链路输出写盘前校验
系统 SHALL 在将 planner/writer/patcher 的输出落盘到 `projects/<project>/` 之前，对其进行 schema 校验。

#### Scenario: writer 输出无效则不写盘
- **WHEN** writer 产出无效的 `chapter_draft`
- **THEN** 系统失败该步骤，且不会写入无效的章节资产

### Requirement: 背景资产写盘前校验
系统 SHALL 在将生成的背景资产（`world.json`、`characters.json`、`theme_conflict.json`）以及 `outline.json` 落盘到 `projects/<project>/` 之前，对其进行 schema 校验。

#### Scenario: 无效的 world.json 不会被写盘
- **WHEN** 系统生成了无效的 `world.json`（schema 不匹配）
- **THEN** 系统以可定位的错误失败（包含字段路径与原因）
- **AND THEN** 系统不会将该无效背景资产写入磁盘

