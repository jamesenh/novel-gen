## Why
当前代码与测试已在 v2.0 分支清理，以解决“工作流与 agent 运用杂糅导致目标混乱”的问题；需要以 **workflow 为主干**、以 **agent 为插件** 的方式重建可运行的生成/审计/修订闭环，并以结构化资产落盘与门禁规则作为硬约束。

## What Changes
- 以工作流节点（workflow nodes）作为主流程：按章生成 → 审计 → 修订循环 → 通过门禁后推进下一章。
- 将审计/影响分析等能力以插件（agent plugins）形式提供：插件只“读 state/产出结构化结果”，不直接 I/O 落盘。
- 建立最小但硬的契约：`blocker == 0` 才能进入下一章；修订导致正文/设定变化时必须同步更新审计报告与记忆资产。
- 版本管理的具体实现细节（如作品级 commit manager / Git 资产仓库）在本阶段明确为 **后置**，但预留 `run_id`/`revision_id` 等可追踪字段以支持未来补齐。

## Impact
- Affected specs (new in v2 baseline):
  - `orchestration`：章节循环、审计循环、门禁与失败策略
  - `persistence`：资产落盘与同步回写一致性（正文/审计/记忆/可选 DB）
  - `agent-plugins`：插件契约与边界
  - `validation`：schema 校验门禁（写盘前）
- Affected code:
  - New v2 workflow runtime package (TBD in tasks)
  - New schema definitions and minimal tests
