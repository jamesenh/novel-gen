## ADDED Requirements

### Requirement: Context Pack 写入/调用前校验
系统 SHALL 在将 `context_pack` 传递给插件或生成器之前，对其进行 schema 校验。

#### Scenario: 无效 context pack 会被拒绝
- **WHEN** 系统构建了一个无效的 `context_pack`（schema 不匹配）
- **THEN** 系统以可定位的错误失败（包含字段路径与原因）
- **AND THEN** 系统不会携带该无效 context pack 去调用插件

### Requirement: 生成链路输出写盘前校验
系统 SHALL 在将 planner/writer/patcher 的输出落盘到 `projects/<project>/` 之前，对其进行 schema 校验。

#### Scenario: writer 输出无效则不写盘
- **WHEN** writer 产出无效的 `chapter_draft`
- **THEN** 系统失败该步骤，且不会写入无效的章节资产

### Requirement: 背景资产写盘前校验
系统 SHALL 在将生成的背景资产（`world.json`、`characters.json`、`theme_conflict.json`）以及 `outline.json` 落盘到 `projects/<project>/` 之前，对其进行 schema 校验。

#### Scenario: 无效的 world.json 不会被写盘
- **WHEN** 系统生成了无效的 `world.json`（schema 不匹配）
- **THEN** 系统以可定位的错误失败（包含字段路径与原因）
- **AND THEN** 系统不会将该无效背景资产写入磁盘
