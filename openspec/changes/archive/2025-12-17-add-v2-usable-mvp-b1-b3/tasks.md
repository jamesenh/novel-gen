## 1. 提案验收
- [x] 1.1 审阅范围：实现 B1-B3（不引入向量库）
- [x] 1.2 确认 CLI 形态：`continue` 与（可选）`ask`

## 2. 规格（Specs）
- [x] 2.1 补充 orchestration deltas：checkpointing + continue 契约 + `run` bootstrap 背景资产契约
- [x] 2.2 新增 retrieval spec：FTS5 索引 + context pack 契约（无向量库）
- [x] 2.3 修改 agent-plugins spec：明确插件可获得的 `context_pack` 字段
- [x] 2.4 补充 validation deltas：context pack/生成输出/背景资产写盘前校验（错误可定位）
- [x] 2.5 运行 `openspec validate add-v2-usable-mvp-b1-b3 --strict` 并修复问题

## 3. 实现（Implementation）

### B1. Continue（断点续跑）
- [x] 3.1 实现 checkpoint store，落在 `projects/<project>/workflow_checkpoints.db`
- [x] 3.2 `run` 执行时接入 checkpointer（可恢复的 State）
- [x] 3.3 实现 `novel-gen continue`：恢复最新 checkpoint 并继续执行
- [x] 3.4 定义并实现“resume 幂等写盘”规则（以 `revision_id` 为核心）
- [x] 3.5 集成测试：中断 → continue → 资产正确且无部分写入残留

### B2. 真实生成链路（替换 stub）
- [x] 3.6 在 `run` 中实现 bootstrap：章节循环前执行 `parse_prompt` → `build_or_update_bible` → `build_outline`
  - 验收：首次 `run --prompt "<short>"` 会生成 `world.json/characters.json/theme_conflict.json/outline.json`
  - 验收：后续 `run` 默认只加载既有文件（不静默覆写）
- [x] 3.7 引入 `Planner/Writer/Patcher` 接口，并从 `Config` 注入依赖
- [x] 3.8 为测试实现确定性的 `FakePlanner/FakeWriter/FakePatcher`
- [x] 3.9 落地 `plan_chapter`：至少产出 1 个场景计划；并通过 schema 校验
- [x] 3.10 落地 `write_chapter`：产出非占位内容；计算 `word_count`；并通过 schema 校验
- [x] 3.11 落地 `apply_patch`：基于 `issues[].fix_instructions` 做最小改动；回到审计直至过门禁或人工审核
- [x] 3.12 端到端测试：跑通 1 章“非占位文本”生成，并验证修订循环可在 Fake* 组件下收敛

### B3. 上下文检索与 context pack（无向量库）
- [x] 3.13 定义 `ContextPack` schema 与校验（稳定字段 + 可追溯 sources）
- [x] 3.14 实现语料 loader：项目资产 → 规范化 documents/chunks（稳定 `source_id`）
- [x] 3.15 在 `projects/<project>/data/retrieval.db` 实现 SQLite FTS5 索引（create/update/rebuild）
- [x] 3.16 实现检索函数：query + filters → top_k chunks
- [x] 3.17 增加 `build_context_pack` 节点：必带上下文 + 检索结果；写入 `state["context_pack"]`
- [x] 3.18 将 `context_pack` 注入 `plan_chapter/write_chapter/audit_chapter`（以及插件）使用
- [x] 3.19（可选）新增 `novel-gen ask --question ...`：基于检索结果综合回答并返回引用 sources
- [x] 3.20 测试：context pack schema 稳定 + 检索命中预期来源 + 若涉及 DB 则遵守 `.stale` 行为

## 4. 文档（Documentation）
- [x] 4.1 更新 `docs/CLI.md`：补充 `continue` 行为与 `ask` 用法（若实现）
- [x] 4.2 更新 `docs/MVP_TASKS.md`：完成后勾选 B1-B3 并写明验收点
