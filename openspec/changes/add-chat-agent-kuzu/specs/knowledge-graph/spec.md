## ADDED Requirements

### Requirement: Provide Embedded Kùzu Knowledge Graph Per Project

The system MUST provide an embedded Kùzu graph database per project for structured retrieval of characters, relationships, chapters, and events.

#### Scenario: Initialize per-project graph store

- **WHEN** 系统在项目 `projects/<project_id>/` 下初始化图谱层
- **THEN** 系统 MUST 在 `projects/<project_id>/data/graph/` 创建并使用 Kùzu 数据目录
- **AND** 图谱初始化 MUST 幂等（重复初始化不会破坏现有数据）

### Requirement: Rebuild Graph from JSON Sources

The system MUST provide a rebuild operation to reconstruct the graph from JSON sources (characters.json and chapter_memory.json) to address drift or corruption.

#### Scenario: Rebuild graph idempotently

- **WHEN** 用户运行 `ng graph rebuild <project_id>`
- **THEN** 系统 MUST 从 `characters.json` 初始化 Character 节点与基础关系
- **AND** 系统 MUST 从 `chapter_memory.json` 写入 Chapter/Event/参与关系
- **AND** 若某些 JSON 文件不存在，系统 MUST 优雅降级并给出提示（不应崩溃）

### Requirement: Update Graph After Chapter Memory Is Written

The system MUST update the knowledge graph after a chapter memory entry has been persisted successfully.

#### Scenario: Incremental chapter update

- **WHEN** 第 N 章生成完成且 `chapter_memory.json` 成功写入新增条目
- **THEN** 系统 MUST 将该章节对应的 Chapter/Event/参与关系增量写入 Kùzu
- **AND** 每条写入 MUST 带 evidence_ref（至少包含 chapter_number/source/snippet）
- **AND** 若图谱写入失败，系统 MUST 记录警告并继续主流程（不阻断章节生成）

#### Scenario: Deterministic mapping from ChapterMemoryEntry to Event + evidence_ref

- **WHEN** 系统基于 `chapter_memory.json` 的单条 `ChapterMemoryEntry` 写入图谱
- **THEN** 系统 MUST 将 `key_events` 中的每个条目视为一个 Event
- **AND** Event MUST 具备稳定的 event_id（例如 `ch{chapter_number}_e{index}`）
- **AND** evidence_ref MUST 至少包含：
  - chapter_number: 章节号
  - source: `"chapter_memory.key_events[{index}]"`
  - snippet: 对应的 key_events 文本
- **AND** 系统 MAY 基于 `characters.json` 的角色名进行字符串匹配来建立参与关系（未匹配到时允许不创建参与边）

### Requirement: Provide Graph Query Interfaces for Character Retrieval

The system MUST provide query interfaces to retrieve character profiles, relationships, and chapter-scoped events, returning evidence references.

#### Scenario: Query relations for a character

- **WHEN** 用户查询 “A 与 B 的关系是什么？证据在哪？”
- **THEN** 系统 MUST 返回关系类型/描述
- **AND** MUST 返回 evidence_ref（章号与引用片段）

#### Scenario: Query relation between two specific characters (pair query)

- **WHEN** 用户提供 A 与 B 两个明确角色（例如 `ng graph relations <project> A --with B` 或等效接口）
- **THEN** 系统 MUST 优先返回 A↔B 之间的直接关系与证据引用
- **AND** 若不存在直接关系，系统 MUST 明确返回“未找到直接关系”而不是给出猜测


