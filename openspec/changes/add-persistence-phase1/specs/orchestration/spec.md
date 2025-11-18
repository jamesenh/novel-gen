## MODIFIED Requirements

### Requirement: Coordinate Multi-step Novel Generation
The system MUST provide an orchestrator to coordinate the 6-step novel generation process, managing project files, handling dependency relationships, tracking progress, and optionally persisting state to database.

#### Scenario: Chain execution with prerequisites
- **WHEN** 执行某步骤时（如step3_create_characters）
- **THEN** 编排器应验证所需前置数据是否存在
- **AND** 前置数据缺失时应抛出ValueError并提示正确的执行顺序

#### Scenario: Save JSON outputs
- **WHEN** 任意生成步骤完成
- **THEN** 编排器应将结果保存到projects/{project_name}/目录的JSON文件中
- **AND** 文件名和路径应遵循项目约定
- **AND** 如果启用了持久化功能，应同时将结果保存到数据库

#### Scenario: Reuse existing results
- **WHEN** 调用生成步骤且force=False（默认）
- **THEN** 若对应JSON文件存在且能被Pydantic模型解析，应跳过生成并使用现有结果
- **AND** 控制台应打印跳过信息提示用户

#### Scenario: Force regeneration
- **WHEN** 调用生成步骤且force=True
- **THEN** 系统应忽略现有文件并重新生成内容
- **AND** 覆盖原文件保存新结果
- **AND** 如果启用了持久化功能，应更新数据库中的对应记录

#### Scenario: Batch chapter processing
- **WHEN** 调用generate_all_chapters()
- **THEN** 系统应遍历outline.json中所有章节
- **AND** 依次为每个章节执行plan生成和text生成
- **AND** 处理失败时应记录错误并继续下一章
- **AND** 如果启用了持久化功能，应为每个生成的场景创建文本记忆块

#### Scenario: Manage project lifecycle
- **WHEN** 初始化NovelOrchestrator时
- **THEN** 应创建项目目录结构（项目和章节子目录）
- **AND** 确保目录可写入
- **AND** 如果启用了持久化功能，应初始化数据库和向量存储连接

#### Scenario: Provide verbose logging
- **WHEN** verbose=True is set during initialization
- **THEN** the system MUST output detailed generation information
- **AND** MUST include LLM call duration, token usage, prompt content, and other debugging information
- **AND** 如果启用了持久化功能，应包含数据库操作的状态信息

## ADDED Requirements

### Requirement: 持久化集成钩子
编排器MUST提供可选的持久化功能，在生成过程中自动保存状态快照和文本记忆。

#### Scenario: 持久化初始化
- **WHEN** orchestrator启动且persistence_enabled=True
- **THEN** 必须初始化数据库连接和向量存储
- **AND** 必须验证存储功能可用性
- **AND** 如果存储不可用，必须降级到非持久化模式并记录警告

#### Scenario: 状态快照自动保存
- **WHEN** 任何生成链执行完成并输出Pydantic模型
- **THEN** orchestrator必须自动调用持久化服务保存状态快照
- **AND** 必须包含项目ID、链类型、执行时间戳、输出数据等完整信息
- **AND** 保存失败时不应中断主流程，只记录错误日志

#### Scenario: 文本记忆向量化
- **WHEN** 场景文本生成完成（GeneratedScene）
- **THEN** orchestrator必须自动将文本内容分块并向量化
- **AND** 必须建立文本块与项目、章节、场景的关联关系
- **AND** 向量化失败时不应中断主流程，只记录错误日志

#### Scenario: 持久化配置管理
- **WHEN** 用户需要配置持久化行为
- **THEN** orchestrator必须支持通过配置文件或环境变量控制持久化开关
- **AND** 必须支持配置数据库路径、向量存储设置等参数（例如通过 ProjectConfig.db_path / vector_store_dir 或对应环境变量）
- **AND** 配置变更必须支持运行时热重载而不影响正在进行的任务；在当前 CLI/单次运行架构下，“热重载”指通过重新创建 NovelOrchestrator 实例来应用最新配置，而不会影响已有实例正在执行的任务

#### Scenario: 错误处理和降级
- **WHEN** 持久化操作发生错误
- **THEN** orchestrator必须优雅降级到JSON文件模式
- **AND** 必须确保主要的生成流程不受持久化故障影响
- **AND** 必须提供详细的错误日志用于问题诊断
