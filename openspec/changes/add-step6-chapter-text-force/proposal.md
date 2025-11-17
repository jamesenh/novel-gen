# Proposal: add-step6-chapter-text-force

## Why
当前 orchestrator 的 `step6_generate_chapter_text` 每次调用都会重新生成章节文本，即使该章节的 JSON 文件已经存在且可解析。这导致：
- 不能像 step1~5 那样通过 `force` 参数控制复用已有结果
- 批量执行 `generate_all_chapters()` 时，无法跳过已生成章节，浪费 token 和时间
- 行为与 orchestration spec 中“Reuse existing results / Force regeneration” 的通用要求不完全一致，需要显式覆盖到章节文本生成步骤

## What Changes
- 为 `step6_generate_chapter_text` 增加 `force: bool = False` 参数
- 在生成前检测 `chapter_{chapter_number:03d}.json` 是否存在且可解析，`force=False` 时直接复用
- 在控制台输出清晰的“跳过/强制重算”日志提示
- 更新 `generate_all_chapters()` 使其调用 step6 时遵守相同的 force 语义

## Impact
- Affected specs: orchestration
- Affected code: novelgen/runtime/orchestrator.py

## Goals
1. 让章节文本生成具备与前面步骤一致的“可复用/可强制重算”行为。
2. 在不破坏现有项目结构的前提下，减少重复 LLM 调用和生成时间。
3. 保持 `generate_all_chapters()` 与单章生成在行为上的一致性。

## Scope & Approach
- 在 orchestrator 中复用现有 `_maybe_use_existing` 工具方法，对 `chapter_XXX.json` 做存在性和解析检查。
- 为 step6 和 generate_all_chapters 增加 `force` 参数，并在日志中区分复用 vs 重算。
- 通过 OpenSpec delta 在 orchestration 能力下新增关于“章节文本级 force 控制”的要求。

## Non-Goals
- 不改动章节 plan 生成的行为（已支持 force）。
- 不引入新的缓存层或存储形态。
- 不改变一致性检查、章节记忆生成等后处理逻辑。

## Risks
- 调整默认行为时需确认不会影响现有 demo 项目预期（例如依赖重新生成的调试流程）。

## Validation
- 针对已存在章节 JSON 时调用 step6，验证 `force=False` 复用结果、`force=True` 重新生成。
- 对 generate_all_chapters() 进行回归验证，确保在混合“已生成+未生成”章节场景下行为正确。
- 通过 `openspec validate add-step6-chapter-text-force --strict`。
