## Context

NovelGen 当前是一个纯 CLI 应用，使用 Typer 框架实现命令行交互。项目核心功能包括：
- 6 步小说生成流程（世界观→主题→角色→大纲→章节计划→场景生成）
- LangGraph 工作流编排和检查点持久化
- Mem0 记忆管理
- 项目状态查询和回滚

Web 迁移需要在保留现有核心逻辑的基础上，新增 HTTP API 和前端界面。

**约束条件：**
- 单用户模式（暂不支持多用户认证）
- 生成任务耗时较长（分钟级），需要异步处理
- 需要实时进度反馈
- 保持与现有 CLI 的功能一致性

## Goals / Non-Goals

### Goals
- 提供完整的 Web 界面替代 CLI 所有核心功能
- 实现异步生成任务和实时进度推送
- 保持现有代码的复用性，避免重复实现
- 提供良好的用户体验和可视化能力

### Non-Goals
- 不实现多用户认证（仅预留接口）
- 不实现在线协作功能
- 不改变现有的生成逻辑和 LangGraph 工作流
- 不重构现有的 chains/ 和 runtime/ 模块

## Decisions

### 1. 后端框架选择：FastAPI

**决策**：使用 FastAPI 作为 Web 框架

**理由**：
- 原生异步支持，与 LangGraph 异步工作流兼容
- 自动生成 OpenAPI 文档
- Pydantic 集成，可复用现有模型
- WebSocket 支持良好

### 2. 异步任务处理：Celery + Redis

**决策**：使用 Celery 处理生成任务，Redis 作为消息代理

**理由**：
- 生成任务耗时较长（分钟级），不适合在请求中同步处理
- Celery 支持任务取消、重试、优先级
- Redis 同时可作为进度状态缓存
- 成熟稳定，社区支持良好

### 3. 进度推送：WebSocket

**决策**：使用 WebSocket 推送生成进度

**理由**：
- 实时性好，无需轮询
- FastAPI 原生支持
- 可推送详细进度信息（当前步骤、章节、场景等）

**替代方案**：
- SSE (Server-Sent Events)：单向通信，但浏览器兼容性略好
- HTTP 轮询：资源消耗大，实时性差

### 4. 前端技术栈：React + TypeScript + Vite

**决策**：使用 React + TypeScript 构建前端

**理由**：
- 组件化开发，适合复杂 UI
- TypeScript 类型安全，可与后端 Pydantic 模型对齐
- Vite 构建速度快
- 生态丰富，UI 库选择多

**替代方案**：
- Vue：同样优秀，但团队更熟悉 React
- Next.js：SSR 功能不需要，过于复杂

### 5. 状态管理：Zustand

**决策**：使用 Zustand 进行前端状态管理

**理由**：
- 轻量级，API 简单
- 原生 TypeScript 支持
- 不需要 Redux 的样板代码

**替代方案**：
- Redux Toolkit：功能强大但过于复杂
- Jotai/Recoil：原子化状态，本项目不需要

### 6. 容器化策略：仅 Redis 容器化

**决策**：开发环境仅 Redis 使用 Docker，应用本地运行

**理由**：
- 简化开发调试流程
- 应用可直接在本地调试断点
- Redis 无状态，容器化简单

**未来可扩展**：生产环境可全部容器化

### 7. 服务层设计：封装 Orchestrator

**决策**：新增 services/ 层封装 orchestrator 调用

**理由**：
- API 路由保持简洁
- 业务逻辑集中管理
- 便于单元测试
- 支持 Celery 任务复用

```
API Route → Service → Orchestrator → LangGraph Workflow
                 ↓
            Celery Task (async)
```

### 8. UI 框架：Tailwind CSS

**决策**：使用 Tailwind CSS 作为样式框架

**理由**：
- 灵活度高，可高度定制
- 与现有规划文档一致
- 无需学习组件库 API
- 打包体积小（PurgeCSS）

### 9. 前端路由：React Router

**决策**：使用 React Router v6 进行路由管理

**理由**：
- 最成熟的 React 路由方案
- 社区支持广泛
- 与 React 生态集成良好

### 10. API 版本控制：首版不需要

**决策**：首版不使用版本控制，路径统一 `/api/`

**理由**：
- 单用户模式，不存在多版本兼容问题
- 简化开发和维护
- 未来如需版本控制可扩展为 `/api/v1/`

### 11. 并发限制：单任务

**决策**：单用户模式下限制为 1 个并发生成任务

**理由**：
- 生成任务资源消耗大（LLM 调用、内存）
- 避免任务间状态冲突
- 简化任务管理逻辑
- 可通过 Redis 的 active_task 键实现

### 12. 进度/日志持久化与断线恢复

**决策**：生成进度与日志写入 Redis，提供 HTTP fallback 接口，WebSocket 仅作实时推送。

**理由**：
- Redis 可在 WebSocket 断线时提供可恢复快照
- HTTP fallback 便于前端重连与状态一致性校验
- 日志持久化便于调试与失败复盘

**实现要点**：
- 进度键：`generation_progress:{project_name}`，包含 current_step/current_chapter/current_scene/progress_percent/message
- 活跃任务键：`active_task:{project_name}`，用于并发限制与状态恢复
- 日志键：`generation_logs:{project_name}`（循环列表或分片存储），用于 LogViewer 与 API 导出
- 提供 `GET /api/projects/{name}/generate/progress` 与 `GET /api/projects/{name}/generate/logs`

### 13. 多格式导出策略

**决策**：在保留 TXT 的基础上新增 Markdown 与 JSON 导出，通过适配层统一格式。

**理由**：
- Markdown 便于阅读与排版
- JSON 便于二次处理与外部集成
- 适配层隔离文件格式，降低后续扩展成本

**实现要点**：
- export_service 增加 formatter 适配（txt/md/json）
- API：`/api/projects/{name}/export/md`、`/md/{chapter_num}`、`/export/json`
- 文件名规范：`{project}-{format}.{ext}`，章节带 `{chapter_num}` 后缀

## Risks / Trade-offs

### Risk 1: Celery 任务与 LangGraph 检查点冲突
**风险**：Celery 任务重启后，LangGraph 检查点状态可能不一致
**缓解**：
- 任务开始时从文件系统重建状态
- 使用 orchestrator 的 resume_workflow() 方法
- 任务 ID 与项目名绑定

### Risk 2: WebSocket 连接不稳定
**风险**：长时间生成过程中 WebSocket 可能断开
**缓解**：
- 前端实现自动重连
- 进度状态存储在 Redis，可随时查询
- 提供 HTTP 轮询 fallback

### Risk 3: 生成任务取消不完整
**风险**：取消任务时 LLM 调用可能无法立即中断
**缓解**：
- 复用现有的 SIGINT 处理机制
- 设置 should_stop_early 标志
- 在节点边界检查停止标志

## Migration Plan

### 步骤 1：基础设施搭建
1. 添加 FastAPI/Celery 依赖到 pyproject.toml
2. 创建 docker-compose.yml (Redis)
3. 初始化 API 目录结构

### 步骤 2：核心 API 实现
1. 实现项目管理 API
2. 实现生成控制 API + Celery 任务（含 stop_at、单任务并发限制）
3. 实现 WebSocket 进度/日志推送 + Redis 进度/日志持久化 + HTTP fallback
4. 实现内容展示 API
5. 实现导出 API（TXT 首版 + 适配层为后续多格式做准备）
6. 实现回滚 API（清理 Redis active_task/进度）

### 步骤 3：前端开发
1. 初始化 React 项目
2. 实现项目管理页面
3. 实现生成控制页面（stop_at、断线重连、日志展示）
4. 实现内容阅读页面
5. 实现世界观/角色/大纲展示页面

### 步骤 4：集成测试
1. API 集成测试
2. 前后端联调
3. 生成流程端到端测试
4. 多格式导出与内容编辑回归测试

### Rollback 计划
- CLI 保留完整功能，可随时回退
- API 和前端独立部署，不影响现有功能

