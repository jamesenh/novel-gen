## ADDED Requirements

### Requirement: Celery Application Configuration

系统 MUST 配置 Celery 应用用于处理异步生成任务。

#### Scenario: Initialize Celery app

- **WHEN** 应用启动
- **THEN** Celery MUST 使用 Redis 作为 broker
- **AND** 结果后端 MUST 配置为 Redis
- **AND** 任务序列化 MUST 使用 JSON 格式

#### Scenario: Configure task queues

- **WHEN** Celery 初始化
- **THEN** MUST 创建 generation 队列用于生成任务
- **AND** 并发数 MUST 限制为 1（单用户模式，避免资源冲突）

### Requirement: Generation Task Definition

系统 MUST 定义 Celery 任务封装小说生成流程。

#### Scenario: Create generation task

- **WHEN** 调用 generate_novel 任务
- **THEN** 任务 MUST 接受参数：project_name, stop_at (optional), verbose (optional)
- **AND** 任务 MUST 创建 NovelOrchestrator 实例执行生成
- **AND** 任务 MUST 返回生成结果（成功/失败）

#### Scenario: Resume generation task

- **WHEN** 调用 resume_novel 任务
- **THEN** 任务 MUST 调用 orchestrator.resume_workflow()
- **AND** 任务 MUST 从最新检查点恢复状态

#### Scenario: Handle task failure

- **WHEN** 生成过程中发生异常
- **THEN** 任务 MUST 记录错误日志
- **AND** 任务状态 MUST 设置为 FAILURE
- **AND** 异常信息 MUST 可通过结果获取

### Requirement: Progress Reporting

系统 MUST 支持生成任务的进度报告。

#### Scenario: Update task progress

- **WHEN** 生成步骤完成或章节/场景生成完成
- **THEN** 任务 MUST 调用 self.update_state() 更新进度
- **AND** 进度信息 MUST 包括：current_step, current_chapter, current_scene, progress_percent, message

#### Scenario: Store progress in Redis

- **WHEN** 进度更新
- **THEN** 系统 MUST 将进度存储到 Redis
- **AND** key 格式 MUST 为 generation_progress:{project_name}
- **AND** 值 MUST 为 JSON 格式

#### Scenario: Query progress from Redis

- **WHEN** API 或 WebSocket 需要获取进度
- **THEN** 系统 MUST 能从 Redis 读取最新进度
- **AND** 如果任务未运行 MUST 返回 idle 状态

### Requirement: Task Cancellation

系统 MUST 支持取消正在运行的生成任务。

#### Scenario: Request task cancellation

- **WHEN** 调用停止生成 API
- **THEN** 系统 MUST 向任务发送终止信号
- **AND** MUST 设置停止标志（should_stop_early）
- **AND** MUST 调用 revoke() 取消 Celery 任务

#### Scenario: Handle cancellation in task

- **WHEN** 任务收到取消信号
- **THEN** 任务 MUST 在下一个安全点停止
- **AND** MUST 保存当前状态到检查点
- **AND** 任务状态 MUST 设置为 REVOKED

#### Scenario: Graceful shutdown

- **WHEN** 任务被取消
- **THEN** 系统 MUST 调用 orchestrator.cleanup()
- **AND** MUST 关闭 Mem0 管理器和数据库连接

### Requirement: Task State Management

系统 MUST 管理生成任务的状态。

#### Scenario: Track active task

- **WHEN** 生成任务启动
- **THEN** 系统 MUST 在 Redis 存储活动任务信息
- **AND** key 格式 MUST 为 active_task:{project_name}
- **AND** 值 MUST 包含 task_id, started_at

#### Scenario: Prevent concurrent tasks

- **WHEN** 尝试启动新任务但已有任务运行中
- **THEN** 系统 MUST 检查 active_task 是否存在
- **AND** 如果存在 MUST 拒绝新任务并返回错误

#### Scenario: Clear task state on completion

- **WHEN** 任务完成、失败或被取消
- **THEN** 系统 MUST 删除 active_task 记录
- **AND** MUST 保留进度历史用于查询

### Requirement: Task Retry and Recovery

系统 MUST 支持任务失败后的重试和恢复。

#### Scenario: Automatic retry on transient failure

- **WHEN** 任务因临时错误失败（如网络超时）
- **THEN** Celery MUST 自动重试任务
- **AND** 最大重试次数 MUST 为 3
- **AND** 重试间隔 MUST 指数增长

#### Scenario: Manual recovery via resume

- **WHEN** 任务因非临时错误失败
- **THEN** 系统 MUST 允许用户通过 resume API 手动恢复
- **AND** 恢复 MUST 从最新检查点开始

### Requirement: Task Logging

系统 MUST 记录生成任务的日志。

#### Scenario: Log task lifecycle

- **WHEN** 任务启动、完成或失败
- **THEN** 系统 MUST 记录带时间戳的日志
- **AND** 日志级别 MUST 为 INFO（正常）或 ERROR（失败）

#### Scenario: Stream logs to WebSocket

- **WHEN** verbose 模式启用
- **THEN** 系统 MUST 将详细日志推送到 WebSocket
- **AND** 日志 MUST 包含 LLM 调用信息、生成内容摘要等

#### Scenario: Persist logs for retrieval

- **WHEN** 任务产生日志
- **THEN** 系统 MUST 将日志写入 Redis（如 generation_logs:{project_name}）
- **AND** MUST 支持通过 API 分页读取日志

