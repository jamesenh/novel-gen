# logic-review Specification

## Purpose

逻辑审查模块负责对已生成的章节/场景内容进行“合理性与逻辑连贯性”审查，并输出结构化审查报告（含评分、问题列表与修复指引）。该模块用于在内容生成流程中提供可配置的质量门控，防止错误叠加到后续章节。

**技术实现（实现阶段）**：
- 使用 LangChain `with_structured_output()` 优先输出结构化 `LogicReviewReport`
- 提供 `PydanticOutputParser + LLMJsonRepairOutputParser` 作为 fallback
- 审查输入以 JSON 真源（`chapter_XXX.json`、`chapter_XXX_plan.json`）为准

## ADDED Requirements

### Requirement: Produce Structured Logic Review Report

系统 MUST 为章节逻辑审查输出结构化报告，包含评分与可定位的问题描述。

#### Scenario: Return a chapter logic review report

- **WHEN** 输入为某章的 `ChapterPlan` 与 `GeneratedChapter`（以及必要的 chapter_context）
- **THEN** 系统 MUST 输出 `LogicReviewReport`，至少包含：
  - `chapter_number`
  - `overall_score`（0-100）
  - `issues[]`（每项包含 `issue_type`、`description`、`severity`，可选 `evidence` 与 `fix_instructions`）
  - `summary`

#### Scenario: Empty issues for passing chapters

- **WHEN** 章节未发现明显逻辑问题且评分不低于阈值
- **THEN** `issues` MAY 为空数组
- **AND** `summary` MUST 给出简短结论

### Requirement: Determine Blocking Conditions

系统 MUST 能基于评分与严重问题判断是否触发阻断。

#### Scenario: Block by score threshold

- **WHEN** `overall_score < logic_review_min_score`
- **THEN** 系统 MUST 将该章标记为需要修复（用于触发质量闸门）

#### Scenario: Block by high severity issue

- **WHEN** `issues` 中存在任意 `severity == "high"`
- **THEN** 系统 MUST 将该章标记为需要修复（用于触发质量闸门）

### Requirement: Persist Reports as Read-only Views

系统 MUST 将逻辑审查报告落盘为只读视图文件，不得作为正文真源。

#### Scenario: Save review report file

- **WHEN** 章节逻辑审查完成
- **THEN** 系统 MUST 保存 `projects/<project>/reviews/chapter_XXX_logic_review.json`
- **AND** 文件内容 MUST 可被后续 CLI/Agent 读取并回显摘要

