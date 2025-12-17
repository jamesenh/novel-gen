## ADDED Requirements

### Requirement: Configure Logic Review Quality Gate

系统 MUST 支持配置“逻辑审查质量闸门”，并确保默认行为与旧项目保持兼容。

#### Scenario: Default off for backward compatibility

- **WHEN** 项目未配置逻辑审查相关字段
- **THEN** `logic_review_policy` MUST 默认为 `"off"`
- **AND** 系统 MUST 不因逻辑审查而阻断生成流程

#### Scenario: Enable blocking mode in settings

- **WHEN** `settings.json` 中配置：
  - `logic_review_policy == "blocking"`
  - `logic_review_min_score` 为一个 0-100 的整数
- **THEN** 系统 MUST 在章节生成完成后启用逻辑审查 gate
- **AND** MUST 使用 `logic_review_min_score` 作为评分阈值

#### Scenario: Override logic review policy via environment variables

- **WHEN** 设置环境变量 `NOVELGEN_LOGIC_REVIEW_POLICY`
- **THEN** 系统 MUST 允许用其覆盖项目默认策略
- **AND** 支持的值至少包含：`off`、`blocking`

- **WHEN** 设置环境变量 `NOVELGEN_LOGIC_REVIEW_MIN_SCORE`
- **THEN** 系统 MUST 允许用其覆盖 `logic_review_min_score`

### Requirement: Provide Chain-level LLM Configuration for Logic Review

系统 MUST 为逻辑审查链提供链级 LLM 配置，与现有 chain-level 配置模式保持一致。

#### Scenario: Define logic_review_chain defaults

- **WHEN** 初始化 ProjectConfig 的链配置
- **THEN** 系统 MUST 提供 `logic_review_chain` 的默认配置（model/max_tokens/temperature 等）
- **AND** MUST 支持通过环境变量 `{CHAIN_NAME}_{CONFIG_TYPE}` 覆盖（如 `LOGIC_REVIEW_CHAIN_MODEL_NAME`）

