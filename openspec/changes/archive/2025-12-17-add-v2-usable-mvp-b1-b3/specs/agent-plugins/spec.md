## MODIFIED Requirements

### Requirement: Plugin Input Contract
系统 SHALL 向插件提供稳定的输入契约，包含当前 `State` 与 `context_pack`（必带上下文 + 可选检索结果），以便插件能产出可追溯的 evidence。

#### Scenario: 插件收到章节的 context pack
- **WHEN** 工作流进入 `chapter_id = N` 的审计步骤
- **THEN** 插件获得当前章节草稿与相关的 bible/outline 上下文
- **AND THEN** 插件获得包含可追溯来源的 `context_pack.retrieved[]`（至少含 `source_path` 与 `source_id`），以便 evidence 可引用来源

## ADDED Requirements

### Requirement: Context Pack 字段稳定且可追溯
系统 SHALL 向插件与生成节点提供 schema 稳定的 `context_pack`；其中 `retrieved[]` 条目至少包含 `source_path` 与 `source_id`，且可追溯到具体项目资产。

#### Scenario: context pack 条目字段稳定
- **WHEN** 系统从任意项目资产构建一个 context pack 条目
- **THEN** 该条目包含 `source_path` 与 `source_id`
- **AND THEN** 系统能够将该条目追溯回具体的项目文件与定位信息
