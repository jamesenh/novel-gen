# chapter-planning Specification

## Purpose

章节计划生成模块负责将大纲中的章节摘要细化为详细的场景计划列表。每个场景定义了具体的地点、出场角色、场景目的、关键动作和预计字数，为后续的场景文本生成提供精确的蓝图。

**技术实现**：
- 使用 LangChain `ChatPromptTemplate` 构建结构化提示词
- 输出符合 `ChapterPlan` Pydantic 模型，包含 `ScenePlan` 列表
- 注入章节记忆上下文（最近 N 章的记忆条目）
- 注入章节依赖信息用于验证
- 支持批量生成多个章节的计划

**代码位置**：`novelgen/chains/chapters_plan_chain.py`

## Requirements

### Requirement: Generate Detailed Chapter Plans

The system MUST break down a chapter summary into a detailed plan containing multiple scenes, where each scene defines scene number, location, characters, purpose, key actions, and estimated word count.

#### Scenario: Plan scenes for chapter

- **WHEN** 输入 chapter_summary（标题、概要、关键事件）
- **THEN** 系统应将章节分解为 3-5 个连贯的场景
- **AND** 每个场景必须包含:
  - scene_number: 场景编号（1,2,3...）
  - location: 具体场景地点
  - characters: 出场角色名称列表
  - purpose: 场景目的（达成什么叙事目标）
  - key_actions: 关键动作列表
  - estimated_words: 预计字数（根据场景复杂度）
  - scene_type: 场景类型（日常/对话/战斗/发展/高潮/结局）
  - intensity: 强度等级（低/中/高）

#### Scenario: Ensure scene variety

- **WHEN** 生成章节计划时
- **THEN** 场景类型应多样化（避免连续多个相同类型场景）
- **AND** 场景强度应有起伏变化，形成节奏感

#### Scenario: Link scenes logically

- **WHEN** generating multiple scenes
- **THEN** scenes MUST have clear causal relationships or emotional transitions
- **AND** MUST ensure the scene sequence advances the chapter's key events and overall objectives

#### Scenario: Support batch processing

- **WHEN** a list of chapter numbers is provided for chapter plan generation
- **THEN** the system MUST batch generate plans for all specified chapters
- **AND** return a list of ChapterPlan objects

### Requirement: Generate Plans for All Chapters from Outline

The system MUST support generating chapter plans for all chapters defined in the current outline without requiring the caller to manually enumerate chapter numbers.

#### Scenario: Plan all chapters by outline

- **WHEN** 用户在已存在的大纲基础上调用章节计划生成功能并指定「生成全部章节」（例如通过 special 参数或不传入章节列表）
- **THEN** 系统应从 outline.json 中读取所有章节的 `chapter_number`
- **AND** 为每个章节生成或复用章节计划（遵守 orchestration 中的 force 语义）
- **AND** 返回按章节编号升序排列的 ChapterPlan 列表

### Requirement: Consume Chapter Memory Context

Chapter plan generation MUST consume structured chapter memory entries to ensure new plans respect resolved/ongoing plotlines.

#### Scenario: Provide memory to planning chain

- **WHEN** 调用 generate_chapter_plan()
- **THEN** 系统应传入最近 N 章的记忆（含角色状态、悬念、时间节点）及当前章所依赖的章节 ID
- **AND** 规划链必须在输出中标注如何承接/推进这些悬念（例如在 purpose 或 key_actions 中描述)

### Requirement: Validate Outline Dependencies Before Planning

Chapter planning MUST enforce per-chapter dependency constraints defined in the outline.

#### Scenario: Block planning when dependencies unmet

- **WHEN** outline.chapters[x].dependencies 中列出的章节尚未生成记忆或标记完成
- **THEN** 系统应抛出可读错误并阻止该章计划生成
- **AND** 错误消息需列出具体未满足的依赖

### Requirement: Save Chapter Plan State

The system MUST persist chapter plans for reuse and downstream consumption.

#### Scenario: Save plan to JSON file

- **WHEN** 章节计划生成成功
- **THEN** 系统 MUST 将计划保存到 `chapters/chapter_XXX_plan.json`
- **AND** 文件格式 MUST 符合 ChapterPlan Pydantic 模型

#### Scenario: Reuse existing plan when force is False

- **WHEN** 调用章节计划生成且 force=False
- **AND** 对应的 plan.json 文件已存在且可解析
- **THEN** 系统 MUST 跳过生成并返回现有计划
- **AND** 在控制台输出跳过信息
