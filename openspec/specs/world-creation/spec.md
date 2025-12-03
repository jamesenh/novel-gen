# world-creation Specification

## Purpose

世界观生成模块负责根据用户输入的简要描述生成完整、自洽的小说世界观设定。该模块是小说生成流程的第一步，为后续的主题冲突、角色创建和故事发展奠定基础。

**技术实现**：
- 使用 LangChain `ChatPromptTemplate` 构建结构化提示词
- 通过 `PydanticOutputParser` 结合 `LLMJsonRepairOutputParser` 确保输出符合 `WorldSetting` 模型
- 支持 `verbose` 模式输出详细日志（提示词、响应时间、token 使用情况）
- 通过环境变量 `WORLD_CHAIN_*` 支持链级别的 LLM 配置覆盖

**代码位置**：`novelgen/chains/world_chain.py`

## Requirements

### Requirement: Generate World Setting

The system MUST generate a world setting with world name, time period, geography, social system, power system, technology level, culture customs, and special rules based on user description.

#### Scenario: Create a cultivation world

- **WHEN** 用户提供描述:"一个修真世界，门派林立，强者为尊"
- **THEN** 系统应生成包含以下字段的 WorldSetting:
  - world_name: 描述性世界名称
  - time_period: 时代背景信息
  - geography: 地理特色描述
  - social_system: 社会结构与组织形式
  - power_system: 修为体系和等级（如有）
  - technology_level: 相当于何种时代的技术水平
  - culture_customs: 文化习俗与特色
  - special_rules: 特殊规则与限制

#### Scenario: Validate JSON output structure

- **WHEN** 世界观生成完成
- **THEN** 输出必须能通过 Pydantic 的 WorldSetting 模型验证
- **AND** 必须以 UTF-8 编码的 JSON 格式保存到项目目录

#### Scenario: Handle user input variations

- **WHEN** the user provides minimal, detailed, or specific setting requirements
- **THEN** the system MUST generate a reasonable, complete, and coherent world setting based on the input
- **AND** MUST fill in missing reasonable details

### Requirement: Automatic JSON Repair

The system MUST automatically repair malformed JSON output from LLM to ensure reliable parsing.

#### Scenario: Repair unescaped quotes in JSON

- **WHEN** LLM 输出的 JSON 包含未转义的引号或其他格式问题
- **THEN** `LLMJsonRepairOutputParser` MUST 尝试自动修复 JSON
- **AND** 修复失败时 MUST 抛出包含原始输出的异常信息

#### Scenario: Extract JSON from markdown wrapper

- **WHEN** LLM 输出被 Markdown 代码块（如 \`\`\`json）包裹
- **THEN** 系统 MUST 自动提取 JSON 内容并解析
- **AND** 解析后的数据 MUST 符合 WorldSetting 模型

### Requirement: Save World State to Memory

The system MUST persist the generated world setting to the memory layer for downstream context retrieval.

#### Scenario: Store world in Mem0

- **WHEN** 世界观成功生成并保存到 JSON 文件
- **THEN** 系统 SHOULD 将世界观关键信息（世界名称、时代、社会制度等）保存到 Mem0
- **AND** 后续步骤可通过 Mem0 检索世界观上下文
