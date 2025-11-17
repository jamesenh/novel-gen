# Proposal: add-all-chapter-generation

## Why
当前在大纲阶段已经确定了章节总数和编号，但在后续章节计划（step5）和章节文本生成（step6）阶段：
- 需要手动传入章节编号列表才能批量生成计划；
- `generate_all_chapters()` 只能按大纲生成全部章节文本，无法通过参数只生成部分章节；
- API 在「单章 / 多章 / 全部章节」之间的语义不够统一，调用体验不佳，也不利于后续脚本化和自动化测试。

## What Changes
- 为章节计划阶段增加“生成全部章节”的能力，调用方不需要手动枚举章节编号。
- 为 orchestrator 提供统一的章节范围参数（例如传入列表或 special 值），控制 step5 和 step6 处理哪些章节。
- 更新 chapter-planning 与 orchestration 的 spec 以描述上述行为，并补充对应的实现任务。

## Impact
- Affected specs: chapter-planning, orchestration
- Affected code: novelgen/runtime/orchestrator.py, main.py（示例脚本）

## Goals
- 利用大纲中已有的章节信息，一次性生成全部章节计划。
- 通过参数统一控制「单章 / 多章 / 全部章节」的生成范围。
- 保持与现有 `force` 语义（复用/重算）兼容，避免破坏既有项目。

## Scope & Approach
- 在 chapter-planning spec 中新增一个关于“基于大纲生成全部章节计划”的 ADDED requirement。
- 在 orchestration spec 中新增一个关于“参数化章节范围”的 ADDED requirement，覆盖 step5 和 generate_all_chapters。
- 后续在 orchestrator 中实现：
  - 支持在 step5 中传入“全部章节”模式（例如特殊参数值或缺省值），内部自动读取 outline.chapters。
  - 扩展 generate_all_chapters，支持通过参数只处理部分章节，并与 step5 的行为保持一致。

## Non-Goals
- 不改动大纲生成逻辑（章节数和章节列表仍由 step4 决定）。
- 不新增独立的“章节文本生成” capability spec，仍由 orchestration 协调 scene-text-generation。
- 不引入新的存储结构或缓存机制。

## Validation
- 通过 `openspec validate add-all-chapter-generation --strict`。
- 在 demo 项目中验证：
  - 单章、部分章节、全部章节三种调用方式都能正常工作。
  - 行为与现有 chapter-planning / orchestration spec 保持一致且向后兼容。
