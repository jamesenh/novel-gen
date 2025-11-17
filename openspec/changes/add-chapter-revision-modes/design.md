## Context

当前系统在 step6 生成章节文本后，会执行：
- 基于 `GeneratedChapter` 生成章节记忆（chapter memory）；
- 调用一致性检测（consistency check），得到 `ConsistencyReport`；
- 若存在可自动修复问题，则通过 `runtime/revision.py` 生成修订文本，写入 `chapter_XXX_revised.txt`。

但：
- 后续的记忆、下游章节生成和导出都只使用 `chapter_XXX.json` 中的场景文本；
- 修订结果不会回写 JSON，也不会影响章节记忆；
- 没有「人工确认」的统一机制，更没有流程级的 gating。

本设计将修订视为 orchestrator 管道中的一个可配置阶段，通过策略模式控制：
- 是否执行修订；
- 修订如何影响章节 JSON 真源；
- 是否在人工确认前阻断后续章节生成。

## Goals / Non-Goals

- **Goals**
  - 将章节修订纳入编排 pipeline，而不是孤立的 txt 副产物；
  - 提供两种行为清晰的修订模式：`auto_apply` 与 `manual_confirm`；
  - 明确章节 JSON 为唯一正文真源，修订一旦生效必须回写 JSON；
  - 在 manual 模式下，为后续章节生成提供「强制人工确认后再继续」的 gating 能力。

- **Non-Goals**
  - 不在本变更中设计复杂的 UI 或交互，只约束行为与接口；
  - 不在本变更中完全重写修订链 prompt，仅约束其输入输出角色；
  - 不引入数据库或复杂状态机，状态仍然基于 JSON 文件管理。

## Decisions

### 1. 引入 revision_policy 作为 orchestrator 策略

- 在 `ProjectConfig` 中新增字段（具体 schema 由实现负责）：
  - `revision_policy: "none" | "auto_apply" | "manual_confirm"`；
- orchestrator 在 step6 内部根据该策略决定：
  - 是否调用修订链；
  - 修订结果是否直接回写 JSON；
  - 是否生成「待确认」状态并阻断后续流程。

### 2. 章节 JSON 作为唯一正文真源

- 明确约束：
  - 对外暴露的章节内容（导出、记忆生成、下游章节上下文）必须以 `chapter_XXX.json` 为准；
  - `_revised.txt` 仅作为审阅视图或中间产物，不能成为第二套真源；
- 当修订被「应用」时（无论自动或人工确认后）：
  - 系统 MUST 将修订结果映射回 `GeneratedChapter.scenes[*].content`；
  - MUST 重新计算 `total_words` 并覆盖写回 JSON 文件；
  - MAY 备份原始 JSON（如 `chapter_XXX_original.json`），由实现自行决定。

### 3. auto_apply 模式行为

- 触发条件：
  - `revision_policy == "auto_apply"`；
  - 当前章节一致性报告中存在具有 `fix_instructions` 的 issue。
- 调度流程：
  1. 一致性检测完成后，编排器收集所有可自动修复的 issue，拼接为 `revision_notes`；
  2. 将「原始章节整合文本」与 `revision_notes` 传入修订链；
  3. 获得修订后的整章文本后，解析并更新 `GeneratedChapter` 对象；
  4. 覆盖写回 `chapter_XXX.json`，确保之后的导出与记忆均使用修订结果；
  5. 重新生成章节记忆（或至少允许实现选择在修订后重建记忆）。
- 允许：
  - 实现层可选择继续写入 `_revised.txt` 以方便人工对照审阅，但这不是真源。

### 4. manual_confirm 模式行为

- 触发条件：
  - `revision_policy == "manual_confirm"`；
  - 一致性报告中存在可自动修复的 issue。
- 调度流程：
  1. 一致性检测完成后，编排器同样收集 issue 并生成修订候选文本；
  2. 将候选文本与元数据（问题列表、revision_notes、时间戳等）保存到项目目录下的**修订状态文件**中（具体格式留给实现）；
  3. 不直接修改 `chapter_XXX.json`，原始 JSON 仍然是当前真源；
  4. 将当前章节标记为「待人工确认」状态；
  5. `generate_all_chapters()` 在默认行为下：
     - 若发现存在编号小于当前章节且处于「待确认」状态的章节，MUST 阻止继续生成并给出可读错误，列出需要先处理的章节编号。
- 需要提供的操作：
  - 系统 MUST 暴露一个显式「应用修订」的操作（例如 CLI 命令或 runtime 函数），其行为为：
    1. 读取修订状态文件和修订候选文本；
    2. 将修订内容映射回 `GeneratedChapter` 并回写 `chapter_XXX.json`；
    3. 更新修订状态为已接受（accepted）；
    4. 触发或允许调用方触发章节记忆重建；
  - 该操作不要求在本 design 中约束具体 API 形态，只要求存在清晰的「从待确认到已应用」的状态迁移。

### 5. 与 existing behavior 的兼容策略

- 默认策略由实现决定，但推荐：
  - 默认 `revision_policy == "none"`，与当前行为保持一致，避免对现有项目造成不可预期的文本修改；
- 启用 auto / manual 模式应通过：
  - 配置文件 / 环境变量（例如 `NOVELGEN_REVISION_POLICY`）；
  - 或 `NovelOrchestrator` 构造参数（高优先级覆盖配置）。

### 6. 修订链输出结构化 GeneratedChapter

- 修订链的输出契约调整为：
  - 输入：原始章节的 GeneratedChapter 结构（或等价 JSON 表示） + `revision_notes`；
  - 输出：完整的、已修订的 GeneratedChapter 结构；
- 实现要求：
  - MUST 使用 Pydantic 模型 `GeneratedChapter` 作为结构化输出约束（例如通过 LangChain 的 `with_structured_output`）；
  - MUST 保持 `chapter_number` 和 `chapter_title` 不变，除非修复的是标题错误本身；
  - SHOULD 在不必要时避免增加/删除场景数量，优先在原有 `scenes[*].content` 上做最小必要修改；
- 基于该契约：
  - auto_apply 模式可以直接使用修订链返回的 GeneratedChapter 覆盖章节 JSON；
  - manual_confirm 模式在状态文件中保存的是修订候选的 GeneratedChapter（或其 JSON），并可选附带人类可读的对比文本（例如 `_revised.txt`）。

## Risks / Trade-offs

- **风险：自动应用可能「过度修改」文本**
  - 缓解：默认策略不启用 auto_apply，用户需显式选择；
  - 在 design 层明确章节 JSON 备份和日志记录的重要性。
- **风险：manual 模式引入新的状态管理复杂度**
  - 缓解：
    - 状态仍基于 JSON 文件，不引入数据库；
    - 仅引入有限的状态枚举（pending/accepted/rejected），并由实现定义数据模型；
- **权衡：在修订后是否强制重建章节记忆**
  - 设计层推荐：在 auto_apply 和 manual_confirm-accepted 两种情况下，系统 SHOULD 重建章节记忆；
  - 但为简化实现，不强制规定必须自动重建，可通过单独任务补充约束。

## Migration Plan

- 新增 `revision_policy` 字段时，应为旧项目提供默认值，避免加载失败；
- 对已有项目：
  - 若未配置策略，则行为与当前版本保持一致；
  - 在文档中说明如何为已有项目开启 auto / manual 模式；
- 实现应添加日志输出，在首次启用修订模式时提示当前策略和行为差异。

## Open Questions

- manual 模式下，是否允许在存在 pending 章节时继续生成后续章节但附带强提醒？
  - 当前设计倾向于「默认阻断，提供高级参数绕过」的模式，可在实现阶段细化。
