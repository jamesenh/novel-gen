# NovelGen Web 应用功能规划

> **目标**：Web 应用将完全替代现有 CLI，提供完整的小说生成和管理功能。

## 技术决策摘要

| 类别 | 选择 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | 异步支持、自动 OpenAPI 文档 |
| 前端框架 | React + TypeScript | 组件化、类型安全 |
| 任务队列 | Celery + Redis | 异步生成任务处理 |
| 容器化 | Docker | Redis 和数据库容器化，应用本地调试 |
| 用户模式 | 单用户 | 暂不支持多用户 |
| 生成方式 | 异步 | WebSocket 推送进度 |
| 用户认证 | 预留 | 代码结构预留，后续实现 |

---

## 一、当前 CLI 功能概览

### 1.1 核心生成流程（6步）

| 步骤 | 功能 | 输入 | 输出 |
|------|------|------|------|
| 1. 世界观生成 | 根据描述生成完整世界设定 | world_description | world.json |
| 2. 主题冲突 | 生成核心主题与冲突 | theme_description + world | theme_conflict.json |
| 3. 角色创建 | 生成主角、反派、配角 | world + theme_conflict | characters.json |
| 4. 大纲生成 | 生成故事结构与章节摘要 | 上述所有 | outline.json |
| 5. 章节计划 | 每章拆分为多个场景 | outline | chapter_XXX_plan.json |
| 6. 场景生成 | 生成实际小说文本 | 章节计划 + 上下文 | chapter_XXX.json |

### 1.2 辅助功能

| 功能 | 描述 |
|------|------|
| 一致性检查 | 检测生成内容的逻辑/角色一致性 |
| 章节修订 | 根据一致性报告自动/手动修订 |
| 动态章节扩展 | 评估剧情进度，动态扩展大纲 |
| 断点续跑 | LangGraph 检查点支持中断恢复 |
| 导出 | 导出为 txt 格式 |
| 回滚 | 回滚到指定步骤/章节 |

### 1.3 CLI 命令

```bash
ng init <project>    # 创建项目
ng run <project>     # 运行生成
ng resume <project>  # 恢复生成
ng status <project>  # 查看状态
ng state <project>   # 详细状态
ng export <project>  # 导出
ng rollback <project> --step/--chapter  # 回滚
```

---

## 二、Web 应用功能拆分

### 2.1 项目管理模块

**适合 Web 的功能：**
- ✅ 项目列表展示（所有已创建项目）
- ✅ 创建新项目（交互式表单）
- ✅ 删除项目
- ✅ 项目详情页面

**Web 展示优势：**
- 可视化项目卡片
- 搜索和筛选
- 批量操作

### 2.2 生成流程控制模块

**适合 Web 的功能：**
- ✅ 一键生成整本小说
- ✅ 分步生成（可选停止点）
- ✅ 实时进度展示
- ✅ 生成日志查看
- ✅ 中断/恢复生成
- ✅ 回滚操作（选择回滚点）

**技术考虑：**
- WebSocket 实时推送进度
- 后台任务队列处理生成
- 生成状态持久化

### 2.3 内容展示模块

**适合 Web 的功能：**

**世界观展示：**
- ✅ 结构化展示世界设定各字段
- ✅ 编辑和重新生成

**角色展示：**
- ✅ 角色卡片列表
- ✅ 角色关系图谱（可视化）
- ✅ 角色详情页

**大纲展示：**
- ✅ 故事结构概览
- ✅ 章节列表（可折叠）
- ✅ 章节依赖可视化

**章节阅读：**
- ✅ 章节选择器
- ✅ 场景导航
- ✅ 阅读进度追踪
- ✅ 全书阅读模式

### 2.4 编辑与修订模块

**适合 Web 的功能：**
- ✅ 世界观/角色/大纲在线编辑
- ✅ 一致性问题列表展示
- ✅ 修订候选对比（diff view）
- ✅ 接受/拒绝修订
- ✅ 手动编辑章节内容

### 2.5 导出模块

**适合 Web 的功能：**
- ✅ 导出为 TXT（单章/全书）
- ✅ 导出为 EPUB（需新增）
- ✅ 导出为 PDF（需新增）
- ✅ 下载生成文件

### 2.6 统计与分析模块

**适合 Web 的功能：**
- ✅ 项目生成统计
- ✅ 字数统计（每章/总计）
- ✅ 生成时间统计
- ✅ 一致性问题分布图表

---

## 三、技术架构

### 3.1 后端架构（FastAPI）

```
novelgen/
├── api/                        # API 层
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── deps.py                 # 依赖注入
│   ├── auth.py                 # 用户认证（预留，暂不实现）
│   ├── routes/                 # 路由模块
│   │   ├── __init__.py
│   │   ├── projects.py         # 项目管理 API
│   │   ├── generation.py       # 生成控制 API
│   │   ├── content.py          # 内容查看/编辑 API
│   │   ├── export.py           # 导出 API
│   │   └── stats.py            # 统计 API
│   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── generation.py
│   │   ├── content.py
│   │   └── common.py
│   └── websockets/             # WebSocket 处理
│       ├── __init__.py
│       └── progress.py         # 生成进度推送
├── tasks/                      # Celery 后台任务
│   ├── __init__.py
│   ├── celery_app.py           # Celery 应用配置
│   ├── generation_tasks.py     # 生成任务定义
│   └── worker_control.py       # Worker 控制工具（优雅停机）
└── services/                   # 业务逻辑层（复用现有代码）
    ├── __init__.py
    ├── project_service.py      # 项目管理服务
    ├── generation_service.py   # 生成服务（封装 orchestrator）
    └── export_service.py       # 导出服务
```

**核心组件：**

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 异步 REST API + WebSocket |
| 任务队列 | Celery | 异步生成任务处理 |
| 消息代理 | Redis | Celery broker + 结果存储 |
| 数据存储 | 现有 JSON + SQLite | 复用现有持久化机制 |

**Celery Worker 控制：**

Worker 启动推荐使用 `--pool=solo` 以确保信号能正确传递：
```bash
celery -A novelgen.tasks.celery_app worker -l info -Q generation --pool=solo
```

Worker 停机提供专用 CLI 工具（解决 Ctrl+C 无法停止的问题）：
```bash
# 优雅停机（等待任务检测停止标志后退出）
python -m novelgen.tasks.worker_control shutdown

# 强制停机（立即终止任务）
python -m novelgen.tasks.worker_control shutdown --force
```

停机流程会：
1. 设置停止标志通知运行中的工作流
2. 将活跃项目状态标记为 "stopping"
3. 广播 shutdown 信号给所有 Worker
4. 等待 Worker 完成清理后退出（LangGraph 检查点已持久化）

### 3.2 前端架构（React + TypeScript）

```
frontend/
├── public/
├── src/
│   ├── main.tsx                # 应用入口
│   ├── App.tsx                 # 根组件
│   ├── pages/                  # 页面组件
│   │   ├── ProjectList/        # 项目列表页
│   │   ├── ProjectDetail/      # 项目详情页
│   │   ├── Generation/         # 生成控制页
│   │   ├── Reader/             # 阅读器页
│   │   ├── Editor/             # 编辑器页
│   │   └── Settings/           # 设置页
│   ├── components/             # 通用组件
│   │   ├── common/             # 基础组件
│   │   ├── project/            # 项目相关组件
│   │   │   ├── ProjectCard.tsx
│   │   │   └── ProjectForm.tsx
│   │   ├── content/            # 内容展示组件
│   │   │   ├── WorldCard.tsx
│   │   │   ├── CharacterCard.tsx
│   │   │   ├── OutlineTree.tsx
│   │   │   └── ChapterReader.tsx
│   │   └── generation/         # 生成相关组件
│   │       ├── ProgressBar.tsx
│   │       └── LogViewer.tsx
│   ├── hooks/                  # 自定义 Hooks
│   │   ├── useProjects.ts
│   │   ├── useGeneration.ts
│   │   └── useWebSocket.ts
│   ├── services/               # API 调用服务
│   │   ├── api.ts              # Axios 实例
│   │   ├── projectApi.ts
│   │   ├── generationApi.ts
│   │   └── contentApi.ts
│   ├── store/                  # 状态管理（Zustand/Redux）
│   │   ├── projectStore.ts
│   │   └── generationStore.ts
│   ├── types/                  # TypeScript 类型定义
│   │   ├── project.ts
│   │   ├── content.ts
│   │   └── generation.ts
│   └── utils/                  # 工具函数
├── package.json
├── tsconfig.json
└── vite.config.ts              # Vite 构建配置
```

### 3.3 数据流架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React)                          │
├─────────────────────────────────────────────────────────────┤
│  用户操作 → API 调用 → 状态更新 → UI 渲染                      │
│                ↑                                             │
│                │ WebSocket (进度推送)                         │
└────────────────┼────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     后端 (FastAPI)                           │
├─────────────────────────────────────────────────────────────┤
│  REST API ←→ Services ←→ Orchestrator ←→ LangGraph          │
│      │                                                       │
│      └──→ Celery Task ──→ Redis (Broker)                    │
│                │                                             │
│                └──→ WebSocket 推送进度                        │
└─────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     存储层                                   │
├─────────────────────────────────────────────────────────────┤
│  projects/           # JSON 文件（现有）                      │
│  *.db               # SQLite 检查点（现有）                   │
│  data/vectors/      # ChromaDB 向量存储（Mem0）               │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    开发环境部署                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐                      │
│  │   Frontend   │     │   Backend    │    ← 本地运行         │
│  │  (npm run    │     │  (uvicorn)   │                      │
│  │    dev)      │     │              │                      │
│  └──────┬───────┘     └──────┬───────┘                      │
│         │                    │                               │
│         └────────┬───────────┘                               │
│                  │                                           │
│         ┌────────▼────────┐                                  │
│         │  Docker Compose │    ← 容器化                      │
│         ├─────────────────┤                                  │
│         │  ┌───────────┐  │                                  │
│         │  │   Redis   │  │    端口: 6379                    │
│         │  └───────────┘  │                                  │
│         └─────────────────┘                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**docker-compose.yml 示例：**

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

---

## 四、功能开发优先级

### P0：基础功能（必须）

| 序号 | 功能 | 说明 | CLI 对应 |
|------|------|------|----------|
| 1 | 项目列表 | 展示所有项目，支持搜索 | `ng status` |
| 2 | 创建项目 | 表单输入世界观/主题描述 | `ng init` |
| 3 | 删除项目 | 确认后删除项目 | - |
| 4 | 一键生成 | 触发完整生成流程 | `ng run` |
| 5 | 生成进度 | WebSocket 实时推送 | CLI 日志输出 |
| 6 | 断点续跑 | 从中断处恢复 | `ng resume` |
| 7 | 内容阅读 | 展示生成的小说内容 | 文件查看 |
| 8 | TXT 导出 | 导出为文本文件 | `ng export` |

### P1：增强功能（重要）

| 序号 | 功能 | 说明 | CLI 对应 |
|------|------|------|----------|
| 9 | 分步生成 | 可选择停止点 | `ng run --stop-at` |
| 10 | 生成日志 | 详细日志查看 | `--verbose` |
| 11 | 世界观展示 | 结构化展示设定 | 查看 JSON |
| 12 | 角色展示 | 角色卡片列表 | 查看 JSON |
| 13 | 大纲展示 | 章节树形结构 | 查看 JSON |
| 14 | 项目状态 | 详细生成状态 | `ng state` |

### P2：高级功能（增强）

| 序号 | 功能 | 说明 | CLI 对应 |
|------|------|------|----------|
| 15 | 内容编辑 | 在线编辑各类内容 | 手动编辑 JSON |
| 16 | 回滚功能 | 回滚到指定状态 | `ng rollback` |
| 17 | 一致性管理 | 查看/处理一致性问题 | 查看报告 |
| 18 | 修订对比 | Diff 视图对比修订 | 对比文件 |
| 19 | 多候选选择 | 世界观/主题多候选 | 新功能 |

### P3：扩展功能（可选）

| 序号 | 功能 | 说明 |
|------|------|------|
| 20 | 角色关系图谱 | 可视化角色关系 |
| 21 | 统计仪表板 | 字数、时间等统计 |
| 22 | EPUB 导出 | 电子书格式导出 |
| 23 | PDF 导出 | PDF 格式导出 |
| 24 | 项目模板 | 预设世界观模板 |

---

## 五、API 设计概览

### 5.1 项目管理 API

```
GET    /api/projects              # 获取项目列表
POST   /api/projects              # 创建新项目
GET    /api/projects/{name}       # 获取项目详情
DELETE /api/projects/{name}       # 删除项目
GET    /api/projects/{name}/state # 获取项目状态
```

### 5.2 生成控制 API

```
POST   /api/projects/{name}/generate         # 开始生成
POST   /api/projects/{name}/generate/resume  # 恢复生成
POST   /api/projects/{name}/generate/stop    # 停止生成
GET    /api/projects/{name}/generate/status  # 获取生成状态
POST   /api/projects/{name}/rollback         # 回滚操作
```

### 5.3 内容 API

```
GET    /api/projects/{name}/world            # 获取世界观
PUT    /api/projects/{name}/world            # 更新世界观
GET    /api/projects/{name}/characters       # 获取角色
PUT    /api/projects/{name}/characters       # 更新角色
GET    /api/projects/{name}/outline          # 获取大纲
GET    /api/projects/{name}/chapters         # 获取章节列表
GET    /api/projects/{name}/chapters/{num}   # 获取章节内容
PUT    /api/projects/{name}/chapters/{num}   # 更新章节内容
```

### 5.4 导出 API

```
GET    /api/projects/{name}/export/txt                # 导出全书 TXT
GET    /api/projects/{name}/export/txt/{chapter_num}  # 导出单章 TXT
```

### 5.5 WebSocket

```
WS     /ws/projects/{name}/progress   # 生成进度推送
```

---

## 六、用户认证（预留）

> 当前版本为单用户模式，用户认证代码结构预留但不实现具体逻辑。

### 预留文件结构

```
novelgen/api/
├── auth.py                 # 认证逻辑（预留空实现）
├── deps.py                 # 依赖注入（包含 get_current_user）
└── routes/
    └── auth.py             # 认证路由（预留）
```

### 预留接口

```python
# api/auth.py
async def get_current_user():
    """获取当前用户（预留，当前返回默认用户）"""
    return {"user_id": "default", "username": "local_user"}

# 后续扩展：
# - JWT Token 认证
# - 用户注册/登录
# - 权限控制
```

---

## 七、开发计划

### 第一阶段：基础框架搭建

1. 后端 FastAPI 项目初始化
2. Celery + Redis 集成
3. 前端 React + TypeScript 项目初始化
4. Docker Compose 配置（Redis）
5. API 基础结构搭建

### 第二阶段：P0 功能实现

1. 项目管理 API + 页面
2. 生成控制 API + Celery 任务
3. WebSocket 进度推送
4. 内容阅读页面
5. 导出功能

### 第三阶段：P1 功能实现

1. 分步生成控制
2. 生成日志查看
3. 世界观/角色/大纲展示页面
4. 项目状态详情页

### 第四阶段：P2 & P3 功能

1. 内容编辑功能
2. 回滚功能
3. 一致性管理
4. 扩展功能（图谱、统计、多格式导出）

