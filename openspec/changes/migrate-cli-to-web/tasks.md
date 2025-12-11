## 1. 基础设施搭建

- [x] 1.1 添加后端依赖到 pyproject.toml (FastAPI, uvicorn, celery, redis, websockets)
- [x] 1.2 创建 docker-compose.yml 配置 Redis 服务
- [x] 1.3 创建 novelgen/api/ 目录结构 (main.py, deps.py, routes/, schemas/, websockets/)
- [x] 1.4 创建 novelgen/tasks/ 目录 (celery_app.py, generation_tasks.py)
- [x] 1.5 创建 novelgen/services/ 目录 (project_service.py, generation_service.py, export_service.py)
- [x] 1.6 初始化前端项目 (npm create vite frontend -- --template react-ts)
- [x] 1.7 配置前端依赖 (react-router-dom v6, zustand, axios, tailwindcss)

## 2. API 层实现 - 项目管理 (P0)

- [x] 2.1 实现 Pydantic 请求/响应 schemas (project.py, common.py)
- [x] 2.2 实现 project_service.py 封装项目 CRUD 操作
- [x] 2.3 实现 GET /api/projects 项目列表 API
- [x] 2.4 实现 POST /api/projects 创建项目 API
- [x] 2.5 实现 GET /api/projects/{name} 项目详情 API
- [x] 2.6 实现 DELETE /api/projects/{name} 删除项目 API
- [x] 2.7 实现 GET /api/projects/{name}/state 项目状态 API
- [x] 2.8 编写项目管理 API 测试

## 3. API 层实现 - 生成控制 (P0)

- [x] 3.1 实现 Celery 应用配置 (celery_app.py)
- [x] 3.2 实现生成任务 (generation_tasks.py) 封装 orchestrator 调用
- [x] 3.3 实现 generation_service.py 管理任务状态
- [x] 3.4 实现 POST /api/projects/{name}/generate 开始生成 API（支持 stop_at 参数）
- [x] 3.5 实现 POST /api/projects/{name}/generate/resume 恢复生成 API
- [x] 3.6 实现 POST /api/projects/{name}/generate/stop 停止生成 API
- [x] 3.7 实现 GET /api/projects/{name}/generate/status 生成状态 API
- [x] 3.8 实现 WebSocket /ws/projects/{name}/progress 进度推送
- [x] 3.9 编写生成控制 API 测试
- [x] 3.10 在 generation_service 中实现单项目单活跃任务约束（并发返回 409）
- [x] 3.11 将 active_task 与进度快照持久化到 Redis（用于断线重连与 HTTP fallback）
- [x] 3.12 实现 GET /api/projects/{name}/generate/progress 进度查询 HTTP fallback
- [x] 3.13 实现生成日志持久化与提取（WebSocket 推送 + GET /api/projects/{name}/generate/logs）
- [x] 3.14 stop_at/恢复/停止流程覆盖 Redis 状态清理与任务取消
- [x] 3.15 补充 stop_at/并发限制/进度日志的端到端测试用例

## 4. API 层实现 - 内容管理 (P0)

- [x] 4.1 实现 content schemas (content.py)
- [x] 4.2 实现 GET /api/projects/{name}/world 世界观 API
- [x] 4.3 实现 GET /api/projects/{name}/characters 角色 API
- [x] 4.4 实现 GET /api/projects/{name}/outline 大纲 API
- [x] 4.5 实现 GET /api/projects/{name}/chapters 章节列表 API
- [x] 4.6 实现 GET /api/projects/{name}/chapters/{num} 章节内容 API
- [x] 4.7 编写内容 API 测试

## 5. API 层实现 - 导出功能 (P0)

- [x] 5.1 实现 export_service.py 封装导出逻辑
- [x] 5.2 实现 GET /api/projects/{name}/export/txt 全书导出 API
- [x] 5.3 实现 GET /api/projects/{name}/export/txt/{chapter_num} 单章导出 API
- [x] 5.4 编写导出 API 测试

## 6. 前端实现 - 基础框架 (P0)

- [x] 6.1 配置 Tailwind CSS v3 和基础样式（颜色主题、字体）
- [x] 6.2 设置 React Router v6 路由结构（BrowserRouter, Routes, Route）
- [x] 6.3 创建 API 服务层 (services/api.ts, projectApi.ts)
- [x] 6.4 创建 Zustand store (projectStore.ts, generationStore.ts)
- [x] 6.5 创建基础布局组件 (Layout, Navbar, Sidebar)

## 7. 前端实现 - 项目管理页面 (P0)

- [x] 7.1 实现 ProjectList 页面 (项目卡片列表)
- [x] 7.2 实现 ProjectCard 组件
- [x] 7.3 实现 CreateProjectModal 创建项目弹窗
- [x] 7.4 实现项目搜索和筛选功能

## 8. 前端实现 - 生成控制页面 (P0)

- [x] 8.1 实现 WebSocket hook (useWebSocket.ts)
- [x] 8.2 实现 ProgressBar 进度条组件
- [x] 8.3 实现 LogViewer 日志查看组件
- [x] 8.4 实现 GenerationControl 页面 (开始/停止/恢复按钮)
- [x] 8.5 实现实时进度展示 (当前步骤、章节、场景)

## 9. 前端实现 - 内容阅读页面 (P0)

- [x] 9.1 实现 Reader 页面基础布局
- [x] 9.2 实现 ChapterList 章节选择器
- [x] 9.3 实现 ChapterReader 章节内容展示
- [x] 9.4 实现场景导航功能

## 10. 前端实现 - 项目详情页 (P0)

- [x] 10.1 实现 ProjectDetail 页面框架
- [x] 10.2 实现项目状态概览组件
- [x] 10.3 实现生成进度时间线组件

## 11. API 层实现 - 回滚功能 (P1)

- [x] 11.1 实现 POST /api/projects/{name}/rollback 回滚 API
- [x] 11.2 支持步骤级回滚参数
- [x] 11.3 支持章节级回滚参数
- [x] 11.4 支持场景级回滚参数
- [x] 11.5 编写回滚 API 测试
- [x] 11.6 回滚后清理 Redis 进度与 active_task 状态

## 12. 前端实现 - 内容展示页 (P1)

- [x] 12.1 实现 WorldView 世界观展示组件
- [x] 12.2 实现 CharacterList 角色列表组件
- [x] 12.3 实现 CharacterCard 角色卡片组件
- [x] 12.4 实现 OutlineTree 大纲树形组件

## 13. 前端实现 - 分步生成控制 (P1)

- [x] 13.1 实现步骤选择器组件
- [x] 13.2 实现 stop-at 参数支持
- [x] 13.3 更新 GenerationControl 页面
- [x] 13.4 WebSocket 断线自动重连 + HTTP 进度/日志 fallback 整合

## 14. API 层实现 - 内容编辑 (P2)

- [x] 14.1 实现 PUT /api/projects/{name}/world 更新世界观 API
- [x] 14.2 实现 PUT /api/projects/{name}/characters 更新角色 API
- [x] 14.3 实现 PUT /api/projects/{name}/outline 更新大纲 API
- [x] 14.4 实现 PUT /api/projects/{name}/chapters/{num} 更新章节 API（含场景内容更新）
- [x] 14.5 实现 DELETE /api/projects/{name}/chapters/{num} 删除章节/场景 API（软删或重建章节）
- [x] 14.6 编写内容编辑 API 测试（含乐观并发/校验失败场景）

## 15. 前端实现 - 内容编辑 (P2)

- [x] 15.1 实现 WorldEditor 世界观编辑器
- [x] 15.2 实现 CharacterEditor 角色编辑器
- [x] 15.3 实现 ChapterEditor 章节编辑器
- [x] 15.4 实现 OutlineEditor 大纲编辑器
- [x] 15.5 为编辑器提供保存/撤销/错误提示与并发保护

## 16. 前端实现 - 回滚功能 (P2)

- [x] 16.1 实现 RollbackModal 回滚确认弹窗
- [x] 16.2 实现回滚点选择器
- [x] 16.3 集成到项目详情页

## 17. 集成与测试

- [ ] 17.1 编写 API 集成测试
- [ ] 17.2 进行前后端联调测试
- [ ] 17.3 进行完整生成流程端到端测试
- [ ] 17.4 性能测试和优化

## 18. 文档与部署

- [x] 18.1 更新 README.md 添加 Web 应用使用说明
- [x] 18.2 编写 API 文档
- [x] 18.3 编写开发环境搭建指南

## 19. 导出增强 (P3)

- [x] 19.1 实现 GET /api/projects/{name}/export/md 与 /md/{chapter_num} Markdown 导出
- [x] 19.2 实现 GET /api/projects/{name}/export/json 结构化导出（全书/单章）
- [x] 19.3 在 export_service 中抽象导出格式适配层
- [x] 19.4 前端支持多格式导出入口（全书与单章）
- [x] 19.5 编写多格式导出测试（包含编码、文件名、空章节处理）

