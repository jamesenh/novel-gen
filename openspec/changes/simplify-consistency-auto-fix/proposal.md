# Simplify Consistency Auto-Fix Logic

## Why
当前一致性检测链要求模型同时返回 `can_auto_fix` 和 `fix_instructions` 两个字段，增加了模型负担和判断复杂度。实际上，如果模型能给出 `fix_instructions`，就说明问题可以自动修复。让模型做两次判断（是否可修复 + 如何修复）是冗余的。

简化逻辑：**只要一致性检测报告中包含 `fix_instructions`，就认为该问题可以自动修复。**

## What Changes
- **移除** `ConsistencyIssue.can_auto_fix` 字段（或标记为 deprecated）
- **简化** 一致性检测链的 prompt，不再要求模型判断 `can_auto_fix`
- **修改** orchestrator 中的判断逻辑：从 `if issue.can_auto_fix and issue.fix_instructions` 改为 `if issue.fix_instructions`
- **更新** 相关日志输出，移除对 `can_auto_fix` 的提及

## Impact
- **Affected specs**: orchestration（章节生成和修订流程）
- **Affected code**: 
  - `novelgen/models.py` - ConsistencyIssue 模型
  - `novelgen/runtime/consistency.py` - 一致性检测链 prompt
  - `novelgen/runtime/orchestrator.py` - 修订判断逻辑和日志
- **Breaking change**: ❌ 非破坏性（保留字段为 deprecated，或直接移除因为是内部模型）
- **Migration**: 已有的 `consistency_reports.json` 文件可能包含 `can_auto_fix` 字段，但不影响读取（Pydantic 会忽略额外字段）
