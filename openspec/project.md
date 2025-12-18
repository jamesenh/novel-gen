# Novel-Gen OpenSpec 项目约定

本仓库是「长篇小说生成/迭代工作流」的项目资产与规范仓库。`openspec/` 用于管理“系统/流程/数据契约”的规格与变更提案；小说内容资产主要落在 `projects/`。

## 仓库结构（约定）

- `docs/开发文档.md`：开发宗旨、流程、数据契约的说明（规范来源）。
- `projects/<project_name>/`：每个小说项目的结构化资产与正文（权威产物）。
- `openspec/`：规格（`specs/`）与变更提案（`changes/`）。

## 关键原则（影响 spec 与变更评审）

- **结构化优先**：设定/计划/审计尽量使用 JSON（或强结构化表述）。
- **一致性优先**：跨章节保持世界观、人物动机、时间线、知情链、伏笔线程稳定。
- **最小改动修订**：修订优先补过渡/补证据/改台词与动机，避免整章推倒重写。
- **回归门禁**：章节推进的门禁默认是 `blocker == 0`；当达到最大修订轮次仍存在 blocker，应标记 `needs_human_review` 并停止自动推进。
- **编码正确**：所有文本与 JSON 默认 UTF-8，避免双重编码导致的乱码。

## 数据契约与兼容性

对“会落盘到 `projects/` 的结构化输出”进行变更时（新增字段、改名、枚举变动、语义变化）：

- 关键 JSON 建议包含 `schema_version`、`generated_at`、`generator`。
- 写入 `projects/` 前必须通过 schema 校验，避免资产污染。
- 兼容策略：优先新增字段；字段改名需保留旧字段一段时间并双写；`schema_version` 升级必须提供迁移脚本或兼容读取逻辑。

## 记忆回写一致性（强约束）

若正文/设定发生变更，必须避免“正文变了但记忆没变”：

- 同步更新 `projects/<project>/chapter_memory.json` 与 `projects/<project>/consistency_reports.json`。
- 若存在 `projects/<project>/data/novel.db`，同步更新对应 `memory_chunks` / `entity_snapshots`。

## 变更提案的附加要求（本项目特化）

当 change 影响到工作流门禁、审计输出字段、或资产数据模型时，提案中至少写清：

- 影响范围：哪些资产文件/表会变、哪些章节需要回归。
- 回归范围规则：若影响 bible 关键字段（人物动机/世界规则/关键事件），至少回归受影响章节区间及后续 1–2 章；仅表达润色可只做风格校验。
- 测试要求：审计输出字段变更需补充契约测试；结构化输出变更需更新/新增 schema 校验测试（如 `tests/test_schemas.py`、`tests/test_routing.py`，若仓库实际存在）。

## 安全与仓库卫生

- 不提交真实密钥：`.env` 仅本地使用；如需共享配置用示例文件并忽略真实文件。
- 注意大文件：`projects/*/data/`（向量库/DB/graph）可能很大；新增或搬运前先确认策略。
