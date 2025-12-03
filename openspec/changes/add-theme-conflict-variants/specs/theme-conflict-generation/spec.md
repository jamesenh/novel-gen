## ADDED Requirements

### Requirement: Generate Multiple Theme Conflict Variants from World Setting

The system MUST support generating multiple (configurable) distinct theme conflict variants based on the world setting, allowing users to choose their preferred option.

#### Scenario: Generate variants from world setting without user input

- **WHEN** 用户未提供主题方向描述
- **AND** 系统已有完整的 WorldSetting
- **THEN** 系统 MUST 根据世界观自动推导并生成多个风格各异的主题冲突候选
- **AND** 每个候选 MUST 包含:
  - `variant_id`: 唯一标识符（如 "variant_1"）
  - `style_tag`: 风格标签（如 "热血成长"、"黑暗复仇"、"治愈日常"）
  - `brief_description`: 50-100字的主题冲突简述
  - `theme_conflict`: 完整的 ThemeConflict 对象

#### Scenario: Generate variants with user direction

- **WHEN** 用户提供简短的主题方向描述（如 "复仇"、"爱情"）
- **AND** 系统已有完整的 WorldSetting
- **THEN** 系统 MUST 结合用户方向生成多个不同角度的主题冲突候选

#### Scenario: Ensure variant diversity

- **WHEN** 系统生成多个主题冲突候选
- **THEN** 各候选 MUST 在以下维度体现差异化:
  - 核心主题方向（成长/复仇/守护/爱情/探索）
  - 冲突类型（外部/内心/人际/命运）
  - 作品基调（热血/黑暗/温馨/悬疑）
  - 叙事节奏（快节奏/慢热/起伏剧烈）

#### Scenario: Use configured variant count

- **WHEN** 生成主题冲突候选
- **THEN** 系统 MUST 从 `ProjectConfig.world_variants_count` 读取候选数量
- **AND** 数量由环境变量 `WORLD_VARIANTS_COUNT` 配置，默认为 3

### Requirement: Select Theme Conflict Variant

The system MUST allow users to select a specific theme conflict variant from the generated candidates.

#### Scenario: Select and save variant

- **WHEN** 用户从候选中选择一个变体（通过 variant_id）
- **THEN** 系统 MUST 将选中变体的 `theme_conflict` 保存为 `theme_conflict.json`
- **AND** 后续流程使用该选择

#### Scenario: Regenerate variants

- **WHEN** 用户对所有候选都不满意
- **THEN** 用户 MAY 请求重新生成新的候选集
- **AND** 新候选应与之前不同

