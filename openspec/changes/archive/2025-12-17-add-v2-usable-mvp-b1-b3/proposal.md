## Why

当前 v2 baseline 已能跑通 “plan → write → audit → revise → store” 的最小闭环，但仍停留在“能跑”而非“能用”的水平：
- 无法从中断处继续（`continue` 仍为占位），难以日常迭代长篇
- `plan_chapter` / `write_chapter` / `apply_patch` 为 stub，无法形成真实生成与收敛修订
- 缺少“上下文检索与 context pack”，插件与生成链路无法稳定获取项目知识，从而难以做一致性与综合问答

需要把 `docs/MVP_TASKS.md` 的 **B1-B3** 作为下一阶段的“可用级 MVP”落地目标，并在不引入向量库的前提下实现可复现、可测试的上下文检索基线。

## What Changes

（对应 `docs/MVP_TASKS.md` 的 B1-B3）

## 背景与动机
当前 v2 baseline 已能跑通 “plan → write → audit → revise → store” 的最小闭环，但仍停留在“能跑”而非“能用”的水平：
- 无法从中断处继续（`continue` 仍为占位），难以日常迭代长篇
- `plan_chapter` / `write_chapter` / `apply_patch` 为 stub，无法形成真实生成与收敛修订
- 缺少“上下文检索与 context pack”，插件与生成链路无法稳定获取项目知识，从而难以做一致性与综合问答

需要把 `docs/MVP_TASKS.md` 的 **B1-B3** 作为下一阶段的“可用级 MVP”落地目标，并在不引入向量库的前提下实现可复现、可测试的上下文检索基线。

## 变更内容（对应 `docs/MVP_TASKS.md` 的 B1-B3）
- B1：实现 `continue`（断点续跑）：基于 `projects/<project>/workflow_checkpoints.db` 恢复并继续执行，并提供幂等写盘策略。
- B2：替换 stub 的生成链路：
  - `plan_chapter` 生成可执行的章节计划（至少包含场景计划）
  - `write_chapter` 生成非占位的章节正文（至少包含一个有内容的场景，`word_count` 可计算）
  - `apply_patch` 基于 `issues[].fix_instructions` 实施最小改动修订，推动 blocker 收敛或进入人工审核
- B3：实现上下文检索与 context pack（不引入向量库）：
  - 从 `world/characters/theme_conflict/outline/chapters/chapter_memory/consistency_reports` 等资产抽取可检索文本
  - 使用 SQLite FTS5 做关键词检索（或在缺省时回退到无索引的简易检索）
  - 组装稳定 schema 的 `context_pack`，供 plan/write/audit/插件复用
  - 提供一个“检索项目文档综合回答”的入口（例如 `novel-gen ask`），输出 answer + sources

## 用户流程（计划 UX）

> 目标：用户只提供一个**简短提示词**，`run` 在必要时自动扩写并生成背景资产，然后进入按章生成与审计闭环。

### 1) 初始化项目

```bash
python -m app.main -p <projectID> init
```

预期输出（示例）：

```text
Initialized project '<projectID>' at .../projects/<projectID>
```

### 2) 首次运行：自动生成背景资产 + 生成章节

> 注：当前 CLI 参数形式为 `run --prompt "<text>"`（不是位置参数）。

```bash
python -m app.main -p <projectID> run -c 1 --prompt "完全架空的修仙世界,整个世界分为3界(人界,灵界,魔界)"
```

预期输出（示例）：

```text
Starting generation for '<projectID>', 1 chapter(s)...
[BOOTSTRAP] Parsing prompt -> requirements
[BOOTSTRAP] world.json missing -> generating
[BOOTSTRAP] characters.json missing -> generating
[BOOTSTRAP] theme_conflict.json missing -> generating
[BOOTSTRAP] outline.json missing -> generating (num_chapters=1)
[CH001] plan -> write -> audit -> (revise?)-> store
[OK] Generation completed successfully.
```

预期落盘：
- `projects/<projectID>/world.json`
- `projects/<projectID>/characters.json`
- `projects/<projectID>/theme_conflict.json`
- `projects/<projectID>/outline.json`
- `projects/<projectID>/chapters/chapter_001_plan.json`
- `projects/<projectID>/chapters/chapter_001.json`
- `projects/<projectID>/consistency_reports.json`
- `projects/<projectID>/chapter_memory.json`

### 3) 后续运行：默认复用既有背景资产

```bash
python -m app.main -p <projectID> run -c 3
```

预期输出（示例）：

```text
Starting generation for '<projectID>', 3 chapter(s)...
[BOOTSTRAP] world.json exists -> loading
[BOOTSTRAP] characters.json exists -> loading
[BOOTSTRAP] theme_conflict.json exists -> loading
[BOOTSTRAP] outline.json exists -> loading
[CH001] ... store
[CH002] ... store
[CH003] ... store
[OK] Generation completed successfully.
```

### 4) 人工审核分支

当修订轮次耗尽仍无法清零 blocker：

```text
[WARN] Chapter <N> needs human review.
```

并保持与当前 CLI 一致的退出码约定（`2` 表示需要人工审核）。

## 影响范围
- 影响到的 specs：
  - `orchestration`：增加 checkpoint/continue 的执行与恢复契约；补充 `run` 的背景资产 bootstrap 契约
  - `agent-plugins`：明确 `context_pack` 的字段约定与可用性
  - `validation`：增加 context pack/生成输出/背景资产的校验门禁
  - **新增** `retrieval`：上下文检索与 context pack 的能力规格（FTS 基线、无向量库）
- 影响到的代码（计划）：
  - `app/main.py`：实现 `continue`，新增 `ask`（若采纳）
  - `app/graph/*`：新增 `build_context_pack` 节点，接入 checkpointing
  - `app/storage/*`：新增 checkpoint store / retrieval index store
  - `tests/*`：新增断点续跑与 context pack 的集成测试
