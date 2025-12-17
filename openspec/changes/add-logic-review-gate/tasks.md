## 1. Proposal Checklist

- [x] 1.1 明确阻断策略：`overall_score < min_score` 或 `high` issue → 阻断
- [x] 1.2 明确"下一步"闭环：报告 → 用户确认生成候选 → 用户确认应用 → 复审通过后继续
- [x] 1.3 明确无绕过模式：任何后续生成入口必须检测 `pending` 并拒绝
- [x] 1.4 对齐落盘约定：`reviews/` 报告视图 + `chapter_XXX_revision.json` 作为闸门信号

## 2. Implementation

- [x] 2.1 新增 `LogicReviewReport`/`LogicReviewIssue` 等 Pydantic 模型
- [x] 2.2 新增章节逻辑审查链（structured_output + fallback）
- [x] 2.3 在 LangGraph 主流程中接入 `chapter_logic_review_node`
- [x] 2.4 触发阻断时写入：
  - [x] 2.4.1 `reviews/chapter_XXX_logic_review.json`
  - [x] 2.4.2 `chapters/chapter_XXX_revision.json`（`status=pending`）
- [x] 2.5 全入口闸门：
  - [x] 2.5.1 `workflow.run` / `workflow.resume` 先检查 pending 并拒绝后续章节
  - [x] 2.5.2 `chapter.text.generate` / `scene.generate` / `scene.merge_to_chapter` 同样检查并拒绝
- [x] 2.6 Agent 交互与工具：
  - [x] 2.6.1 增加"查看逻辑审查报告"工具/命令（无需确认）
  - [x] 2.6.2 增加"生成候选修订稿"工具/命令（普通确认）
  - [x] 2.6.3 复用/扩展"应用修订"操作（破坏性确认）
- [x] 2.7 配置接入：
  - [x] 2.7.1 `logic_review_policy` 默认 off（兼容旧项目）
  - [x] 2.7.2 `logic_review_min_score` 默认值与覆盖策略（settings/env）
- [x] 2.8 文档更新：在流程文档与 chat 指南中补充"阻断 → 修复 → 继续"的操作指引

## 3. Validation

- [x] 3.1 运行 `openspec validate add-logic-review-gate --strict`
- [x] 3.2 最小回归验证：
  - [x] 3.2.1 触发阻断时，后续章节/场景生成入口都会返回一致的阻断错误
  - [x] 3.2.2 应用修订后阻断解除，可继续 `/resume`

## Implementation Summary

### 新增/修改的文件

**模型层 (models.py)**
- `LogicReviewIssue`: 逻辑审查问题模型
- `LogicReviewReport`: 逻辑审查报告模型（含 `should_block()` 方法）
- `RevisionStatus`: 新增 `triggered_by` 字段区分触发来源

**配置层 (config.py)**
- `ProjectConfig`: 新增 `logic_review_policy` 和 `logic_review_min_score` 字段
- 支持环境变量覆盖：`NOVELGEN_LOGIC_REVIEW_POLICY`、`NOVELGEN_LOGIC_REVIEW_MIN_SCORE`

**链 (chains/)**
- `logic_review_chain.py`: 逻辑审查链，使用 structured_output + fallback
- `chapter_revision_chain.py`: 章节修订链，支持基于报告和基于说明两种模式

**运行时 (runtime/)**
- `nodes.py`: 新增 `chapter_logic_review_node` 节点
- `workflow.py`: 在 `chapter_generation` 后插入 `chapter_logic_review`，添加条件边
- `gate.py`: 质量闸门检查模块，提供 `check_pending_revision_gate` 等函数
- `orchestrator.py`: `run_workflow`/`resume_workflow` 入口检查闸门

**工具 (tools/)**
- `revision_tools.py`: 新增审查工具集
  - `review.report` (无需确认)
  - `review.list` (无需确认)
  - `review.status` (无需确认)
  - `review.generate_fix` (普通确认)
  - `review.apply` (破坏性确认)
  - `review.reject` (普通确认)
- `chapter_tools.py`: 添加闸门检查
- `scene_tools.py`: 添加闸门检查

**Agent (agent/chat.py)**
- 注册 revision_tools
- 更新帮助信息
- 更新参数解析

**文档**
- `docs/对话式Agent使用指南.md`: 添加逻辑审查质量闸门章节
- `docs/ENV_SETUP.md`: 添加环境变量配置说明

**测试**
- `tests/test_logic_review_gate.py`: 闸门功能回归测试（13 个测试用例）
