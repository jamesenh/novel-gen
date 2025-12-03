# configuration Specification

## Purpose

配置管理模块负责管理项目级别和链级别的 LLM 配置、API 密钥、Mem0 配置以及运行时参数。支持通过环境变量灵活覆盖默认配置，实现不同生成步骤使用不同的模型和参数。

**技术实现**：
- 使用 Pydantic `BaseModel` 定义配置类
- 自动加载 `.env` 和 `.env.local` 文件
- 支持链特定的环境变量覆盖（`{CHAIN_NAME}_{CONFIG_TYPE}` 格式）
- `ProjectConfig` 提供项目目录结构和文件路径管理
- `Mem0Config` 管理 Mem0 记忆层配置

**代码位置**：`novelgen/config.py`

## Requirements

### Requirement: Support Chain-level LLM Configuration

The system MUST provide independent LLM configuration for each generation chain, supporting overrides to default settings via environment variables.

#### Scenario: Define chain-specific defaults

- **WHEN** 系统初始化 ProjectConfig
- **THEN** 每个生成链应有默认配置:
  - world_chain: gpt-4o-mini, 1000 tokens, temperature 0.7
  - theme_conflict_chain: gpt-3.5-turbo, 500 tokens, temperature 0.7
  - characters_chain: gpt-4o-mini, 2000 tokens, temperature 0.7
  - outline_chain: gpt-4o-mini, 3000 tokens, temperature 0.7
  - chapters_plan_chain: gpt-3.5-turbo, 1000 tokens, temperature 0.7
  - scene_text_chain: gpt-4, 8000 tokens, temperature 0.7
  - chapter_memory_chain: gpt-4o-mini, 2000 tokens, temperature 0.7
  - consistency_chain: gpt-4o-mini, 4000 tokens, temperature 0.7
  - revision_chain: gpt-4o-mini, 8000 tokens, temperature 0.7
  - memory_context_chain: gpt-4o-mini, 1000 tokens, temperature 0.7

#### Scenario: Override via environment variables

- **WHEN** 设置环境变量如 WORLD_CHAIN_MODEL_NAME=gpt-4
- **THEN** world_chain 应使用该模型而非默认值
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

### Requirement: Support Structured Output Mode

The system MUST support configuring structured output mode for each chain.

#### Scenario: Enable structured output by default

- **WHEN** 创建 LLMConfig 且未显式设置 use_structured_output
- **THEN** use_structured_output MUST 默认为 True
- **AND** 链应优先尝试使用 with_structured_output() 模式

#### Scenario: Disable structured output for fallback

- **WHEN** use_structured_output 设置为 False 或 structured output 初始化失败
- **THEN** 系统 MUST 退回到 PydanticOutputParser + LLMJsonRepairOutputParser

### Requirement: Configure Mem0 Memory Layer

The system MUST support comprehensive Mem0 configuration for the memory layer.

#### Scenario: Enable Mem0 via environment variable

- **WHEN** 环境变量 MEM0_ENABLED 设置为 "true"、"1"、"yes" 或 "on"
- **THEN** 系统 MUST 创建 Mem0Config 并初始化 Mem0 管理器
- **AND** Mem0Config MUST 包含以下字段：
  - enabled: 是否启用
  - chroma_path: ChromaDB 存储路径
  - collection_name: Collection 名称
  - embedding_model_dims: 向量维度

#### Scenario: Configure Mem0 LLM settings

- **WHEN** 需要配置 Mem0 内部使用的 LLM
- **THEN** 系统 MUST 支持以下环境变量：
  - MEM0_LLM_MODEL_NAME: LLM 模型名称
  - MEM0_LLM_API_KEY: LLM API 密钥
  - MEM0_LLM_BASE_URL: LLM API 基础 URL
  - MEM0_LLM_TEMPERATURE: LLM 温度（默认 0.0）
  - MEM0_LLM_MAX_TOKENS: LLM 最大 token 数

#### Scenario: Configure Mem0 retry settings

- **WHEN** 需要配置 Mem0 的重试行为
- **THEN** 系统 MUST 支持以下环境变量：
  - MEM0_REQUEST_TIMEOUT: 请求超时（默认 30 秒）
  - MEM0_MAX_RETRIES: 最大重试次数（默认 3）
  - MEM0_RETRY_BACKOFF_FACTOR: 重试退避因子（默认 2.0）

#### Scenario: Configure Mem0 parallel processing

- **WHEN** 需要配置 Mem0 的并行处理
- **THEN** 系统 MUST 支持环境变量 MEM0_PARALLEL_WORKERS（默认 5）
- **AND** 该值控制场景内容保存的并行工作线程数

### Requirement: Configure Embedding Model

The system MUST support configuring the embedding model for vector operations.

#### Scenario: Set embedding model via environment

- **WHEN** 需要配置 Embedding 模型
- **THEN** 系统 MUST 支持以下环境变量：
  - EMBEDDING_MODEL_NAME: 模型名称（默认 text-embedding-3-small）
  - EMBEDDING_API_KEY: API 密钥
  - EMBEDDING_BASE_URL: API 基础 URL
  - EMBEDDING_DIMENSIONS: 向量维度（可选）
  - EMBEDDING_CHUNK_SIZE: 文本分块大小（默认 500）
  - EMBEDDING_CHUNK_OVERLAP: 分块重叠大小（默认 50）

### Requirement: Configure Revision Policy

The system MUST support configuring chapter revision policy.

#### Scenario: Set revision policy via environment

- **WHEN** 需要配置修订策略
- **THEN** 系统 MUST 支持环境变量 NOVELGEN_REVISION_POLICY
- **AND** 支持的值：none（默认）、auto_apply、manual_confirm

#### Scenario: Configure revision policy in ProjectConfig

- **WHEN** 初始化 ProjectConfig
- **THEN** revision_policy 字段 MUST 支持以下值：
  - "none": 不执行自动修订（默认）
  - "auto_apply": 自动应用修订
  - "manual_confirm": 生成修订候选等待确认

### Requirement: Configure LangGraph Recursion Limit

The system MUST support configuring LangGraph workflow recursion limits.

#### Scenario: Set recursion limit via environment

- **WHEN** 需要配置递归限制
- **THEN** 系统 MUST 支持环境变量 LANGGRAPH_RECURSION_LIMIT（默认 500）
- **AND** 该值 MUST 传入 workflow.invoke() 的 config.recursion_limit

#### Scenario: Configure nodes per chapter estimate

- **WHEN** 需要配置每章预估节点消耗数
- **THEN** 系统 MUST 支持环境变量 LANGGRAPH_NODES_PER_CHAPTER（默认 6）
- **AND** 该值用于递归限制预估机制

### Requirement: Provide Project File Paths

The system MUST provide convenient access to project file paths.

#### Scenario: Access standard file paths

- **WHEN** 需要访问项目文件路径
- **THEN** ProjectConfig MUST 提供以下属性：
  - world_file: world.json 路径
  - theme_conflict_file: theme_conflict.json 路径
  - characters_file: characters.json 路径
  - outline_file: outline.json 路径
  - chapters_dir: chapters 目录路径
  - chapter_memory_file: chapter_memory.json 路径
  - consistency_report_file: consistency_reports.json 路径

#### Scenario: Access vector store directory

- **WHEN** 需要获取向量存储目录
- **THEN** `get_vector_store_dir()` MUST 返回：
  - 如果设置了 vector_store_dir，返回该路径（相对路径相对于 project_dir）
  - 否则返回默认路径 project_dir/data/vectors

### Requirement: Auto-load Environment Files

The system MUST automatically load environment variables from .env files.

#### Scenario: Load .env files on import

- **WHEN** config.py 模块被导入
- **THEN** 系统 MUST 自动加载以下文件（按优先级）：
  - .env.local（优先级更高）
  - .env
- **AND** 已存在的环境变量不应被覆盖
