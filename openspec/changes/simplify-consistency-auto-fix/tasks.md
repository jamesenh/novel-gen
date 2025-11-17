## 1. Implementation
- [x] 1.1 移除 `ConsistencyIssue.can_auto_fix` 字段
  - [x] 1.1.1 在 `novelgen/models.py` 中从 `ConsistencyIssue` 移除 `can_auto_fix` 字段
  - [x] 1.1.2 可选：添加注释说明判断标准为「是否有 fix_instructions」
- [x] 1.2 简化一致性检测链 prompt
  - [x] 1.2.1 在 `novelgen/runtime/consistency.py` 中更新 system prompt
  - [x] 1.2.2 移除对 `can_auto_fix` 的说明，强调「只为可修复问题提供 fix_instructions」
- [x] 1.3 更新 orchestrator 中的判断逻辑
  - [x] 1.3.1 在 `_handle_revision_stage` 方法中，将 `if issue.can_auto_fix and issue.fix_instructions` 改为 `if issue.fix_instructions`
  - [x] 1.3.2 在 `step6_generate_chapter_text` 方法中，更新日志输出逻辑
  - [x] 1.3.3 移除 `sum(1 for issue in report.issues if issue.can_auto_fix)` 的计算，改为 `sum(1 for issue in report.issues if issue.fix_instructions)`

## 2. Documentation & UX
- [x] 2.1 更新日志输出文案
  - [x] 2.1.1 将 "其中X个问题可自动修复" 改为 "其中X个问题包含修复建议"

## 3. Testing & Validation
- [x] 3.1 验证一致性检测输出符合预期
  - [x] 3.1.1 运行一致性检测，确认输出的 JSON 不再包含 `can_auto_fix`
  - [x] 3.1.2 确认有 `fix_instructions` 的问题能触发自动修复
- [x] 3.2 验证 auto_apply 和 manual_confirm 模式正常工作
  - [x] 3.2.1 测试 auto_apply 模式自动修复逻辑
  - [x] 3.2.2 测试 manual_confirm 模式候选生成逻辑
- [x] 3.3 运行 `openspec validate simplify-consistency-auto-fix --strict`
