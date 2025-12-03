# character-generation Specification

## Purpose

角色生成模块负责基于世界观设定和主题冲突，设计具有深度的主角、反派和配角角色。该模块创建完整的角色网络，包括动机、背景和关系，以支撑长篇叙事需求。

**技术实现**：
- 优先使用 LangChain 的 `with_structured_output()` 模式（如果后端模型支持）
- 退回到 `PydanticOutputParser` + `LLMJsonRepairOutputParser` 作为 fallback
- 生成的角色自动初始化到 Mem0 Agent Memory
- 支持 `verbose` 模式和链级别配置覆盖

**代码位置**：`novelgen/chains/characters_chain.py`

## Requirements

### Requirement: Generate Multi-dimensional Characters

The system MUST generate multi-dimensional characters including protagonist, antagonist (optional), and multiple supporting characters based on the world setting and theme conflict.

#### Scenario: Create protagonist with depth

- **WHEN** 生成角色配置
- **THEN** 必须为主角定义以下完整信息:
  - name: 姓名
  - role: 定位为"主角"
  - age: 年龄（如适用）
  - gender: 性别
  - appearance: 外貌特征
  - personality: 性格特质
  - background: 背景故事
  - motivation: 行动动机
  - abilities: 特殊能力列表（如适用）
  - relationships: 与其他角色的关系映射

#### Scenario: Optionally generate antagonist

- **WHEN** 故事需要反派角色
- **THEN** 系统可生成包含完整属性的 antagonist 对象
- **AND** 必须体现反派的目标、动机和与主角的对立关系

#### Scenario: Create supporting characters

- **WHEN** generating character configuration
- **THEN** the system MUST generate at least 3 supporting characters to form a character network
- **AND** each supporting character MUST have unique personality, background, and connection to the main story

#### Scenario: Build character relationships

- **WHEN** generating the relationships field for characters
- **THEN** the system MUST clearly describe relationships with other characters (e.g., master-disciple, nemesis, lover, ally)
- **AND** relationship descriptions MUST reflect emotional bonds and interest connections between characters

### Requirement: Support Structured Output Mode

The system MUST support both structured output mode and traditional parsing mode for character generation.

#### Scenario: Use structured output when available

- **WHEN** `llm_config.use_structured_output` 为 True 且后端模型支持
- **THEN** 系统 MUST 使用 `with_structured_output(CharactersConfig)` 模式
- **AND** 输出直接符合 CharactersConfig Pydantic 模型

#### Scenario: Fallback to traditional parsing

- **WHEN** structured output 模式初始化失败
- **THEN** 系统 MUST 自动退回到 PydanticOutputParser + LLMJsonRepairOutputParser
- **AND** 在控制台输出警告信息说明退回原因

### Requirement: Initialize Character Memory

The system MUST initialize character states in the memory layer for tracking throughout the story.

#### Scenario: Save initial character states to Mem0

- **WHEN** 角色配置成功生成
- **THEN** 系统 MUST 为每个角色（主角、反派、配角）在 Mem0 中创建初始状态记录
- **AND** 初始状态 MUST 包含角色的性格特点和背景信息
- **AND** 状态记录 MUST 标记为 chapter_index=0（故事开始前）
