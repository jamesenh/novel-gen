## ADDED Requirements

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
