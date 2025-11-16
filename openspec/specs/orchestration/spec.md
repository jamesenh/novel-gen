# orchestration Specification

## Purpose
TBD - created by archiving change establish-baseline. Update Purpose after archive.
## Requirements
### Requirement: Coordinate Multi-step Novel Generation
The system MUST provide an orchestrator to coordinate the 6-step novel generation process, managing project files, handling dependency relationships, and tracking progress.

#### Scenario: Chain execution with prerequisites
- **WHEN** 执行某步骤时（如step3_create_characters）
- **THEN** 编排器应验证所需前置数据是否存在
- **AND** 前置数据缺失时应抛出ValueError并提示正确的执行顺序

#### Scenario: Save JSON outputs
- **WHEN** 任意生成步骤完成
- **THEN** 编排器应将结果保存到projects/{project_name}/目录的JSON文件中
- **AND** 文件名和路径应遵循项目约定

#### Scenario: Reuse existing results
- **WHEN** 调用生成步骤且force=False（默认）
- **THEN** 若对应JSON文件存在且能被Pydantic模型解析，应跳过生成并使用现有结果
- **AND** 控制台应打印跳过信息提示用户

#### Scenario: Force regeneration
- **WHEN** 调用生成步骤且force=True
- **THEN** 系统应忽略现有文件并重新生成内容
- **AND** 覆盖原文件保存新结果

#### Scenario: Batch chapter processing
- **WHEN** 调用generate_all_chapters()
- **THEN** 系统应遍历outline.json中所有章节
- **AND** 依次为每个章节执行plan生成和text生成
- **AND** 处理失败时应记录错误并继续下一章

#### Scenario: Manage project lifecycle
- **WHEN** 初始化NovelOrchestrator时
- **THEN** 应创建项目目录结构（项目和章节子目录）
- **AND** 确保目录可写入

#### Scenario: Provide verbose logging
- **WHEN** verbose=True is set during initialization
- **THEN** the system MUST output detailed generation information
- **AND** MUST include LLM call duration, token usage, prompt content, and other debugging information

