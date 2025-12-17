# NovelGen 项目结构说明

本文档说明仓库目录结构、核心模块职责，以及 `projects/<project>` 下的落盘约定（JSON 真源 + checkpoint + 可选 Mem0/图谱）。

## 仓库结构（概览）

```
novel-gen/
  novelgen/
    cli.py              # Typer CLI（ng）
    agent/              # 对话式 Agent（ng chat）
    tools/              # Agent 工具注册与实现（workflow/graph/memory/preference）
    chains/             # 各阶段生成链（结构化输出）
    runtime/            # LangGraph 工作流、节点实现、编排器
    graph/              # Kùzu 图谱存储与更新（可选）
  projects/             # 每本小说一个项目目录（生成产物真源）
  docs/                 # 文档目录
  tests/                # 测试
  scripts/              # 运维/维护脚本
  openspec/             # OpenSpec 规格与变更管理
```

## 生成产物目录（projects/<project_id>/）

> 约定：**JSON 文件为真源**。LangGraph checkpoint、Mem0 向量与图谱都是“可重建/可降级”的辅助层。

常见文件：

```
projects/<project_id>/
  settings.json
  world.json
  theme_conflict.json
  characters.json
  outline.json
  consistency_reports.json
  chapter_memory.json
  workflow_checkpoints.db
  chapters/
    chapter_001_plan.json
    scene_001_001.json
    ...
    chapter_001.json
  data/
    vectors/            # Mem0/Chroma（可选）
    graph/              # Kùzu 图谱（可选）
```

## 核心模块职责

- `novelgen/runtime/workflow.py`：LangGraph `StateGraph` 定义（含章节循环/场景子图）
- `novelgen/runtime/nodes.py`：各节点实现（读写 JSON、调用 chains、写入 Mem0、更新图谱）
- `novelgen/runtime/orchestrator.py`：对外编排入口（CLI/脚本调用），并提供状态扫描、回滚、导出等
- `novelgen/chains/*.py`：每一步的提示词与结构化解析（Pydantic）
- `novelgen/runtime/mem0_manager.py`：Mem0 封装（偏好/实体状态/场景分块）
- `novelgen/graph/*`：Kùzu schema、写入与查询封装（从 `chapter_memory` 等增量入图）
- `novelgen/agent/chat.py`：对话式 REPL，会调用 `novelgen/tools/*` 执行动作

## 与 OpenSpec 的关系

OpenSpec 主要用于“新增能力/架构变更/破坏性改动”的提案与追踪，项目内说明见：

- `openspec/AGENTS.md`
- `openspec/project.md`

