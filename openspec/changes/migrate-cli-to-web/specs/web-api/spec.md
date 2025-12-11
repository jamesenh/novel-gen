## ADDED Requirements

### Requirement: API Base Configuration

系统 MUST 使用 FastAPI 框架提供 RESTful API，所有接口统一使用 `/api/` 前缀。

#### Scenario: API path convention

- **WHEN** 客户端请求任何 API
- **THEN** 所有 API 路径 MUST 以 `/api/` 为前缀
- **AND** 首版不使用版本号（如 `/api/v1/`）
- **AND** WebSocket 路径 MUST 以 `/ws/` 为前缀

### Requirement: Project Management API

系统 MUST 提供 RESTful API 管理小说项目，支持项目的创建、查询、删除等操作。

#### Scenario: List all projects

- **WHEN** 客户端请求 GET /api/projects
- **THEN** 系统 MUST 返回 projects/ 目录下所有项目的列表
- **AND** 每个项目 MUST 包含 name, created_at, status 字段
- **AND** 响应状态码 MUST 为 200

#### Scenario: Create new project

- **WHEN** 客户端请求 POST /api/projects 并提供 project_name, world_description, theme_description, initial_chapters
- **THEN** 系统 MUST 创建项目目录和 settings.json
- **AND** 响应 MUST 包含创建的项目信息
- **AND** 响应状态码 MUST 为 201

#### Scenario: Get project details

- **WHEN** 客户端请求 GET /api/projects/{name}
- **THEN** 系统 MUST 返回项目的详细信息（settings, 生成进度等）
- **AND** 如果项目不存在 MUST 返回 404

#### Scenario: Delete project

- **WHEN** 客户端请求 DELETE /api/projects/{name}
- **THEN** 系统 MUST 删除项目目录及所有相关文件
- **AND** 响应状态码 MUST 为 204

#### Scenario: Get project state

- **WHEN** 客户端请求 GET /api/projects/{name}/state
- **THEN** 系统 MUST 返回项目的详细状态，包括：
  - steps: 各基础步骤完成情况
  - chapters: 每章的计划、场景、完成状态
  - checkpoint_exists: 检查点是否存在

### Requirement: Generation Control API

系统 MUST 提供 API 控制小说生成流程，支持开始、恢复、停止生成任务。

#### Scenario: Start generation

- **WHEN** 客户端请求 POST /api/projects/{name}/generate
- **THEN** 系统 MUST 创建 Celery 异步任务执行生成
- **AND** 响应 MUST 包含 task_id 用于跟踪进度
- **AND** 响应状态码 MUST 为 202

#### Scenario: Start generation with stop-at

- **WHEN** 客户端请求 POST /api/projects/{name}/generate 并提供 stop_at 参数
- **THEN** 系统 MUST 创建生成任务，在指定步骤后停止
- **AND** stop_at 支持的值 MUST 包括: world_creation, theme_conflict_creation, character_creation, outline_creation, chapter_planning

#### Scenario: Resume generation

- **WHEN** 客户端请求 POST /api/projects/{name}/generate/resume
- **THEN** 系统 MUST 从最新检查点恢复生成任务
- **AND** 如果无检查点可恢复 MUST 返回 400

#### Scenario: Stop generation

- **WHEN** 客户端请求 POST /api/projects/{name}/generate/stop
- **THEN** 系统 MUST 设置停止标志并终止当前任务
- **AND** 响应 MUST 返回停止确认

#### Scenario: Get generation status

- **WHEN** 客户端请求 GET /api/projects/{name}/generate/status
- **THEN** 系统 MUST 返回当前生成任务状态
- **AND** 状态 MUST 包括: idle, running, completed, failed, stopped
- **AND** 如果 running MUST 包含当前步骤和进度信息

### Requirement: WebSocket Progress Push

系统 MUST 通过 WebSocket 实时推送生成进度给客户端。

#### Scenario: Connect to progress WebSocket

- **WHEN** 客户端连接 WS /ws/projects/{name}/progress
- **THEN** 系统 MUST 建立 WebSocket 连接
- **AND** 连接成功后 MUST 发送当前状态消息

#### Scenario: Push progress updates

- **WHEN** 生成任务执行过程中
- **THEN** 系统 MUST 推送进度更新消息，包括：
  - current_step: 当前步骤名称
  - current_chapter: 当前章节号（如适用）
  - current_scene: 当前场景号（如适用）
  - progress_percent: 整体进度百分比
  - message: 人类可读的状态消息

#### Scenario: Push completion notification

- **WHEN** 生成任务完成或失败
- **THEN** 系统 MUST 推送完成消息
- **AND** 消息 MUST 包含 status (completed/failed) 和 result/error 信息

### Requirement: Progress & Logs Fallback API

系统 MUST 提供 HTTP 接口以便在 WebSocket 断线时获取进度与日志。

#### Scenario: Query progress via HTTP

- **WHEN** 客户端请求 GET /api/projects/{name}/generate/progress
- **THEN** 系统 MUST 返回 Redis 中最新的进度快照
- **AND** 进度 MUST 包含 current_step, current_chapter, current_scene, progress_percent, message, status
- **AND** 若无活动任务 MUST 返回 idle 状态

#### Scenario: Query logs via HTTP

- **WHEN** 客户端请求 GET /api/projects/{name}/generate/logs
- **THEN** 系统 MUST 返回最近的生成日志列表（按时间倒序）
- **AND** 日志项 MUST 包含 timestamp, level, message, context
- **AND** 响应 MUST 支持分页或条数限制

### Requirement: Content API

系统 MUST 提供 API 获取和更新生成的小说内容。

#### Scenario: Get world setting

- **WHEN** 客户端请求 GET /api/projects/{name}/world
- **THEN** 系统 MUST 返回 world.json 的完整内容
- **AND** 如果文件不存在 MUST 返回 404

#### Scenario: Get characters

- **WHEN** 客户端请求 GET /api/projects/{name}/characters
- **THEN** 系统 MUST 返回 characters.json 的完整内容

#### Scenario: Get outline

- **WHEN** 客户端请求 GET /api/projects/{name}/outline
- **THEN** 系统 MUST 返回 outline.json 的完整内容

#### Scenario: Get chapters list

- **WHEN** 客户端请求 GET /api/projects/{name}/chapters
- **THEN** 系统 MUST 返回所有章节的元数据列表
- **AND** 每个章节 MUST 包含 chapter_number, chapter_title, scenes_count, total_words, status

#### Scenario: Get chapter content

- **WHEN** 客户端请求 GET /api/projects/{name}/chapters/{num}
- **THEN** 系统 MUST 返回该章节的完整内容（所有场景）
- **AND** 如果章节不存在 MUST 返回 404

### Requirement: Content Editing API

系统 MUST 提供 API 更新与删除生成内容。

#### Scenario: Update world setting

- **WHEN** 客户端请求 PUT /api/projects/{name}/world
- **THEN** 系统 MUST 校验请求体并更新 world.json
- **AND** 成功后 MUST 返回更新后的世界观数据

#### Scenario: Update characters

- **WHEN** 客户端请求 PUT /api/projects/{name}/characters
- **THEN** 系统 MUST 覆盖 characters.json 的角色列表
- **AND** MUST 校验角色唯一性与必填字段

#### Scenario: Update outline

- **WHEN** 客户端请求 PUT /api/projects/{name}/outline
- **THEN** 系统 MUST 更新 outline.json 并保持章节顺序一致

#### Scenario: Update chapter or scenes

- **WHEN** 客户端请求 PUT /api/projects/{name}/chapters/{num}
- **THEN** 系统 MUST 允许更新章节元数据与场景内容
- **AND** MUST 校验章节存在，否则返回 404

#### Scenario: Delete chapter or scene

- **WHEN** 客户端请求 DELETE /api/projects/{name}/chapters/{num}（可选 scene 参数）
- **THEN** 系统 MUST 删除指定章节或场景并更新合并文件
- **AND** MUST 返回删除的对象列表

### Requirement: Export API

系统 MUST 提供 API 导出小说内容为文本文件。

#### Scenario: Export full novel

- **WHEN** 客户端请求 GET /api/projects/{name}/export/txt
- **THEN** 系统 MUST 返回包含所有章节的完整文本
- **AND** Content-Type MUST 为 text/plain; charset=utf-8
- **AND** Content-Disposition MUST 设置为附件下载

#### Scenario: Export single chapter

- **WHEN** 客户端请求 GET /api/projects/{name}/export/txt/{chapter_num}
- **THEN** 系统 MUST 返回该章节的文本内容
- **AND** 如果章节不存在 MUST 返回 404

#### Scenario: Export full novel as Markdown

- **WHEN** 客户端请求 GET /api/projects/{name}/export/md
- **THEN** 系统 MUST 返回 Markdown 格式的全书内容（含章节与场景分隔）
- **AND** Content-Type MUST 为 text/markdown; charset=utf-8
- **AND** Content-Disposition MUST 设置为附件下载

#### Scenario: Export full novel as JSON

- **WHEN** 客户端请求 GET /api/projects/{name}/export/json
- **THEN** 系统 MUST 返回结构化 JSON（包含章节与场景）
- **AND** MUST 支持可选 chapter_num 参数仅导出单章

### Requirement: Rollback API

系统 MUST 提供 API 回滚项目状态到指定点。

#### Scenario: Rollback to step

- **WHEN** 客户端请求 POST /api/projects/{name}/rollback 并提供 step 参数
- **THEN** 系统 MUST 删除该步骤及之后所有步骤的输出文件
- **AND** 清理相关记忆
- **AND** 响应 MUST 包含删除的文件数和记忆数

#### Scenario: Rollback to chapter

- **WHEN** 客户端请求 POST /api/projects/{name}/rollback 并提供 chapter 参数
- **THEN** 系统 MUST 删除该章节及之后所有章节的文件
- **AND** 保留章节计划文件

#### Scenario: Rollback to scene

- **WHEN** 客户端请求 POST /api/projects/{name}/rollback 并提供 chapter 和 scene 参数
- **THEN** 系统 MUST 删除该场景及之后所有场景文件
- **AND** 删除该章节的合并文件

### Requirement: Error Handling

系统 MUST 对所有 API 错误返回一致的错误响应格式。

#### Scenario: Return consistent error format

- **WHEN** API 请求发生错误
- **THEN** 响应 MUST 包含 JSON 格式的错误信息
- **AND** 格式 MUST 为 {"detail": "错误描述", "error_code": "ERROR_CODE"}
- **AND** HTTP 状态码 MUST 与错误类型匹配 (400/404/500等)

#### Scenario: Handle project not found

- **WHEN** 请求的项目不存在
- **THEN** 系统 MUST 返回 404
- **AND** detail MUST 说明项目名称

#### Scenario: Handle concurrent generation

- **WHEN** 尝试启动生成但已有生成任务运行中
- **THEN** 系统 MUST 返回 409 Conflict
- **AND** detail MUST 说明当前任务状态

