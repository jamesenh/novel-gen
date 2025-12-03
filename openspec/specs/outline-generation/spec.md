# outline-generation Specification

## Purpose

大纲生成模块负责根据世界观设定、主题冲突和角色配置，构建完整的故事大纲。大纲包括故事前提、五幕结构（开端、发展、高潮、结局）和详细的章节摘要列表，为后续章节规划和场景生成提供蓝图。

**技术实现**：
- 使用 LangChain `ChatPromptTemplate` 构建结构化提示词
- 输出符合 `Outline` Pydantic 模型，包含 `ChapterSummary` 列表
- 支持动态章节扩展模式（`is_complete` 和 `current_phase` 字段）
- 每个章节包含 `timeline_anchor` 和 `dependencies` 元数据
- 支持 `initial_chapters` 和 `max_chapters` 配置控制章节数量

**代码位置**：`novelgen/chains/outline_chain.py`

## Requirements

### Requirement: Generate Structured Story Outline

The system MUST generate a structured story outline including story premise, five-act structure (beginning, development, climax, resolution), and chapter list based on the world setting, theme conflict, and character configuration.

#### Scenario: Define story premise

- **WHEN** 生成大纲时
- **THEN** 系统应总结故事前提，清晰阐述"这是一个关于什么的故事"
- **AND** 前提应体现世界观和主题冲突的核心元素

#### Scenario: Build five-act structure

- **WHEN** 生成大纲结构
- **THEN** 必须包含并用 1-2 段描述:
  - beginning: 故事开端（引入世界、人物、初始冲突）
  - development: 发展过程（冲突升级、人物成长、关系演变）
  - climax: 高潮（冲突顶点、重大转折、决定性时刻）
  - resolution: 结局（冲突解决、人物归宿、世界变化）

#### Scenario: Plan chapter sequence

- **WHEN** 用户指定章节数量 num_chapters（默认 20 章）
  - 应适配不同长度需求（短篇 10 章，中篇 20 章，长篇 50 章等）
- **THEN** 系统应生成对应数量的章节摘要列表
- **AND** 每个章节包含:
  - chapter_number: 章节序号
  - chapter_title: 章节标题
  - summary: 章节概要（本章节发生的主要事件）
  - key_events: 关键事件列表（推动剧情的重要节点）

#### Scenario: Maintain pacing and progression

- **WHEN** planning the chapter sequence
- **THEN** chapter content MUST reflect reasonable pacing (alternating tension and relaxation)
- **AND** MUST ensure plot progression from beginning → development → climax → resolution

### Requirement: Capture Timeline Anchors and Dependencies

Outline generation MUST enrich each chapter summary with timeline and dependency metadata for downstream validation.

#### Scenario: Emit timeline_anchor per chapter

- **WHEN** 构建 chapter_summary
- **THEN** 输出需包含 timeline_anchor 字段（相对或绝对时间节点），用于表明章内事件在全局时间线中的位置

#### Scenario: Emit dependencies list per chapter

- **WHEN** 章节事件依赖早期章节的结果或特定事件
- **THEN** 应在 dependencies 字段列出依赖的 chapter_number 或事件 ID，以及依赖类型（如"林玄回到宗门"）
- **AND** 无依赖时可输出空数组但字段必须存在

### Requirement: Validate timeline and dependency consistency

Outline generation MUST ensure timeline anchors progress logically and dependencies refer to valid chapters.

#### Scenario: Timeline monotonicity

- **WHEN** 生成全书大纲
- **THEN** 系统应检查 timeline_anchor 是否遵循整体顺序（允许适当闪回但须在字段中标注），否则抛出说明错误

#### Scenario: Dependency referencing

- **WHEN** dependencies 中引用某章节
- **THEN** 必须验证该章存在且发生在时间线上早于当前章，若不满足需报错或重新生成

### Requirement: Support Dynamic Chapter Extension

The system MUST support dynamic chapter extension mode for stories that grow organically based on plot development.

#### Scenario: Initialize outline in dynamic mode

- **WHEN** 使用动态章节模式（Settings.initial_chapters 设置）
- **THEN** 系统 MUST 生成初始章节数量（initial_chapters）的大纲
- **AND** Outline.is_complete MUST 设置为 False
- **AND** Outline.current_phase MUST 设置为 "opening"

#### Scenario: Track story phase progression

- **WHEN** 大纲中的 current_phase 字段被更新
- **THEN** 系统 MUST 支持以下阶段值：
  - "opening": 开篇阶段
  - "development": 发展阶段
  - "climax": 高潮阶段
  - "resolution": 收尾阶段
  - "complete": 已完成

#### Scenario: Support outline extension

- **WHEN** 所有已规划章节生成完毕且 is_complete 为 False
- **THEN** 系统 SHOULD 通过剧情进度评估决定是否扩展大纲
- **AND** 扩展时 MUST 追加新的 ChapterSummary 到 chapters 列表
- **AND** MUST 更新 current_phase 以反映故事进展

### Requirement: Respect Maximum Chapter Limit

The system MUST enforce maximum chapter limits to prevent infinite story generation.

#### Scenario: Enforce max_chapters constraint

- **WHEN** 动态扩展大纲时
- **THEN** 系统 MUST 检查当前章节数是否已达到 Settings.max_chapters
- **AND** 达到限制时 MUST 强制进入收尾阶段
- **AND** 生成的结局章节 MUST 合理收束所有主线和支线
