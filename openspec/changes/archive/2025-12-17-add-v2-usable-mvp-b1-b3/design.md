# 设计说明：B1-B3 “可用级 MVP”

本设计文档用于约束实现方案，以保证可复现、可测试、可扩展，并满足“不引入向量库”的阶段目标。

## 1. 断点续跑与 Continue（B1）

### 1.1 Checkpoint 存储
- 使用 `projects/<project>/workflow_checkpoints.db` 作为运行级 checkpoint 存储。
- 采用 LangGraph 的 checkpointer（SQLite）或等价机制，确保：
  - 每个 run 具有唯一 `run_id`
  - 每次节点执行的状态可恢复

### 1.2 `continue` 行为（恢复并继续）
- `novel-gen -p <project> continue`：
  - 读取 `workflow_checkpoints.db` 的最新 checkpoint
  - 恢复 `State` 并从中断处继续执行至 END（或再次中断）

### 1.3 幂等写盘策略
为避免 “continue 重放 store 节点” 导致重复写盘引入漂移（如时间戳变更）：
- 对同一 `revision_id` 的持久化写入应是幂等的：
  - 若目标文件已存在且 `revision_id` 相同，则不重写（或重写但不改变语义字段；更新时间字段需明确策略）
- 集成测试需覆盖：中断 → continue → 最终资产一致、无部分写入残留。

## 2. 真实生成链路（B2）

### 2.0 Bootstrap：背景资产在 `run` 内自动生成
为满足“用户提供简短提示词即可开跑”的 UX，本阶段将背景资产生成补充到 `run` 执行路径中：
- 若 `world.json/characters.json/theme_conflict.json/outline.json` 缺失，则 `run --prompt "<short>"` 触发扩写与生成，并落盘这些资产
- 若已存在，则默认只加载复用（避免隐式覆写）；需要重建时应通过显式参数开关（后续可扩展）

最小节点序列（在章节循环之前）：
1. `parse_prompt`：将用户简短提示词扩写为结构化 `requirements`
2. `build_or_update_bible`：生成/加载 `world/characters/theme_conflict`
3. `build_outline`：生成/加载 `outline`

建议日志输出（示例，非强制）：
```text
[BOOTSTRAP] Parsing prompt -> requirements
[BOOTSTRAP] world.json missing -> generating
...
```

### 2.1 Provider 抽象（便于测试与真实运行解耦）
为了在不依赖外部网络/LLM 的情况下做单测与集成测试：
- 提供 `Planner` / `Writer` / `Patcher` 接口
- 提供 `Fake*` 实现用于测试（确定性输出）
- 提供 `OpenAI*`（或其它）实现用于真实运行（仅在配置存在时启用）

### 2.2 最小可用输出约束
- `chapter_plan`：至少包含 1 个场景计划，包含 `location/characters/purpose/key_actions` 等最小字段集
- `chapter_draft`：至少包含 1 个场景，`content` 不是占位符，`word_count` 可计算
- `apply_patch`：优先处理 `severity=blocker` 的问题，基于 `fix_instructions` 实施最小改动并递增 `revision_round/revision_id`

## 3. 上下文检索 + Context Pack（B3，无向量库）

### 3.1 可检索语料来源
以项目资产为权威来源：
- bible：`world.json` / `characters.json` / `theme_conflict.json`
- outline：`outline.json`
- chapters：`chapters/chapter_XXX_plan.json` / `chapters/chapter_XXX.json`
- memory/reports：`chapter_memory.json` / `consistency_reports.json`

### 3.2 索引与检索（FTS5）
- 优先使用 SQLite FTS5 建立全文索引（建议位置：`projects/<project>/data/retrieval.db`）
- 当 FTS5 不可用或 index 不存在时，回退到无索引的简易检索（小规模项目可用）

### 3.3 Context Pack 组装
Context pack 由两部分组成：
- **必带上下文（deterministic）**：当前章 outline 片段、bible 摘要、最近 N 章 memory、未闭环 blocker issues（如有）
- **检索结果（retrieved）**：按 query/top_k 返回的片段（带 `source_path/source_id/score`）

### 3.4 “综合回答”入口
在同一套 retrieval/context pack 基础上提供 `ask`：
- 输入：自然语言 question + 可选 filters（chapter range, doc types）
- 输出：`answer` + `sources[]`（引用 context pack 的条目，确保可追溯）

## 4. 用户流程（流程图）

```mermaid
flowchart TD
  A[CLI: init] -->|create dirs| A1[settings.json + chapters/ + data/]

  B[CLI: run --prompt short] --> P[parse_prompt\n短提示词 -> requirements]
  P --> W[build_or_update_bible\n生成/加载 world/characters/theme_conflict]
  W --> O[build_outline\n生成/加载 outline.json]
  O --> L[chapter loop: for ch=1..N]
  L --> C1[plan_chapter]
  C1 --> C2[write_chapter]
  C2 --> C3[audit_chapter (plugins)\nuses optional context_pack later]
  C3 -->|blocker>0 & rounds left| C4[apply_patch]
  C4 --> C3
  C3 -->|gate pass| S[store_artifacts\natomic bundle write]
  S -->|next chapter| L
  S -->|complete| E[END]
  C3 -->|rounds exhausted| H[needs_human_review -> END]
```
