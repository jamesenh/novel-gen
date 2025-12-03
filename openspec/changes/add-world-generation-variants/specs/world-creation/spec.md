## ADDED Requirements

### Requirement: Generate Multiple World Variants from Brief Prompt

The system MUST support generating multiple (default 3) distinct world setting variants from a brief user prompt, allowing users to choose their preferred option.

#### Scenario: Generate variants from minimal prompt

- **WHEN** 用户提供简短提示如 "修仙世界"
- **THEN** 系统 MUST 生成 3 个风格各异的世界观候选
- **AND** 每个候选 MUST 包含:
  - `variant_id`: 唯一标识符（如 "variant_1"）
  - `style_tag`: 风格标签（如 "古典仙侠"、"都市修真"、"末世修仙"）
  - `brief_description`: 50-100字的简要描述
  - `world_setting`: 完整的 WorldSetting 对象

#### Scenario: Ensure variant diversity

- **WHEN** 系统生成多个世界观候选
- **THEN** 各候选 MUST 在以下维度体现差异化:
  - 时代背景（古代/现代/未来）
  - 社会结构（门派/家族/国家）
  - 力量体系（传统/创新/混合）
  - 整体风格（严肃/轻松/黑暗）

#### Scenario: Configure variant count via parameter

- **WHEN** 用户指定候选数量参数 `num_variants`
- **THEN** 系统 MUST 生成指定数量的候选
- **AND** 数量 MUST 在 2-5 之间

#### Scenario: Use configured default variant count

- **WHEN** 用户未指定 `num_variants` 参数
- **THEN** 系统 MUST 从 `ProjectConfig.world_variants_count` 读取默认值
- **AND** 默认值由环境变量 `WORLD_VARIANTS_COUNT` 配置，未设置时为 3

### Requirement: Expand Brief Prompt to Detailed Description

The system MUST support expanding a brief user prompt into a detailed world description before generation.

#### Scenario: Expand minimal input

- **WHEN** 用户提供简短提示如 "赛博朋克都市"
- **THEN** 系统 MUST 生成 200-500 字的详细世界描述
- **AND** 描述 MUST 包含地理、社会、科技、文化等维度的具体设定

#### Scenario: Preserve user intent

- **WHEN** 用户提供带有特定要求的提示如 "修仙世界，但没有门派只有散修"
- **THEN** 扩写结果 MUST 保留用户的特定要求
- **AND** 在此基础上补充其他合理细节

### Requirement: Select World Variant

The system MUST provide an interface for users to select one variant from the generated candidates.

#### Scenario: Select variant by ID

- **WHEN** 用户选择候选 `variant_id` 如 "variant_2"
- **THEN** 系统 MUST 将对应的 WorldSetting 保存为项目的正式世界观
- **AND** 保存到 `world.json` 文件

#### Scenario: Store variants for later selection

- **WHEN** 多候选生成完成但用户未立即选择
- **THEN** 系统 MUST 将所有候选保存到 `world_variants.json`
- **AND** 用户可以稍后通过命令选择

#### Scenario: Reject all variants and regenerate

- **WHEN** 用户对所有候选都不满意
- **THEN** 用户可以请求重新生成新一批候选
- **AND** 可选择性地提供更具体的提示来引导生成方向

