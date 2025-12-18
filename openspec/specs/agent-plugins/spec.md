# Agent Plugins Spec

## Purpose

定义审计/一致性插件在工作流中的输入输出契约、只读边界与结构化问题输出格式，确保插件可组合、可测试且不会直接改写项目资产。
## Requirements
### Requirement: Plugin Read-Only Boundary
Agent plugins SHALL be pure analysis components: they MUST NOT directly write to `projects/` artifacts or databases.

#### Scenario: Plugin produces issues only
- **WHEN** a plugin is invoked during audit
- **THEN** it returns a structured `issues` payload
- **AND THEN** it performs no direct filesystem or database writes

### Requirement: Plugin Input Contract
系统 SHALL 向插件提供稳定的输入契约，包含当前 `State` 与 `context_pack`（必带上下文 + 可选检索结果），以便插件能产出可追溯的 evidence。

#### Scenario: 插件收到章节的 context pack
- **WHEN** 工作流进入 `chapter_id = N` 的审计步骤
- **THEN** 插件获得当前章节草稿与相关的 bible/outline 上下文
- **AND THEN** 插件获得包含可追溯来源的 `context_pack.retrieved[]`（至少含 `source_path` 与 `source_id`），以便 evidence 可引用来源

### Requirement: Plugin Output Contract
Plugins SHALL output structured issues including `severity`, `category`, and actionable fix guidance, sufficient for an automated minimal-change patcher to act.

#### Scenario: Blocker issue includes fix instructions
- **WHEN** a plugin detects a blocker-level inconsistency
- **THEN** the issue includes actionable `fix_instructions` describing the minimal change needed
- **AND THEN** the issue includes `evidence` referencing the chapter text and/or bible/outline sources

#### Scenario: Issues carry stable, filterable fields
- **WHEN** a plugin emits any issue
- **THEN** the issue includes `severity` and `category` for filtering and routing
- **AND THEN** the issue includes a human-readable `summary` (or `description`)

### Requirement: Context Pack 字段稳定且可追溯
系统 SHALL 向插件与生成节点提供 schema 稳定的 `context_pack`；其中 `retrieved[]` 条目至少包含 `source_path` 与 `source_id`，且可追溯到具体项目资产。

#### Scenario: context pack 条目字段稳定
- **WHEN** 系统从任意项目资产构建一个 context pack 条目
- **THEN** 该条目包含 `source_path` 与 `source_id`
- **AND THEN** 系统能够将该条目追溯回具体的项目文件与定位信息

