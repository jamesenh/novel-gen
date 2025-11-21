## ADDED Requirements
### Requirement: Structured Revision Chain
The system MUST provide a revision chain that accepts a GeneratedChapter structure and revision notes, and outputs a revised GeneratedChapter structure.

#### Scenario: Revision chain accepts structured input
- **WHEN** 调用修订链进行章节修订
- **THEN** 修订链 MUST 接受以下输入：
  - 原始章节的 GeneratedChapter 结构（JSON 格式）
  - 修订说明文本（revision_notes，来自一致性报告的问题汇总）
- **AND** 修订链 MUST 使用 Pydantic 模型 GeneratedChapter 作为结构化输出约束

#### Scenario: Revision chain preserves chapter metadata
- **WHEN** 修订链生成修订结果
- **THEN** 输出的 GeneratedChapter MUST 保持 chapter_number 和 chapter_title 与输入一致
- **AND** SHOULD 优先修改场景内容（scenes[*].content）而非增加或删除场景
- **AND** MUST 重新计算 total_words 以反映修订后的实际字数

### Requirement: Chapter Revision Modes
The orchestration system MUST support configurable chapter revision modes that define how consistency-check-driven revisions are applied to chapter content.

#### Scenario: Configure revision policy
- **WHEN** 初始化 NovelOrchestrator 或加载 ProjectConfig 时
- **THEN** 系统 MUST 支持通过配置字段（如 revision_policy）选择章节修订策略
- **AND** 支持的策略枚举至少包括: "none", "auto_apply", "manual_confirm"
- **AND** 在未显式配置时，默认行为 MUST 与现有版本保持一致（不自动修改章节 JSON）

#### Scenario: Treat JSON as single source of truth
- **WHEN** 一章文本已经生成并可能触发修订
- **THEN** 编排器 MUST 将 `projects/{project_name}/chapters/chapter_XXX.json` 视为该章正文的唯一真源
- **AND** 导出整书、生成章节记忆和后续章节上下文时 MUST 仅使用章节 JSON 中的内容
- **AND** 修订候选文本（如 `chapter_XXX_revised.txt`）仅作为中间产物或审阅视图，不得作为独立真源

#### Scenario: Auto-apply revision to chapter JSON
- **WHEN** revision_policy == "auto_apply" 且对某章执行一致性检测后发现可自动修复的问题
- **THEN** 编排器 MUST：
  - 收集所有带有 `fix_instructions` 修复指令的 issue，拼接为修订说明（revision_notes）
  - 将原始章节的 GeneratedChapter 结构和 revision_notes 传入修订链
  - 直接获取修订链输出的结构化 GeneratedChapter
  - 使用修订链返回的 GeneratedChapter 覆盖写回 `chapter_XXX.json`，使其成为新的正文真源
- **AND** 系统 SHOULD 在修订应用后重建章节记忆或提供显式入口以重建记忆
- **AND** 系统 MAY 将修订后的 GeneratedChapter 导出为可读文本文件供审阅

#### Scenario: Produce manual-confirm revision candidate
- **WHEN** revision_policy == "manual_confirm" 且一致性检测发现可自动修复的问题
- **THEN** 编排器 MUST：
  - 将原始章节的 GeneratedChapter 和修复指令（revision_notes）传入修订链
  - 获取修订链输出的结构化 GeneratedChapter 作为修订候选
  - 将修订候选 GeneratedChapter 和相关元数据（问题列表、revision_notes、时间戳等）保存到修订状态文件（如 `chapter_XXX_revision.json`）
  - 保持 `chapter_XXX.json` 不变，即该章正文仍为未修订版本
  - 将该章节标记为处于 "pending" 状态
- **AND** 系统 MAY 将修订候选导出为可读文本以便人工对比

#### Scenario: Gate further generation on pending revisions
- **WHEN** 调用 generate_all_chapters() 且存在章节处于修订待确认状态
- **THEN** 在默认配置下，编排器 MUST 阻止对后续章节的生成
- **AND** MUST 抛出可读错误或日志，指出哪些章节需要先处理修订（列出章节编号）

#### Scenario: Apply manual-confirmed revision
- **WHEN** 调用显式的「应用修订」操作（例如 CLI 命令或 runtime 函数）针对某一章
- **THEN** 系统 MUST：
  - 读取修订状态文件中的修订候选 GeneratedChapter
  - 直接使用该 GeneratedChapter 覆盖写回 `chapter_XXX.json`
  - 更新修订状态为 "accepted"，并记录确认时间
- **AND** 系统 SHOULD 触发或指导调用方重建该章的章节记忆

### Requirement: Preserve Backward-compatible Default Behavior
The introduction of chapter revision modes MUST NOT change behavior for existing projects that do not configure revision settings.

#### Scenario: Default to non-revision mode
- **WHEN** 现有项目未配置 revision_policy 时初始化 orchestrator
- **THEN** 系统 MUST 保持当前行为：
  - 一致性检测仍会生成报告和可选的修订候选文本文件
  - 不会自动修改章节 JSON 内容
  - 不会阻止 generate_all_chapters() 的执行
- **AND** 新增的修订模式只会在显式配置后生效
