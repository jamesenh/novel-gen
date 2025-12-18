# Persistence Spec

## Purpose

定义生成/修订过程中项目资产的标准落盘路径、写入时序与同步更新要求，避免正文、记忆与一致性报告之间发生漂移，并统一 UTF-8 编码约定。

## Requirements

### Requirement: Artifact Layout
The system SHALL persist generated artifacts under `projects/<project>/` using the repository's standard asset layout (e.g., `world.json`, `characters.json`, `outline.json`, `chapters/`, `consistency_reports.json`, `chapter_memory.json`).

#### Scenario: Chapter artifacts are written to standard paths
- **WHEN** the workflow completes a chapter generation or revision cycle
- **THEN** the system writes/updates the corresponding files in `projects/<project>/...`

### Requirement: Synchronized Writes for Content Changes
When chapter text or core setting changes (world/characters/timeline/threads), the system SHALL synchronously update the corresponding memory and consistency report assets to avoid drift.

#### Scenario: Text change forces memory/report sync
- **WHEN** `chapters/chapter_XXX.json` is modified by a revision cycle
- **THEN** `projects/<project>/chapter_memory.json` is updated
- **AND THEN** `projects/<project>/consistency_reports.json` is updated
- **AND THEN** if `projects/<project>/data/novel.db` exists, corresponding `memory_chunks` and/or `entity_snapshots` are updated OR the DB is explicitly marked stale in a machine-readable way so it is not used for retrieval

### Requirement: UTF-8 Encoding
The system SHALL write all text and JSON assets in UTF-8 encoding.

#### Scenario: No double-encoding corruption
- **WHEN** the system writes any JSON/text asset
- **THEN** the persisted bytes decode as valid UTF-8 without mojibake
