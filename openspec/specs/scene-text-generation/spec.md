# scene-text-generation Specification

## Purpose

场景文本生成模块负责根据场景计划、世界观设定和角色配置，生成高质量的中文小说场景文本。该模块是小说生成流程中产出实际内容的核心环节，需要综合运用前文上下文、章节记忆和场景记忆来确保内容的连贯性和一致性。

**技术实现**：
- 优先使用 LangChain 的 `with_structured_output()` 模式
- 退回到 `PydanticOutputParser` + `LLMJsonRepairOutputParser` 作为 fallback
- 注入 `SceneMemoryContext`（实体状态 + 相关记忆片段）
- 注入用户写作偏好（从 Mem0 检索）
- 支持场景级别的断点续跑（通过 LangGraph 子工作流）
- 字数控制在目标的 ±20% 范围内

**代码位置**：`novelgen/chains/scene_text_chain.py`

## Requirements

### Requirement: Generate Novel Text from Scene Plans

The system MUST generate high-quality novel scene text based on scene plans, world setting, and character configuration, providing previous scene context for improved coherence.

#### Scenario: Write scene narrative

- **WHEN** 提供 scene_plan（类型、强度、地点、角色、目的）
- **THEN** 系统应生成完整的中文小说场景文本
- **AND** 输出必须满足:
  - 字数严格控制在 estimated_words 上下浮动 20% 以内
  - 符合 scene_type 指定的类型（日常/对话/战斗等）风格
  - 体现 intensity 对应的紧张程度
  - 出场角色符合 character 配置的性格与能力

#### Scenario: Maintain coherence with previous content

- **WHEN** 提供 previous_summary 参数（前文概要）
- **THEN** 生成文本应与前文保持连贯性
- **AND** 人物状态、情节发展应与之前内容衔接自然

#### Scenario: Apply world rules and lore

- **WHEN** the world setting defines special rules (e.g., cultivation system, magic system)
- **THEN** the scene text MUST strictly adhere to these settings
- **AND** character behavior MUST reflect ability limitations and social norms in the world setting

#### Scenario: Enforce word count limits

- **WHEN** scene_plan specifies estimated_words as 2000 words
- **THEN** the generated scene.word_count MUST be within 1800-2200 words (±10%)
- **AND** generations that are too short or too long SHOULD be flagged

#### Scenario: Return structured scene data

- **WHEN** 场景文本生成完成
- **THEN** 应返回 GeneratedScene 对象包含:
  - scene_number: 场景编号
  - content: 场景正文（字符串）
  - word_count: 实际计算的字数（整数）

### Requirement: Derive Previous Summary from Generated Scenes

Scene generation MUST use actual summaries of the immediately preceding scene instead of static plan descriptions.

#### Scenario: Summarize prior scene output

- **WHEN** 生成第 k 个场景（k>1）
- **THEN** 系统应先对第 k-1 场景文本运行摘要链并将结果作为 previous_summary
- **AND** 场景 1 缺乏前置内容时，previous_summary 必须反映"本章开篇"而非空字符串

### Requirement: Provide Multi-Chapter Context

Scene generation MUST ingest a `chapter_context` payload that aggregates the latest N chapter summaries plus state diffs.

#### Scenario: Include chapter_context in prompt

- **WHEN** 调用 scene_text_chain
- **THEN** prompt 输入应包含 chapter_context 字段，内容含最近 N 章的概述、关键角色状态变化、未解决悬念
- **AND** 系统指令需明确"生成文本不得与 chapter_context 中的事实冲突，若必须引入新设定须解释合理原因"

### Requirement: Consume Scene Memory Context

Scene generation MUST consume structured scene memory context from Mem0 for enhanced consistency.

#### Scenario: Inject SceneMemoryContext into prompt

- **WHEN** 场景生成时提供了 SceneMemoryContext
- **THEN** 系统 MUST 将以下信息注入提示词：
  - entity_states: 相关角色的当前状态（从 Mem0 检索）
  - relevant_memories: 与场景相关的记忆片段（基于场景目的语义搜索）
- **AND** 生成的文本 MUST 不得与实体状态中的事实冲突

#### Scenario: Handle missing memory context gracefully

- **WHEN** SceneMemoryContext 为 None 或检索失败
- **THEN** 系统 SHOULD 优雅降级，使用 "null" 作为占位
- **AND** 不应阻止场景生成流程

### Requirement: Inject User Writing Preferences

Scene generation SHOULD consume user writing preferences from Mem0 to personalize output style.

#### Scenario: Search and inject preferences

- **WHEN** 场景生成开始
- **THEN** 系统 SHOULD 从 Mem0 检索用户写作偏好（查询 "写作风格和偏好"）
- **AND** 将检索到的偏好以结构化格式附加到 chapter_context

#### Scenario: Apply preferences to generation

- **WHEN** 用户偏好包含特定风格要求（如"多使用心理描写"、"避免过多对话"）
- **THEN** 生成的场景文本 SHOULD 反映这些偏好
- **AND** 偏好不应覆盖场景计划的核心要求

### Requirement: Save Scene Content to Memory

Scene generation MUST persist generated content to Mem0 for future context retrieval.

#### Scenario: Store scene in Mem0

- **WHEN** 场景文本成功生成
- **THEN** 系统 MUST 将场景内容保存到 Mem0
- **AND** 保存时 MUST 包含 chapter_index 和 scene_index 元数据

#### Scenario: Save individual scene files

- **WHEN** 场景生成完成（在子工作流中）
- **THEN** 系统 SHOULD 保存单独的场景文件 `scene_XXX_YYY.json`
- **AND** 这支持场景级别的断点续跑
