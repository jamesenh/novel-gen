## Why

当前 NovelGen 项目仅提供 CLI 接口，用户交互体验受限，无法提供直观的项目管理、实时进度展示和内容可视化能力。将 CLI 功能迁移到 Web 应用可以显著提升用户体验，同时保留现有的核心生成逻辑和 LangGraph 工作流能力。

## What Changes

### 新增能力

- **Web API 层（FastAPI）**
  - 项目管理 API：列表、创建、删除、状态查询
  - 生成控制 API：开始/停止/恢复、stop_at 分步控制、回滚
  - 进度/日志：Redis 持久化、HTTP fallback、WebSocket 推送
  - 内容 API：世界观、角色、大纲、章节的 CRUD
  - 导出 API：TXT + 多格式导出（Markdown / JSON）
  - WebSocket 进度/日志推送

- **异步任务系统（Celery + Redis）**
  - 后台生成任务处理
  - 进度状态实时推送
  - 任务取消和恢复

- **Web 前端（React + TypeScript）**
  - 项目列表和管理页面
  - 生成控制和进度展示
  - 内容阅读器
  - 响应式布局

### 架构变化

- **BREAKING**: 新增 `novelgen/api/` 模块作为 API 层
- **BREAKING**: 新增 `novelgen/tasks/` 模块处理 Celery 任务
- **BREAKING**: 新增 `novelgen/services/` 封装业务逻辑供 API 调用
- **BREAKING**: 新增 `frontend/` 目录存放 React 应用
- 新增 Docker Compose 配置支持 Redis

### 复用现有模块

- 完全复用 `novelgen/chains/` 生成链
- 完全复用 `novelgen/runtime/workflow.py` LangGraph 工作流
- 完全复用 `novelgen/runtime/orchestrator.py` 编排器
- 复用 `novelgen/models.py` Pydantic 模型
- 保留 `novelgen/cli.py` 以便调试和向后兼容

## Impact

- **新增 specs**:
  - `web-api`: REST API 和 WebSocket 规范
  - `web-frontend`: 前端组件和页面规范
  - `web-generation-tasks`: Celery 任务规范

- **受影响的代码**:
  - `novelgen/api/` (新增)
  - `novelgen/tasks/` (新增)
  - `novelgen/services/` (新增)
  - `frontend/` (新增)
  - `docker-compose.yml` (新增)
  - `pyproject.toml` (添加 FastAPI/Celery 依赖)
  - `package.json` (新增前端依赖)

## 开发阶段

### 阶段一：基础框架 (P0)
- FastAPI 项目初始化
- Celery + Redis 集成
- 项目管理 API
- 基础前端框架

### 阶段二：核心功能 (P0)
- 生成控制 API + WebSocket
- stop_at 分步控制、单任务并发限制
- 进度/日志持久化与 HTTP fallback
- 内容展示 API
- 导出 API
- 前端主要页面

### 阶段三：增强功能 (P1)
- 回滚功能（步骤/章节/场景）
- 分步生成控制前端化
- 详细状态展示与断线重连（WebSocket + HTTP fallback）
- 世界观/角色/大纲展示页面

### 阶段四：高级功能 (P2/P3)
- 内容编辑（世界观/角色/大纲/章节/场景）
- 多格式导出（Markdown / JSON）

