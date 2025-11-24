# Memory Management Spec Delta

## ADDED Requirements

### Requirement: Mem0 Client Initialization
系统 SHALL 提供 Mem0 客户端初始化功能，复用现有的 ChromaDB 实例作为向量存储后端。

#### Scenario: Initialize Mem0 with existing ChromaDB
- **WHEN** 配置 `mem0_enabled=True`
- **THEN** 系统应连接到项目现有的 ChromaDB 实例（从 `config.get_vector_store_dir()` 获取路径）
- **AND** 使用独立的 `collection_name="mem0_memories"` 隔离 Mem0 数据
- **AND** 使用与项目一致的 embedding 配置（模型、维度）
- **AND** 初始化成功后返回 Mem0 客户端实例
- **AND** 如果 ChromaDB 连接失败，记录警告日志并禁用 Mem0 功能

#### Scenario: Verify ChromaDB collection isolation
- **WHEN** Mem0 初始化成功
- **THEN** 系统应验证 `mem0_memories` collection 已创建
- **AND** 该 collection 应与现有的 `novel_memories` collection 完全隔离
- **AND** 两个 collection 可以并行读写而不互相干扰

#### Scenario: Mem0 disabled by configuration
- **WHEN** 配置 `mem0_enabled=False`
- **THEN** 系统应跳过 Mem0 初始化
- **AND** 所有记忆操作应回退到 SQLite/ChromaDB（现有逻辑）

### Requirement: User Preference Storage
系统 SHALL 提供用户偏好存储功能，记录作者的写作风格和主动设定的偏好。

**注意**：此功能为预留框架，用于支持未来的用户偏好输入方式（如主动设置、UI 交互等）。当前版本不从自动修订过程中提取偏好，因为基于一致性检测的修订是针对具体章节/场景的，不应作为长期写作偏好。

#### Scenario: Manual user preference setting (预留)
- **WHEN** 用户通过 CLI 或 API 主动添加写作偏好
- **AND** 提供偏好类型（writing_style/character_development/plot_preference/tone）和内容
- **THEN** 系统应存储偏好到 Mem0 User Memory
- **AND** 使用 `user_id="author_{project_name}"` 作为用户标识
- **AND** 偏好应标记来源为 `source="manual"`

### Requirement: User Preference Retrieval
系统 SHALL 在场景生成前检索用户偏好，并将其注入到生成 Prompt 中。

#### Scenario: Inject user preferences into scene generation prompt
- **WHEN** 调用 `generate_scene_text()` 生成场景
- **AND** Mem0 已启用且包含用户偏好
- **THEN** 系统应从 Mem0 检索相关的用户偏好（限制返回前 5 条）
- **AND** 将偏好格式化为 Prompt 的 `{user_preferences}` 部分
- **AND** Prompt 格式示例："作者偏好：避免使用过多形容词；对话需简洁有力"

#### Scenario: Fallback when no user preferences exist
- **WHEN** Mem0 中没有用户偏好记录
- **OR** Mem0 检索失败
- **THEN** 系统应将 `{user_preferences}` 设为空字符串或默认提示
- **AND** 场景生成流程应正常继续（不因缺失偏好而中断）

### Requirement: Entity State Management with Mem0 Agent Memory
系统 SHALL 使用 Mem0 的 Agent Memory 管理角色的动态状态。

#### Scenario: Initialize agent memory for characters
- **WHEN** 执行 `step3_create_characters()` 创建角色
- **AND** Mem0 已启用
- **THEN** 系统应为每个主要角色（主角、反派、配角）创建 Mem0 Agent Memory
- **AND** 使用 `agent_id="{project_id}_{character_name}"` 作为唯一标识
- **AND** 初始状态应包含角色的基础属性（外貌、性格、背景、动机）

#### Scenario: Update entity state after chapter generation
- **WHEN** 完成章节生成（`step6_generate_chapter_text()`）
- **AND** 章节中有角色状态变化（通过场景内容推断）
- **THEN** 系统应更新相关角色的 Mem0 Agent Memory
- **AND** 更新内容应包含：章节编号、场景编号、状态变化描述
- **AND** Mem0 应自动合并新状态与历史状态（去重和冲突解决）

#### Scenario: Retrieve entity state before scene generation
- **WHEN** 调用 `retrieve_scene_memory_context()` 构建场景上下文
- **AND** Mem0 已启用
- **THEN** 系统应优先从 Mem0 检索角色的最新状态（使用 `agent_id`）
- **AND** 如果 Mem0 检索失败或返回空，应降级到 SQLite 的 `get_latest_entity_state()`
- **AND** 返回的 `SceneMemoryContext` 应包含来自 Mem0 的实体状态

### Requirement: Graceful Degradation
系统 SHALL 在 Mem0 服务不可用时自动降级到 SQLite/ChromaDB，确保核心功能不受影响。

#### Scenario: Mem0 connection failure during initialization
- **WHEN** Mem0 初始化失败（网络错误、配置错误、服务不可用）
- **THEN** 系统应记录警告日志："Mem0 初始化失败，降级到 SQLite/ChromaDB"
- **AND** 设置内部标志 `mem0_available=False`
- **AND** 所有后续的记忆操作应使用 SQLite/ChromaDB

#### Scenario: Mem0 query timeout during retrieval
- **WHEN** Mem0 查询超过配置的超时时间（默认 5 秒）
- **THEN** 系统应终止 Mem0 查询
- **AND** 记录警告日志并返回空结果
- **AND** 调用方应继续使用 SQLite/ChromaDB 查询

#### Scenario: Dual-write strategy for data persistence
- **WHEN** 系统写入新记忆（用户偏好或实体状态）
- **AND** Mem0 已启用
- **THEN** 系统应同时写入 Mem0 和 SQLite
- **AND** 如果 Mem0 写入失败，SQLite 写入仍应成功
- **AND** 记录警告日志："Mem0 写入失败，已保存到 SQLite"

### Requirement: Mem0 Health Check and Monitoring
系统 SHALL 提供 Mem0 健康检查功能，便于诊断和监控。

#### Scenario: Check Mem0 connection status
- **WHEN** 调用 `mem0_manager.health_check()` 方法
- **THEN** 系统应尝试连接 Mem0 并执行简单查询
- **AND** 返回健康状态：`{"status": "healthy", "mode": "local/cloud", "response_time_ms": 123}`
- **AND** 如果连接失败，返回：`{"status": "unhealthy", "error": "错误信息"}`

#### Scenario: Export Mem0 memory to JSON backup
- **WHEN** 执行 `scripts/export_mem0_to_json.py --project demo_001`
- **THEN** 系统应导出指定项目的所有 Mem0 记忆（用户偏好和实体状态）
- **AND** 保存为 JSON 文件：`projects/demo_001/mem0_backup_{timestamp}.json`
- **AND** JSON 应包含可读的结构化数据

