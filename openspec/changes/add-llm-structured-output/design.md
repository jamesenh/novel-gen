## Context
当前项目所有链的输出都通过 Pydantic 模型描述，并依赖 LangChain + JSON 提示词来实现结构化输出。为了解决 JSON 解析失败与未转义引号等问题，项目已经引入自定义的 `LLMJsonRepairOutputParser`，在解析失败时再次调用同一个 LLM 修复输出。但随着场景复杂度和正文长度的提升，仅靠提示词约束和事后修复已不足以保证稳定性。

与此同时，LangChain 1.x 为 OpenAI 等模型提供了 `with_structured_output(PydanticModel)` 能力，可以在协议层（JSON mode / 工具调用）约束输出，大幅降低结构偏差和转义错误的概率。本提案希望在不破坏现有 6 步生成流程和模块划分的前提下，引入这一能力，并为不支持 JSON 模式的后端保留现有修复路径。

## Goals / Non-Goals
- Goals:
  - 为支持 JSON 模式的 LLM 后端提供首选的结构化输出实现（`with_structured_output`），减少 JSON 解析相关故障
  - 保持对兼容端点（如部分 Qwen/ModelScope）的良好兼容性，在无法使用 JSON 模式时自动退回现有解析+修复路径
  - 在规范层预留“结构与正文拆步生成”的演进空间，为后续进一步降低转义错误做好铺垫
- Non-Goals:
  - 不改变现有 6 步生成管道及其职责划分
  - 不一次性重写所有链的提示词，仅在必要处调整输出格式相关段落
  - 不新增额外服务或数据库，仅在现有代码库内部演进

## Decisions
- Decision 1：
  - **在支持 JSON 模式/工具调用的后端上，链级优先使用 `llm.with_structured_output(PydanticModel)` 实现结构化输出。**
  - 原因：LangChain 已为主流模型提供稳定支持，可以在协议层减少格式偏差，而不是完全依赖提示词。
- Decision 2：
  - **保留 `PydanticOutputParser + LLMJsonRepairOutputParser` 作为非 JSON 模式后端的兜底实现，并在其中增加统一的输出清洗逻辑。**
  - 原因：兼容端点实现能力不一，完全移除现有路径会带来较大风险；通过轻量清洗可提升成功率。
- Decision 3：
  - **对场景文本与章节修订这类“长正文 + 结构信息”场景，后续提案可引入“两步生成（结构 + 正文）+ 代码侧组装 Pydantic”的模式。**
  - 原因：这是从根源上解决转义问题的方向，但需要单独评估，对当前提案仅做规范层预留。

## Risks / Trade-offs
- 风险：
  - 不同模型供应商对 JSON 模式/工具调用的兼容程度不一，可能导致在部分环境下 structured_output 模式不生效或报错。
  - 在同一代码路径中同时支持 structured_output 与传统解析+修复，会增加一定逻辑复杂度。
- 权衡：
  - 通过在链配置或 LLMConfig 中增加显式开关/后端类型判断，可以将复杂度控制在有限范围内；
  - 遇到不支持 structured_output 的后端时，明确退回现有实现，避免“半启用半失败”的不确定状态。

## Migration Plan
- 在实现阶段按链分批切换：
  1. 先为易于验证的结构化链（如角色/章节计划）接入 structured_output；
  2. 再评估并接入场景文本与章节修订链；
  3. 在每一步都保留旧路径，确保可以通过配置回滚到原有行为。
- 所有变更在合并前需：
  - 通过 `openspec validate add-llm-structured-output --strict`；
  - 在至少一个 demo 项目上跑通完整流程，记录前后 JSON 解析失败率与修复调用次数的对比（哪怕是人工统计）。

## Open Questions
- 不同兼容端点（特别是 Qwen/ModelScope）的 JSON 模式支持程度如何？是否需要在规范层为“部分支持”单独建能力条目？
- 是否需要为 `LLMJsonRepairOutputParser` 增加更细粒度的 metrics（如每条链/每个阶段的修复次数、最终失败率），以便后续评估 structured_output 的收益？
