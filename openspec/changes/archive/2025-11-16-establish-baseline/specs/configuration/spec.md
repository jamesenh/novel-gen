## ADDED Requirements

### Requirement: Support Chain-level LLM Configuration
The system MUST provide independent LLM configuration for each generation chain, supporting overrides to default settings via environment variables.

#### Scenario: Define chain-specific defaults
- **WHEN** 系统初始化ProjectConfig
- **THEN** 每个生成链应有默认配置:
  - world_chain: gpt-4o-mini, 1000 tokens, temperature 0.7
  - theme_conflict_chain: gpt-3.5-turbo, 500 tokens, temperature 0.7
  - characters_chain: gpt-4o-mini, 2000 tokens, temperature 0.7
  - outline_chain: gpt-4o-mini, 3000 tokens, temperature 0.7
  - chapters_plan_chain: gpt-3.5-turbo, 1000 tokens, temperature 0.7
  - scene_text_chain: gpt-4, 8000 tokens, temperature 0.7

#### Scenario: Override via environment variables
- **WHEN** 设置环境变量如WORLD_CHAIN_MODEL_NAME=gpt-4
- **THEN** world_chain应使用该模型而非默认值
- **AND** 支持的覆盖变量格式: {CHAIN_NAME}_{CONFIG_TYPE}
  - {CHAIN_NAME}_MODEL_NAME
  - {CHAIN_NAME}_MAX_TOKENS
  - {CHAIN_NAME}_TEMPERATURE
  - {CHAIN_NAME}_BASE_URL
  - {CHAIN_NAME}_API_KEY

#### Scenario: Configure LLM externally
- **WHEN** switching LLM providers or API endpoints is needed
- **THEN** base_url and api_key MUST be configurable via environment variables
- **AND** LLM services MUST be swappable without code modification

#### Scenario: Load project configuration
- **WHEN** NovelOrchestrator is initialized with project_dir specified
- **THEN** ProjectConfig MUST:
  - Recognize project directory structure
  - Load corresponding configuration for each generation chain
  - Provide file paths required for each step
  - Support configuration serialization and saving
