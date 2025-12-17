## ADDED Requirements

### Requirement: Provide Fine-grained Tool Layer for Agent Chat

The system MUST provide a fine-grained, agent-only tool layer that enables `ng chat` to execute scoped generation and maintenance operations without relying exclusively on `workflow.run/resume`.

#### Scenario: Tool layer is agent-only (no CLI surface)

- **WHEN** 本变更交付
- **THEN** 系统 MUST 仅为对话式 Agent 注册/暴露这些新工具
- **AND** MUST NOT 新增或修改任何 CLI 命令/参数（`ng ...`）

### Requirement: Support ChapterScope for Chapter Plan Generation

The tool layer MUST provide `chapter.plan.generate` that can precisely generate chapter plans for an explicit chapter scope or explicit chapter number list.

#### Scenario: Generate plans for a chapter range only

- **WHEN** 调用 `chapter.plan.generate(chapter_scope=2..5, force=false)`
- **THEN** 系统 MUST 仅生成或复用第 2-5 章的 `chapter_XXX_plan.json`
- **AND** MUST NOT 修改范围外章节的 plan 文件

#### Scenario: Missing-only behavior

- **WHEN** 调用 `chapter.plan.generate(chapter_scope=1..3, missing_only=true)`
- **THEN** 系统 MUST 仅为缺失 plan 的章节生成新 plan
- **AND** 已存在且可解析的 plan MUST 被复用而不是覆盖

### Requirement: Support ChapterScope for Chapter Text Generation with Sequential Default

The tool layer MUST provide `chapter.text.generate` that supports explicit scope generation and enforces sequential constraints by default to avoid unsafe skip-ahead generation.

#### Scenario: Block skip-ahead by default

- **WHEN** 调用 `chapter.text.generate(chapter_numbers=[5], sequential=true)`
- **AND** 第 1-4 章正文缺失
- **THEN** 工具 MUST 不生成第 5 章正文
- **AND** MUST 返回结构化阻塞信息（例如 `blocked_by_missing=[1,2,3,4]`）

#### Scenario: Generate a consecutive range

- **WHEN** 调用 `chapter.text.generate(chapter_scope=2..4, sequential=true)`
- **AND** 第 1 章已存在
- **THEN** 工具 MUST 按 2→3→4 顺序生成或复用章节正文

### Requirement: Enforce No Silent Scope Expansion

Tools that accept `ChapterScope` MUST NOT silently broaden execution beyond the requested scope.

#### Scenario: Refuse to broaden scope

- **WHEN** 调用方请求 `chapter.plan.generate(chapter_scope=1..3)`
- **THEN** 工具 MUST NOT 自动把 scope 扩张为 “全部章节”
- **AND** 若无法执行该 scope（例如缺失大纲），必须返回缺失前置而不是扩张范围

### Requirement: Provide Settings and Outline Tools for Chapter Count Control

The tool layer MUST provide minimal settings/outline tools to allow the agent to align “计划章节数量”与“实际生成范围”。

#### Scenario: Update max chapters for controlled generation

- **WHEN** 用户在对话中要求“只写到 12 章”
- **THEN** Agent SHOULD 能通过 `settings.update({max_chapters: 12})`（或等价 patch）实现上限控制
- **AND** 变更 MUST 持久化到 `settings.json`

