## ADDED Requirements

### Requirement: 工作流检查点落盘
系统 SHALL 将工作流执行检查点持久化到 `projects/<project>/workflow_checkpoints.db`，以便运行被中断后可以恢复继续。

#### Scenario: run 写入检查点
- **WHEN** 用户对 `project = P` 执行 `run`
- **THEN** 系统在 `projects/P/workflow_checkpoints.db` 写入检查点
- **AND THEN** 检查点数据足以恢复执行且不丢失当前 `chapter_id` 与 `revision_id`

### Requirement: 从最新检查点 continue
系统 SHALL 提供 `continue` 命令，从该项目的最新检查点恢复并继续执行。

#### Scenario: 中断后继续
- **GIVEN** 上一次运行在章节中途被中断
- **WHEN** 用户对同一项目执行 `continue`
- **THEN** 系统恢复最新检查点中的 `State`
- **AND THEN** 系统继续执行直至到达 END 或再次被中断

### Requirement: 恢复执行时的幂等持久化
系统 SHALL 在从检查点恢复时保证持久化写盘的幂等性，避免同一 `revision_id` 出现部分写入或重复写入导致资产漂移。

#### Scenario: 恢复不会重复写入
- **GIVEN** `chapter_id = N` 且 `revision_id = R` 的章节捆绑资产已经成功落盘
- **WHEN** 工作流恢复后回放到同一 `revision_id` 的持久化步骤
- **THEN** 最终落盘资产保持一致且不存在部分写入残留

### Requirement: run 中的背景资产 bootstrap
系统 SHALL 在章节循环开始之前，于 `run` 过程中生成或加载项目背景资产（`world.json`、`characters.json`、`theme_conflict.json`）以及 `outline.json`。

#### Scenario: 首次 run 基于提示词生成缺失的背景资产
- **GIVEN** `projects/<project>/` 已存在但背景资产缺失
- **WHEN** 用户执行 `run --prompt "<short prompt>"`
- **THEN** 系统将简短提示词扩写为结构化 `requirements`
- **AND THEN** 系统生成并落盘 `world.json`、`characters.json`、`theme_conflict.json`、`outline.json`
- **AND THEN** 系统使用这些资产进入章节循环

#### Scenario: 后续 run 默认复用既有背景资产
- **GIVEN** `world.json`、`characters.json`、`theme_conflict.json`、`outline.json` 已存在
- **WHEN** 用户在未提供显式重建开关的情况下执行 `run`
- **THEN** 系统加载并复用这些资产，且不会静默覆写
