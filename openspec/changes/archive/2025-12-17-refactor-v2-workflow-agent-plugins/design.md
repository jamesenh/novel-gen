## Context
v2.0 分支以“从零重建”为前提：把 workflow 作为唯一主干，agent 以插件形式提供审查等能力，避免节点内隐式 I/O 与逻辑耦合。

## Goals / Non-Goals
- Goals:
  - Workflow-first：节点可组合、可测试、可复现（以落盘产物为准）。
  - Agent-as-plugin：审计/影响分析等能力不侵入主流程 I/O；只产出结构化结果。
  - Contract-first：门禁与同步一致性成为不可破坏的硬约束。
- Non-Goals:
  - 不在本阶段实现完整“作品级版本管理系统”（仅保留追踪字段与扩展点）。
  - 不追求多模型/多后端一键适配（先跑通最小闭环）。

## Decisions
- Decision: 以 `State` 作为 workflow 唯一共享黑板；节点返回增量更新，I/O 由 persistence 层统一处理。
- Decision: 插件接口固定为 `analyze(state, context) -> issues`（结构化），禁止插件直接写文件/DB。
- Decision: “一次修订循环”视为原子写入单元：正文/审计/记忆（及可选 DB）需要一起更新，避免不一致状态。

## Risks / Trade-offs
- 风险：插件输出不稳定导致修订循环震荡 → 通过最大轮次与 `needs_human_review` 失败策略收敛。
- 风险：结构化契约过早冻结影响迭代 → 先做最小 schema，后续通过 OpenSpec 变更演进。

## Migration Plan
- v2 不兼容旧实现；以新 baseline specs 作为真值来源，后续功能增量以 change 驱动。

## Open Questions
- v2 是否需要场景级最小单元（scene assets）作为必选？（当前作为可选，先按章节资产走）
