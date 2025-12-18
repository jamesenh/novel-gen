# Novel-Gen CLI 使用说明

本项目提供一个命令行工具 `novel-gen`（推荐）和一个等价的模块入口 `python -m app.main`。

总体 MVP 任务清单：`docs/MVP_TASKS.md`

## 0. 约定与目录

- 项目资产默认落在：`projects/<project_name>/`
- `--project/-p` 是**全局参数**，必须写在子命令（`init/run/continue`）之前

示例：

- ✅ `novel-gen -p 穿越唐朝 init`
- ❌ `novel-gen init -p 穿越唐朝`（会报 `unrecognized arguments`）

## 1. 安装与运行方式

> 说明：本项目推荐使用 `uv` 管理与运行（虚拟环境在 `.venv/` 中）。

### 1.1 安装为命令（推荐）

在仓库根目录执行（可用 `python3` 替代 `python`）：

```bash
python -m pip install -e .
novel-gen -h
```

如果你使用 `uv`，也可以：

```bash
uv run novel-gen -h
```

### 1.2 不安装，直接用模块入口

在仓库根目录执行：

```bash
python -m app.main -h
```

说明：不建议直接 `python app/main.py ...`，因为这会受 `PYTHONPATH` 影响导致 `ModuleNotFoundError: No module named 'app'`。

## 2. 全局参数

### `--project / -p <name>`

指定项目名（对应 `projects/<name>/`）。如果不传，则从环境变量 `PROJECT_NAME` 读取。

## 3. 子命令

### 3.1 `init`：初始化项目

用途：创建新项目目录和基础文件。

命令：

```bash
novel-gen -p <project_name> init
```

会创建（若不存在）：

- `projects/<project_name>/settings.json`
- `projects/<project_name>/chapters/`
- `projects/<project_name>/data/`

返回码：

- `0`：初始化成功
- `1`：项目目录已存在

### 3.2 `run`：从头运行生成工作流

用途：生成章节（按工作流：plan → write → audit → revise/store → next）。

命令：

```bash
novel-gen -p <project_name> run
novel-gen -p <project_name> run -c 3
novel-gen -p <project_name> run -c 3 --prompt "你想要的初始提示词"
```

参数：

- `--chapters / -c <n>`：生成章节数；不传则使用配置 `NUM_CHAPTERS`（默认 1）
- `--prompt <text>`：初始提示词；不传则为空字符串

背景资产 bootstrap（可用级 MVP）：

- 若项目缺少 `world.json/characters.json/theme_conflict.json/outline.json`，则必须提供 `--prompt`；
  `run` 会先自动生成这些背景资产再进入章节循环。
- 若这些文件已存在，则默认只加载复用（不会静默覆写）。

输出（每章写入一次，原子捆绑写入）：

- `projects/<project_name>/chapters/chapter_XXX_plan.json`
- `projects/<project_name>/chapters/chapter_XXX.json`
- `projects/<project_name>/consistency_reports.json`（同步更新）
- `projects/<project_name>/chapter_memory.json`（同步更新）

返回码：

- `0`：生成完成且无需人工审核
- `1`：项目不存在（需要先 `init`）
- `2`：生成完成但需要人工审核（例如修订轮次达到上限）

### 3.3 `continue`：从检查点继续（断点续跑）

用途：从 `projects/<project_name>/workflow_checkpoints.db` 恢复最新 checkpoint 并继续执行。

命令：

```bash
novel-gen -p <project_name> continue
```

说明：

- 若没有任何 checkpoint，会提示先运行 `run`
- 若最新 checkpoint 已在 END（工作流已完成），会提示“无需继续”

### 3.4 `ask`：检索项目资产并综合回答（无向量库）

用途：对项目资产做关键词检索，输出摘录与来源列表（便于追溯）。

命令：

```bash
novel-gen -p <project_name> ask --question "某个角色的动机是什么？"
```

## 4. 常用环境变量（可写入 `.env`）

`python-dotenv` 会自动加载仓库根目录的 `.env`（若已安装依赖）。

- `PROJECT_NAME`：默认项目名（不传 `--project` 时使用）
- `AUTHOR`：作者名（写入 `settings.json`）
- `NUM_CHAPTERS`：默认章节数

模型/服务相关：

- `MODEL_PROVIDER`（默认 `openai`）
- `MODEL_NAME`（默认 `gpt-4`）
- `MODEL_BASE_URL`（可选）
- `MODEL_API_KEY`（可选）

审计/修订阈值：

- `QA_BLOCKER_MAX`（默认 `0`，必须为 0 才能推进下一章）
- `QA_MAJOR_MAX`（默认 `3`）
- `MAX_REVISION_ROUNDS`（默认 `3`）

## 5. 常见问题

### 5.1 `unrecognized arguments: -p ...`

原因：`-p/--project` 是全局参数，必须放在子命令前。

改成：

```bash
novel-gen -p 穿越唐朝 init
```

### 5.2 `Project name must be specified ...`

原因：没有提供 `--project/-p`，也没有设置 `PROJECT_NAME`。

### 5.3 `ModuleNotFoundError: No module named 'app'`

原因：用 `python app/main.py` 直接运行导致包导入路径不对。

改用：

```bash
python -m app.main ...
```
