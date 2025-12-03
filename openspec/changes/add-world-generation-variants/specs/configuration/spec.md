## ADDED Requirements

### Requirement: Configure World Variants Generation

The system MUST support configuring the default number of world setting variants to generate.

#### Scenario: Set world variants count via environment variable

- **WHEN** 环境变量 `WORLD_VARIANTS_COUNT` 设置为有效整数（如 "4"）
- **THEN** `ProjectConfig.world_variants_count` MUST 使用该值作为默认候选数量
- **AND** 该值 MUST 在 2-5 范围内，超出范围时使用边界值

#### Scenario: Use default world variants count

- **WHEN** 环境变量 `WORLD_VARIANTS_COUNT` 未设置
- **THEN** `ProjectConfig.world_variants_count` MUST 默认为 3

#### Scenario: Access world variants file path

- **WHEN** 需要访问世界观候选文件路径
- **THEN** `ProjectConfig` MUST 提供 `world_variants_file` 属性
- **AND** 返回 `project_dir/world_variants.json` 路径

