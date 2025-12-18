## ADDED Requirements

### Requirement: Plugin Read-Only Boundary
Agent plugins SHALL be pure analysis components: they MUST NOT directly write to `projects/` artifacts or databases.

#### Scenario: Plugin produces issues only
- **WHEN** a plugin is invoked during audit
- **THEN** it returns a structured `issues` payload
- **AND THEN** it performs no direct filesystem or database writes

### Requirement: Plugin Input Contract
The system SHALL provide plugins with a stable input contract including the current `State` and an optional context pack (retrieval results, bible extracts, prior issues).

#### Scenario: Plugin receives chapter context
- **WHEN** the workflow reaches an audit step for `chapter_id = N`
- **THEN** the plugin receives the current chapter draft and relevant bible/outline context

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
