## ADDED Requirements

### Requirement: Consistency Detection and Revision Trigger
编排器在章节生成后 MUST 执行一致性检测，并根据检测结果中是否有修复建议（`fix_instructions`）触发修订流程。

#### Scenario: Trigger auto-apply revision based on fix_instructions
- **WHEN** revision_policy == "auto_apply" 且一致性检测报告包含至少一个带有 `fix_instructions` 的问题
- **THEN** 编排器 MUST：
  - 收集所有带有 `fix_instructions` 的 issue（不再检查 `can_auto_fix` 字段）
  - 拼接所有 `fix_instructions` 为 revision_notes
  - 调用修订链进行自动修复
  - 将修订后的章节写回 JSON

#### Scenario: Generate manual-confirm candidate based on fix_instructions
- **WHEN** revision_policy == "manual_confirm" 且一致性检测报告包含至少一个带有 `fix_instructions` 的问题
- **THEN** 编排器 MUST：
  - 收集所有带有 `fix_instructions` 的 issue
  - 调用修订链生成修订候选
  - 保存修订候选到 `chapter_XXX_revision.json`
  - 标记章节状态为 pending

#### Scenario: No revision needed
- **WHEN** 一致性检测报告中所有 issue 的 `fix_instructions` 均为 None 或空字符串
- **THEN** 编排器 MUST：
  - 跳过修订流程
  - 保持原始章节 JSON 不变
  - 继续后续流程
