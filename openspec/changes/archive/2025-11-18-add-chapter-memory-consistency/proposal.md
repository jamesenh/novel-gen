# Proposal: add-chapter-memory-consistency

## Why
章节之间的割裂主要来源于「没有结构化记忆」「场景之间仅靠计划目的串联」「缺乏自动一致性复核」。demo_002 已能生成质量不错的单章内容，但：
- Chapter 2 进入禁忌之地，Chapter 3 却直接回到议事厅；
- `previous_summary` 只是场景计划的 purpose 文本，无法承载真实结果；
- 提示词没有全章上下文，更无法参考前几章的状态差分；
- 生成后没有一致性检查流程；
- 大纲也缺少时间线与依赖信息，导致后续步骤无从校验。

## What Changes
- **新增章节记忆系统**：引入`chapter_memory.json`文件，记录每章结束时的角色状态、悬念、时间节点等结构化信息
- **改进场景摘要传递**：step6中生成场景后立刻生成真实摘要，替换下一场景的`previous_summary`
- **扩展章节上下文注入**：scene_text_chain的prompt增加`chapter_context`字段，包含最近N章摘要和状态diff
- **新增一致性检查自动化**：每章完成后自动运行一致性检测，识别设定冲突并输出报告
- **实现分阶段依赖验证**：step5验证逻辑有效性，step6开始前验证实际依赖满足情况
- **增强大纲模型**：ChapterSummary模型支持`timeline_anchor`和`dependencies`字段

## Impact
- Affected specs: orchestration, scene-text-generation, chapter-memory
- Affected code: novelgen/runtime/orchestrator.py, novelgen/models.py, novelgen/chains/scene_text_chain.py, novelgen/runtime/memory.py, novelgen/runtime/consistency.py, novelgen/config.py

## Goals
1. 建立章节记忆表，记录每章结束时的角色状态、悬念、时间节点等字段，并在生成下一章计划与文本时自动注入。
2. 生成场景文本时，用真实上一场景摘要替换 `previous_summary`，驱动更细粒度的承接。
3. 扩展 scene_text_chain 的提示词，传入最近 N 章的「章节概要 + 关键状态 diff」，确保跨章连贯。
4. 引入自动一致性自检：每章写完后对比历史记忆，输出冲突清单并触发修订/告警流程。
5. 大纲层新增「时间线锚点」「依赖关系」，并提供校验规则，保证章序逻辑。

## Scope & Approach
- **数据流**：在 orchestrator 中引入 `chapter_memory.json`，每章写完即通过 `summarize_scenes` + 结构化解析生成记忆条目；章节计划和场景写作链会读取最近条目。
- **场景摘要传递**：生成场景后立刻生成摘要并作为下一场景的 `previous_summary`，杜绝只用 plan purpose 的情况。
- **章节上下文**：scene_text_chain 的 prompt 增加 `chapter_context` 字段，内容为最近 N 章摘要 + 状态 diff（角色
time
events），并在系统指令中明确「不得违背上下文事实」。
- **一致性自检**：新增 `consistency_check_chain`（或同类工具），输入「章节上下文 + 新章全文」，输出冲突列表；若有问题则调用 revision 链或标记为需人工处理。
- **大纲增强**：outline generation 增加 `timeline_anchor`（如 T+3 天）和 `dependencies`（依赖章节ID/事件）；采用分阶段验证策略：step5阶段只验证依赖关系的逻辑有效性（如不依赖未来章节），step6开始前验证实际依赖满足情况（基于章节内容文件存在性）。

## Non-Goals
- 不实现完整的向量数据库记忆，仅限结构化JSON。
- 不改动 LLM 提供者或计费策略。

## Risks
- 记忆表结构需稳定，否则后续解析困难。
- 摘要生成与一致性检查会额外耗费 token，需在任务中评估上限。

## Validation
- 单元/集成测试覆盖：
  - 新增记忆条目生成逻辑的序列化测试。
  - `step5`/`step6` 在存在记忆时正确注入字段。
  - scene_text_chain 的 prompt builder 能携带章节上下文。
  - 一致性检查在模拟冲突文本时返回预期告警。
  - 大纲带依赖字段时，未满足依赖能被校验捕获。
