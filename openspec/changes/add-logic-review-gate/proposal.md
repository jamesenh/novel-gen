## Why

当前生成流程在「章节生成完成后」只做了一致性检测（更偏向“与上下文冲突/设定冲突”），但缺少对**章节与场景内容本身的合理性与逻辑连贯性**的系统性审查与门控，例如：

- 场景目的是否达成、人物动机是否合理、因果链是否断裂
- 场景之间的衔接是否突兀、信息揭示顺序是否导致理解断层
- 章节内部的推进节奏是否自洽（铺垫/转折/回收）

一旦出现严重逻辑问题，后续章节/场景继续生成会把错误“固化”并放大，导致修复成本激增。因此需要引入一个**可配置的逻辑审查质量闸门（Quality Gate）**：在发现严重问题或评分低于阈值时**阻断后续生成**，并产出可执行的“下一步”指引（报告/修订候选/应用修订）。

## What Changes

- **新增逻辑审查链（LLM 结构化输出）**
  - 章节级：基于 `ChapterPlan + GeneratedChapter + chapter_context` 输出结构化 `LogicReviewReport`（含 `overall_score`、`issues`、`summary`、`fix_instructions`）。
  - （可选后续）场景级：在场景生成后对单场景进行快速审查，但本提案以“章节级 gate”为主。

- **新增逻辑审查产物落盘**
  - `projects/<project>/reviews/chapter_XXX_logic_review.json`：章节逻辑审查报告（只读视图，不是正文真源）。
  - 与现有修订机制对齐：当触发阻断时，写入 `projects/<project>/chapters/chapter_XXX_revision.json`（`RevisionStatus.status="pending"`），作为“必须先修复”的闸门信号。

- **新增配置项（默认不改变现有行为）**
  - `logic_review_policy`: `"off" | "blocking"`（默认 `off`）
  - `logic_review_min_score`: `int`（默认建议 75）
  - 触发阻断条件：`overall_score < min_score` 或存在 `severity=="high"` 的 issue

- **工作流集成：阻断后续章节生成（无绕过模式）**
  - 在 `chapter_generation` 之后新增 `chapter_logic_review` 节点；若触发阻断：
    - 落盘报告与 `RevisionStatus(pending)`
    - 正常结束本次工作流（保存 checkpoint），并向上层返回“阻断原因 + 下一步建议”

- **全入口强制闸门**
  - 任意“生成类入口”（`workflow.run/resume`、`chapter.text.generate`、`scene.generate`、`scene.merge_to_chapter` 等）在执行前 MUST 检测是否存在 `pending` 修订：
    - 若存在 `blocked_chapter = min(pending.chapter_number)` 且目标章节/场景章节号 > `blocked_chapter`，则 MUST 失败并返回结构化错误（包含阻断章号、报告路径、建议操作）。
  - 不提供绕过模式（强一致质量门）。

- **Agent 交互（ng chat）对齐**
  - 遇到阻断时，Agent 回显阻断章号、评分/阈值、问题摘要、报告路径，并引导用户：
    - 查看报告（无确认）
    - 确认后生成修订候选（普通确认）
    - 确认后应用修订（破坏性确认）

## Impact

- **Affected specs（通过 spec deltas 更新/新增）**
  - `orchestration`：新增“逻辑审查 gate + pending 修订阻断”的编排契约
  - `configuration`：新增逻辑审查配置项与链级 LLM 配置
  - 新增能力：`logic-review`（报告结构与触发规则）

- **Affected code（实现阶段将改动/新增）**
  - 新增：`novelgen/runtime/logic_review.py`、`novelgen/chains/logic_review_chain.py`（或等价组织）
  - 修改：`novelgen/runtime/nodes.py`、`novelgen/runtime/workflow.py`、`novelgen/runtime/orchestrator.py`
  - 修改：`novelgen/models.py`（新增 LogicReviewReport 模型或扩展）
  - 修改：`novelgen/tools/*`、`novelgen/agent/chat.py`（全入口闸门与交互）

## Non-Goals（本提案不做）

- 不提供“绕过阻断继续生成”的模式
- 不自动应用修订（阻断后先提示用户，经确认后才生成候选稿；应用候选仍需破坏性确认）
- 不在本提案中引入复杂的多轮诊断/自动拆分问题（以结构化报告 + 最小候选修订为主）

