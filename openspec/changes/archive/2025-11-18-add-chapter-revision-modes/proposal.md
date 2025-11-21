## Why
当前章节一致性检测（consistency check）在发现可自动修复问题后，只会生成 `chapter_XXX_revised.txt` 文本文件，并不会回写到章节 JSON 真源，也不会影响后续章节记忆、上下文构建和整书导出流程。

这导致：
- 用户如果不手工对照、复制修订结果，后续步骤仍然基于未修订文本；
- 导出的整书 txt 默认读取 `chapter_XXX.json`，不会包含修订内容；
- 无法在流程层面明确区分「完全自动应用修订」和「需要人工确认后才能继续」两种模式。

本变更希望通过在 orchestrator 中引入章节修订模式（`revision_policy`），定义 `auto_apply` 与 `manual_confirm` 两种行为，使修订成为 6 步生成管道中的一等公民，而不是旁路副产物。

## What Changes
- 在编排能力（orchestration）中新增对「章节一致性检测 + 修订阶段」的规范：
  - 定义章节 JSON 为唯一正文真源；
  - 定义一致性检测产生的自动修订候选如何接入 pipeline。
- 定义 `revision_policy` 策略枚举（`none | auto_apply | manual_confirm`）及其在 orchestrator 中的语义：
  - `none`：保持当前行为，仅记录一致性报告，不做任何修订；
  - `auto_apply`：自动应用可修复问题，直接更新章节 JSON；
  - `manual_confirm`：生成修订候选并挂起流程，要求人工确认后方可使修订生效并继续后续步骤。
- 约束 `generate_all_chapters()` 在存在待确认修订时的行为，使其在默认情况下不会在「未确认文本」之上继续推进剧情。
- 为后续实现留出接口形态：支持显式的「应用修订」操作（例如 CLI 命令或 runtime 函数），将人工确认与自动编排解耦。

## Impact
- **Affected specs**：
  - `specs/orchestration/spec.md`：新增关于章节修订模式的 Requirements 与 Scenarios。
- **Affected code**：
  - `novelgen/runtime/orchestrator.py`
  - `novelgen/runtime/revision.py`
  - `novelgen/runtime/exporter.py`（可选，确保导出行为与章节 JSON 真源一致）
  - `novelgen/config.py`（在 `ProjectConfig` 中暴露 `revision_policy` 配置）

## BREAKING?
- 对现有 CLI/调用方式属于向后兼容增强：
  - 默认策略可以保持当前行为（不自动应用修订），避免破坏已有项目；
  - 新增模式通过配置或构造参数显式开启。
- 但从行为上改变了「一致性检测之后，章节 JSON 是否会被自动更新」这一点，因此需要通过 spec 明确约束，并在实现时谨慎处理默认值与迁移路径。
