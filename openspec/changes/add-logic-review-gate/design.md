## 设计概览

### 1) 关键定义

- **Logic Review（逻辑审查）**：对章节/场景的因果链、动机合理性、衔接自然度、世界规则遵循等进行审查，输出结构化报告与评分。
- **Quality Gate（质量闸门）**：当存在“必须先修复的问题”时，阻断任何后续章节/场景生成入口，直到用户完成修复闭环。
- **blocked_chapter**：所有 `RevisionStatus.status == "pending"` 中 `chapter_number` 的最小值。

### 2) 数据与真源

- 正文真源：`projects/<id>/chapters/chapter_XXX.json`
- 闸门信号：`projects/<id>/chapters/chapter_XXX_revision.json`（`status=pending` 表示必须先修复）
- 报告视图：`projects/<id>/reviews/chapter_XXX_logic_review.json`（只读，不作为真源）

### 3) 触发与阻断规则

- 触发阻断条件：
  - `overall_score < logic_review_min_score` **OR**
  - 存在 `severity == "high"` 的 issue
- 阻断规则：只要存在 `blocked_chapter`，任何目标章节号大于 `blocked_chapter` 的生成请求 MUST 被拒绝（无绕过模式）。

### 4) 工作流接入点（章节级为主）

```
chapter_generation
  -> chapter_logic_review (new)
  -> consistency_check (existing)
  -> chapter_revision (existing)
  -> next_chapter
```

- 若 `chapter_logic_review` 触发阻断：写报告与 pending revision，然后正常结束工作流（确保 checkpoint 落盘）。

### 5) 错误契约（给 CLI/Agent/Tools 统一处理）

当命中闸门，返回结构化错误信息（ToolResult.data 或异常字段），至少包含：
- `blocked_chapter`
- `observed_score`、`min_score`、`high_issues_count`
- `logic_review_report_file`
- `revision_status_file`
- `next_actions`: `["review", "generate_candidate", "apply_revision", "regen", "rollback"]`

### 6) Agent 交互策略

- `/run`/`/resume` 或生成范围请求命中闸门时：
  - 回显阻断原因与文件路径
  - 提供明确下一步：先 `/review <ch>`，再确认 `/fix <ch>` 生成候选，再确认 `/accept <ch>` 应用
- 不提供绕过继续生成后续章节的路径。

