<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.
<!-- OPENSPEC:END -->

# Novel-Gen 仓库工作约定（面向 AI 助手）

本仓库是「长篇小说生成/迭代工作流」的项目资产与规范仓库；核心产物是可落盘、可检索、可回滚的结构化资产（world/characters/outline/chapters/audit/memory）。

## 核心原则（默认遵守）

- **结构化优先**：设定/计划/审计尽量用 JSON（或强结构化表述），减少自然语言漂移。
- **契约化输出**：关键 JSON 建议带 `schema_version`、`generated_at`、`generator`，并在写入项目前通过 schema 校验。
- **最小改动**：修订优先“补过渡/补证据/改台词与动机”，避免整章推倒重写。
- **回归门禁**：章节“进入下一章”的唯一条件是 `blocker == 0`（一致性审计通过）。
- **编码正确**：文本与 JSON 一律 UTF-8，避免双重编码导致的乱码。

## 资产目录（以 `projects/` 为主）

- 项目资产根目录：`projects/<project_name>/`
- 常见文件：
  - `settings.json`（项目元信息）
  - `world.json` / `characters.json` / `theme_conflict.json` / `outline.json`
  - `chapters/`（`chapter_XXX_plan.json`、`chapter_XXX.json`、可选 `chapter_XXX_revised.txt`）
  - `consistency_reports.json`（一致性审计问题与建议修复）
  - `chapter_memory.json`、`data/novel.db`（记忆片段与实体快照；可选）
  - `workflow_checkpoints.db`（断点续跑；可选）

## 修改资产时的同步要求（避免“正文变了但记忆没变”）

- 若修改章节正文/设定（world/characters/timeline/threads），同步更新：
  - `projects/<project>/chapter_memory.json`
  - `projects/<project>/consistency_reports.json`
  - （如存在）`projects/<project>/data/novel.db` 中对应 `memory_chunks` / `entity_snapshots`

## 变更与协作

- “系统怎么改 / 流程怎么变 / schema 变化”统一走 `openspec/`；必要时先写变更提案再实现。
- 新增/修改结构化输出字段时，优先补充/更新 schema 与相关测试（如 `tests/test_schemas.py`、`tests/test_routing.py`）。

## 安全与仓库卫生

- 不提交真实密钥：`.env` 仅本地使用，仓库中应使用示例文件（如 `.env.example`）。
- 注意大文件：`projects/*/data/`（向量库/DB/graph）可能很大，新增或搬运前先确认策略。

## 编码规范

- `docs/*.md`、用户可见说明：默认使用**中文**（术语可保留英文原名）。
- Python 代码：标识符/变量/函数名用**英文**；不要用拼音命名。
- Docstring：**必须**给公开模块/类/函数写 docstring；默认用**中文**。
- 注释说明: 使用**中文**
- 不新增花哨输出：CLI/日志避免新增 emoji 与装饰字符（保持可 grep/可解析）。
- openspec中的change的内容描述文字使用**中文**