# 📘 NovelGen — 基于 LangChain 的 AI 小说生成器

NovelGen 是一个 从零开始构建 AI 自动写小说的项目，目标不仅是生成完整小说，更是用于 学习 LangChain、AI 架构设计、LLM 提示工程。

本项目将小说创作过程拆解为多个结构化步骤：
从世界观 → 角色 → 梗概 → 大纲 → 场景 → 正文，全流程全部由 AI 自动生成，并支持记忆、修订。

## 📚 文档入口

- 文档索引：`docs/README.md`
- 快速开始：`docs/QUICKSTART.md`
- 环境变量配置：`docs/ENV_SETUP.md`
- 项目结构说明：`docs/STRUCTURE.md`
- 生成流程全解（LangGraph + Mem0 + 图谱落盘）：`docs/小说生成完整流程说明.md`
- 对话式 Agent：`docs/对话式Agent使用指南.md`
- Kùzu 知识图谱：`docs/知识图谱使用指南.md`

## ✨ 项目亮点

📚 完整的小说生成工作流

🧱 严格结构化的输出（Pydantic + JSON）

⚙️ 全流程基于 **LangChain + LangGraph** 构建，可拓展性强，支持复杂工作流

🔁 支持章节摘要、全书摘要、场景级生成

🔍 内置"文本自检"，避免设定冲突

🧩 模块化设计，可按需替换链路，每个步骤作为LangGraph节点独立运行

🧠 **Mem0 智能记忆层**（可选）：
   - **用户记忆**：支持主动设置写作偏好和风格，自动注入生成上下文
   - **实体记忆**：自动管理角色状态，智能合并和更新
   - **零部署成本**：复用现有 ChromaDB，无需额外向量数据库

🔗 **Kùzu 知识图谱**（可选）：
   - **角色/关系/事件**：结构化存储角色、关系和事件信息
   - **嵌入式数据库**：每项目独立存储，无需外部服务
   - **智能查询**：支持角色信息、关系和事件的快速检索

💬 **对话式 Agent**：
   - **自然语言交互**：通过对话驱动小说生成、查询和设置
   - **斜杠命令**：`/run`、`/status`、`/whois` 等快捷命令
   - **安全确认**：生成类动作默认需要确认，可切换 `/auto on|off`

🔧 非常适合学习：
   - LangChain 1.0+：Runnable、PromptTemplate、Structured Output、VectorStore
   - LangGraph 1.0+：Stateful workflows、graph-based orchestration、state management
   - Mem0：智能记忆管理、自动去重、冲突解决
   - Kùzu：嵌入式图数据库、Cypher 查询语言

🔬 支持 checkpointing 和状态持久化，可中途暂停/恢复生成

## 🧩 项目目录结构
```
novelgen/
  novelgen/
    cli.py                # ng 命令入口（Typer）
    config.py             # 项目配置 & 环境变量
    models.py             # Pydantic 数据结构
    llm.py                # LangChain LLM 初始化与统一配置
    chains/
        world_chain.py
        theme_conflict_chain.py
        characters_chain.py
        outline_chain.py
        chapters_plan_chain.py
        scene_text_chain.py
    runtime/
      orchestrator.py      # 编排器（兼容 API + 调度 LangGraph）
      workflow.py          # LangGraph 工作流定义
      nodes.py             # LangGraph 节点实现
      consistency.py       # 一致性检查
      memory.py            # 章节记忆生成
      mem0_manager.py      # Mem0 记忆层封装
    tools/                 # 对话式 Agent 工具集
    agent/                 # 对话式 Agent（ng chat）
    graph/                 # Kùzu 图谱（可选）
  projects/
    demo_001/
      settings.json
      world.json
      characters.json
      outline.json
      chapters/
        chapter_001_plan.json
        scene_001_001.json
        chapter_001.json
```

## ✅ 当前已实现（概览）

- LangGraph 状态工作流：支持断点续跑（SQLite checkpoint）与章节循环/场景子循环
- 动态扩展大纲：根据剧情进度继续生成后续章节（可设置 max_chapters）
- 一致性检测 + 自动修订（可选策略）
- Mem0 记忆层（可选）：项目偏好注入 + 角色状态 + 场景向量检索
- Kùzu 知识图谱（可选）：角色/关系/事件查询，支持 `ng graph ...` 与 `/whois` 等
- 对话式 Agent：`ng chat` + 斜杠命令 + 安全确认

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

详细的环境配置说明请参考 `docs/ENV_SETUP.md`。

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

#### 4. 启用知识图谱（可选）

Kùzu 是一个嵌入式图数据库，用于存储和查询角色、关系和事件。

在 `.env` 文件中添加：

```bash
# 启用知识图谱（默认开启）
NOVELGEN_GRAPH_ENABLED=true
```

**特性**：
- ✅ 零部署：嵌入式数据库，无需外部服务
- ✅ 项目独立：每个项目拥有独立的图谱数据
- ✅ 自动更新：章节完成后自动更新图谱
- ✅ 丰富查询：支持角色、关系、事件的复杂查询

图谱数据存储在 `projects/<项目名>/data/graph` 目录下。

## ▶️ 运行示例

### 方式一：CLI 命令
```bash
# 初始化新项目
ng init my_novel

# 运行完整工作流
ng run my_novel

# 从断点恢复
ng resume my_novel

# 查看项目状态
ng status my_novel
```

### 方式二：对话式 Agent
```bash
# 启动对话会话
ng chat my_novel

# 在对话中使用斜杠命令
> /status                   # 查看项目状态
> /whois 主角名             # 查询角色信息
> /relations 角色A --with 角色B  # 查询关系
> /events 主角名            # 查询角色参与的事件
> /run                      # 开始生成
> /resume                   # 从断点继续生成
> /setpref 轻松幽默、少形容词、多心理描写  # 设置写作偏好（当前默认写入 writing_style）
> /prefs                    # 查看当前项目偏好
> /auto on                  # 开启自动确认
> /exit                     # 退出会话
```

### 方式三：图谱管理
```bash
# 重建知识图谱
ng graph rebuild my_novel

# 查询角色信息
ng graph whois my_novel 林风

# 查询角色关系
ng graph relations my_novel 林风

# 查询事件
ng graph events my_novel 林风

# 查看图谱统计
ng graph stats my_novel
```

### 方式四：Python API
```python
from novelgen.runtime.orchestrator import NovelOrchestrator

orchestrator = NovelOrchestrator(project_name="my_novel")
orchestrator.run_workflow()
```

## 🧠 后续计划（中长篇扩展）

- Web 应用（当前仅有规划文档与前端产物）：`docs/web_app_planning.md`
- 对话式 Agent：更强的意图识别、工具规划与多轮信息补齐
- 图谱：更细粒度证据引用与更丰富查询（关系演化、事件链路）
