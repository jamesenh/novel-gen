# 📘 NovelGen — 基于 LangChain 的 AI 小说生成器

NovelGen 是一个 从零开始构建 AI 自动写小说的项目，目标不仅是生成完整小说，更是用于 学习 LangChain、AI 架构设计、LLM 提示工程。

本项目将小说创作过程拆解为多个结构化步骤：
从世界观 → 角色 → 梗概 → 大纲 → 场景 → 正文，全流程全部由 AI 自动生成，并支持记忆、修订。

## ✨ 项目亮点

📚 完整的小说生成工作流

🧱 严格结构化的输出（Pydantic + JSON）

⚙️ 全流程基于 **LangChain + LangGraph** 构建，可拓展性强，支持复杂工作流

🔁 支持章节摘要、全书摘要、场景级生成

🔍 内置"文本自检"，避免设定冲突

🧩 模块化设计，可按需替换链路，每个步骤作为LangGraph节点独立运行

🧠 **Mem0 智能记忆层**（可选）：
   - **用户记忆**：预留功能框架，支持主动设置写作偏好和风格
   - **实体记忆**：自动管理角色状态，智能合并和更新
   - **零部署成本**：复用现有 ChromaDB，无需额外向量数据库

🔧 非常适合学习：
   - LangChain 1.0+：Runnable、PromptTemplate、Structured Output、VectorStore
   - LangGraph 1.0+：Stateful workflows、graph-based orchestration、state management
   - Mem0：智能记忆管理、自动去重、冲突解决

🔬 支持 checkpointing 和状态持久化，可中途暂停/恢复生成

## 🧩 项目目录结构
```
novelgen/
  novelgen/
    config.py             # settings.json 加载 & 校验
    models.py             # 所有数据结构(Pydantic)
    llm.py                # LangChain LLM 初始化
    chains/
        world_chain.py
        theme_conflict_chain.py
        characters_chain.py
        outline_chain.py
        chapters_plan_chain.py
        scene_text_chain.py
      runtime/
        orchestrator.py     # 当前主流程调度（将逐步迁移到LangGraph）
        workflow.py         # LangGraph工作流定义（新的主流程调度）
        summary.py          # 章节/全书摘要
        revision.py         # 修订机制
  projects/
    demo_001/
      settings.json
      world.json
      characters.json
      outline.json
      chapters_plan.json
      chapters/
        ch01.json
        ch01.md
```

## 🚀 开发目标（MVP 阶段）

能从 settings.json → world.json

能从 world → characters

能从 characters → outline

能生成章节计划（chapters_plan.json）

能生成至少 1–2 章正文（简单版，不含自检）

### 📦 安装

#### 1. 安装依赖
```bash
pip install -r requirements.txt
```

或者使用 uv：

```bash
uv sync
```

#### 2. 配置环境变量

**手动设置：**
```bash
# 复制环境变量模板
cp .env.template .env

# 编辑 .env 文件，填入你的 OpenAI API Key
# OPENAI_API_KEY=sk-your-actual-api-key-here
```

详细的环境配置说明请参考 [ENV_SETUP.md](ENV_SETUP.md)。

#### 3. 启用 Mem0（可选）

Mem0 是一个智能记忆层，可以学习用户的写作偏好并自动管理角色状态。

在 `.env` 文件中添加：

```bash
# 启用 Mem0
MEM0_ENABLED=true

# OpenAI API Key（必需，用于 Embedding）
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**特性**：
- ✅ 零额外部署：复用现有 ChromaDB
- ✅ 用户偏好：预留功能框架，支持主动设置写作偏好
- ✅ 智能管理：自动合并和更新角色状态
- ✅ 向后兼容：禁用后不影响现有功能

详细配置请参考 [Mem0 设置指南](docs/mem0-setup.md)。

## ▶️ 运行示例
python -m novelgen.runtime.orchestrator \
  --project projects/demo_001 \
  --steps world,characters,outline,chapters_plan,chapters

## 🧠 后续计划（中长篇扩展）

章节摘要 + 全书摘要

VectorStore + 上下文检索

自检链：一致性、称谓、角色、世界观规则

修订机制（局部修改 → 自动影响范围）

## 🌐 Web 应用快速上手

### 后端（FastAPI）
```bash
# 确保 Redis 已就绪（可用 docker-compose up -d redis）
UV_CACHE_DIR=.uv-cache uv run uvicorn novelgen.api.main:app --reload
# 默认监听 http://127.0.0.1:8000
```

### 前端（Vite + React）
```bash
cd frontend
npm install
npm run dev  # 默认 http://127.0.0.1:5173
```

### 常用环境变量
- `OPENAI_API_KEY`：必填，LLM 调用
- `REDIS_URL`：Redis 连接串，默认 `redis://localhost:6379/0`
- `NOVELGEN_PROJECTS_DIR`：项目输出目录，默认 `projects`
- `MEM0_ENABLED`：是否启用 Mem0 记忆层

### 关键 API（摘要）
- 项目管理：`GET/POST /api/projects`，`GET/DELETE /api/projects/{name}`，`GET /api/projects/{name}/state`
- 生成控制：`POST /api/projects/{name}/generate|resume|stop`，`GET /generate/status|progress|logs`
- 内容读取：`GET /api/projects/{name}/world|characters|outline|chapters|chapters/{num}`
- 内容编辑：`PUT /api/projects/{name}/world|characters|outline|chapters/{num}`，`DELETE /chapters/{num}[?scene=]`
- 回滚：`POST /api/projects/{name}/rollback`（step/chapter/scene）
- 导出：`GET /api/projects/{name}/export/txt|md|json` 以及单章导出 `/.../{chapter_num}`

更多细节见 `docs/web_api.md`。