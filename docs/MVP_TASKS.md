# Novel-Gen v2 MVP 任务清单（全局）

本清单用于在 `docs/` 层面给出“总体 MVP”的单一入口，便于按可验证的验收点推进。

**MVP 基线规格（权威来源）**
- `openspec/specs/orchestration/spec.md`
- `openspec/specs/persistence/spec.md`
- `openspec/specs/agent-plugins/spec.md`
- `openspec/specs/validation/spec.md`

**已完成的 MVP Slice（对应提案）**
- 见 `openspec/changes/refactor-v2-workflow-agent-plugins/tasks.md`

---

## A. v2 MVP Baseline（已完成）

### A1. CLI 与项目初始化
- [x] `init/run/continue(占位)` 命令可用（`novel-gen` 与 `python -m app.main`）
  - 验收：`docs/CLI.md` 示例可运行；`app/main.py` 存在对应 subcommands

### A2. Orchestration（章节循环 + 门禁）
- [x] 章节循环：`chapter_id=1..num_chapters`
- [x] 门禁：`blocker_count <= QA_BLOCKER_MAX` 才能推进
- [x] 修订上限：达到 `MAX_REVISION_ROUNDS` 仍有 blocker → `needs_human_review`
  - 验收：`tests/test_routing.py`、`tests/test_integration.py`

### A3. Agent Plugins（只读边界 + I/O 契约）
- [x] 插件注册表 + 默认插件（noop/continuity）
- [x] 插件只读边界（不允许直接写盘/DB）
- [x] 插件输出 issues 结构化字段可过滤（severity/category/summary 等）
  - 验收：`tests/test_plugins.py`、`tests/test_audit_chapter.py`

### A4. Validation（写盘前 schema 门禁）
- [x] 章节 plan/content 写盘前校验
- [x] 插件 issues 写盘前校验（无效直接拒绝，错误包含路径）
- [x] `consistency_reports.json`、`chapter_memory.json` 写盘前校验
  - 验收：`tests/test_schemas.py`、`tests/test_artifact_store.py`

### A5. Persistence（标准路径 + 同步 + 原子写）
- [x] 标准落盘路径：`projects/<project>/...`
- [x] 同步更新：章节正文变更时同时更新 `consistency_reports.json` 与 `chapter_memory.json`
- [x] 原子捆绑写：plan/content/reports/memory 作为一组写入（失败回滚）
- [x] 可选 DB：若存在 `data/novel.db`，以 `novel.db.stale` 标记陈旧
  - 验收：`tests/test_artifact_store.py`、`tests/test_integration.py`

---

## B. “可用级” MVP（下一阶段建议任务）

> 这些任务不属于当前 baseline 提案的硬性完成条件，但通常是把 v2 从“可跑通”推进到“可日用”的最小集合。

### B1. Continue（断点续跑）
- [x] 实现 `continue`：从 `workflow_checkpoints.db` 恢复并继续执行
  - 验收：提供集成测试，覆盖中断后继续与幂等写盘

### B2. 真实生成链路（替换 stub）
- [x] `plan_chapter` 生成真实计划（基于 outline/上下文）
- [x] `write_chapter` 生成真实正文（基于 plan/上下文）
- [x] `apply_patch` 实施最小改动修订（基于 issues.fix_instructions）
  - 验收：最小端到端跑通 1 章（非占位文本），并能触发“修订循环收敛”

### B3. 上下文检索与 context pack
- [x] 增加检索节点（从 `chapter_memory.json` / 可选 DB / outline/bible 提取 context pack）
  - 验收：插件可获得稳定的 context pack（有 schema 或明确字段约定）

### B4. 可选 DB 真同步
- [ ] 若存在 `data/novel.db`，对 `memory_chunks/entity_snapshots` 做同步写回或提供可重复执行的 backfill
  - 验收：去掉 `.stale` 的条件明确且可测试

### B5. 错误与可恢复性
- [ ] 统一结构化错误输出（包含 failing path + reason + chapter/revision 标识）
- [ ] 提供“失败后恢复”策略说明与最小工具脚本

---

## C. 工程化与发布（建议）

### C1. CI/质量门禁
- [ ] 添加 CI：运行 `.venv` 或 `uv` 环境下的 `pytest`
- [ ] `ruff`/格式化在 CI 运行（若仓库约定需要）

### C2. 安装与运行一致性
- [ ] 明确“推荐运行方式”：`uv run ...` 或 `.venv/bin/python ...`（二选一）
- [ ] 在 docs 中给出一套不会触发平台限制的命令（尤其是 macOS/沙箱环境）
