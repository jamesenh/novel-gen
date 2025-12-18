# retrieval Specification

## Purpose
TBD - created by archiving change add-v2-usable-mvp-b1-b3. Update Purpose after archive.
## Requirements
### Requirement: 检索语料来源于项目资产
系统 SHALL 从 `projects/<project>/` 下的项目资产构建检索语料，包括 bible、outline、chapters、chapter memory 与 consistency reports。

#### Scenario: 语料覆盖关键项目文档
- **WHEN** 系统为某项目构建或刷新检索语料
- **THEN** 语料包含来自 `world.json`、`characters.json`、`outline.json` 的内容
- **AND THEN** 若存在，则语料包含来自 `chapters/`、`chapter_memory.json`、`consistency_reports.json` 的内容

### Requirement: 不依赖向量库的关键词检索
系统 SHALL 在不要求向量数据库的情况下支持关键词检索，并在可用时使用 SQLite FTS5。

#### Scenario: 检索返回 top-k 匹配
- **WHEN** 用户或工作流以 `top_k = K` 查询 `"X"`
- **THEN** 系统返回最多 K 条按关键词相关度排序的片段（chunks）
- **AND THEN** 每条结果包含 `source_path` 与稳定的 `source_id`

### Requirement: 组装 Context Pack
系统 SHALL 组装一个 `context_pack`，将“必带上下文（deterministic）”与“检索结果（retrieved）”组合在一起。

#### Scenario: context pack 同时包含必带与检索条目
- **WHEN** 工作流准备对 `chapter_id = N` 执行 plan/write/audit
- **THEN** context pack 包含与第 N 章相关的 bible/outline/memory 必带摘录
- **AND THEN** context pack 包含基于当前 query/task 的检索片段

### Requirement: 检索索引的存放位置
系统 SHALL 将关键词检索索引存放在 `projects/<project>/data/` 下（例如 `projects/<project>/data/retrieval.db`），以便与项目资产同目录管理。

#### Scenario: 索引与项目数据同目录
- **WHEN** 系统创建检索索引
- **THEN** 索引文件存放在 `projects/<project>/data/` 下

