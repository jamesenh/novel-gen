## ADDED Requirements

### Requirement: Run Chapter Logic Review Gate

编排器在每章正文生成完成后 MUST 执行“章节逻辑审查”，并基于评分与严重问题触发质量闸门（blocking 模式）。

#### Scenario: Review after chapter generation

- **WHEN** `logic_review_policy == "blocking"` 且某章 `chapter_XXX.json` 生成完成
- **THEN** 系统 MUST 调用章节逻辑审查链并生成结构化 `LogicReviewReport`
- **AND** MUST 将报告保存为 `projects/<project>/reviews/chapter_XXX_logic_review.json`

#### Scenario: Block on low score or high severity issues

- **WHEN** 章节逻辑审查报告满足任一条件：
  - `overall_score < logic_review_min_score`
  - 存在至少一个 `severity == "high"` 的 issue
- **THEN** 系统 MUST 进入“阻断状态”，并停止后续章节生成
- **AND** MUST 写入 `projects/<project>/chapters/chapter_XXX_revision.json`（`RevisionStatus.status == "pending"`）
- **AND** MUST 在阻断输出中提供可执行的下一步指引（报告路径、revision 文件路径、建议动作）

#### Scenario: Do not block when policy is off

- **WHEN** `logic_review_policy == "off"`（默认）
- **THEN** 系统 MUST 保持现有行为不变：
  - 不执行逻辑审查
  - 不因逻辑审查阻断章节生成

### Requirement: Enforce Pending Revision Gate Across Generation Entrypoints

系统 MUST 将 `RevisionStatus.status == "pending"` 视为“必须先修复”的闸门信号，并在所有生成入口强制执行阻断（无绕过模式）。

#### Scenario: Block workflow run/resume when pending exists

- **WHEN** 项目存在任意 `chapter_YYY_revision.json` 且其 `status == "pending"`
- **THEN** 系统 MUST 计算 `blocked_chapter = min(pending.chapter_number)`
- **AND** 当用户尝试通过 `run/resume` 继续生成 `blocked_chapter` 之后的内容时，系统 MUST 拒绝执行
- **AND** MUST 返回结构化错误信息，至少包含：
  - `blocked_chapter`
  - `revision_status_file`（对应的 revision 文件路径）
  - `logic_review_report_file`（如有）
  - `next_actions`（例如 review / generate_candidate / apply_revision / regen / rollback）

#### Scenario: Block fine-grained chapter/scene generation when pending exists

- **WHEN** 存在 `blocked_chapter`
- **THEN** 任意针对 `chapter_number > blocked_chapter` 的以下操作 MUST 被拒绝：
  - 章节正文生成（如 `chapter.text.generate`）
  - 场景生成与合并（如 `scene.generate` / `scene.merge_to_chapter`）
- **AND** 错误回显 MUST 指出“必须先处理第 blocked_chapter 章的 pending 修订”

## MODIFIED Requirements

### Requirement: Gate further generation on pending revisions

系统对“待确认修订”的阻断 MUST 适用于所有来源（包括一致性检测触发的修订与逻辑审查触发的修订），并以 `RevisionStatus.status == "pending"` 为唯一闸门信号。

#### Scenario: Treat any pending revision as a hard gate

- **WHEN** 任意章节存在 `RevisionStatus.status == "pending"`
- **THEN** 系统 MUST 阻止对更后章节的生成，直到该 pending 被处理为 accepted/rejected 或被重生成流程清理
