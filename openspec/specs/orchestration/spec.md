# orchestration Specification

## Purpose

编排器模块负责协调整个小说生成流程，管理 6 步生成步骤（世界观→主题冲突→角色→大纲→章节计划→场景文本）的执行顺序、依赖关系和状态持久化。编排器基于 LangGraph StateGraph 实现，支持检查点恢复、断点续跑和动态章节扩展。

**技术实现**：
- 使用 LangGraph `StateGraph` 定义工作流，状态类型为 `NovelGenerationState`
- 使用 `SqliteSaver` 实现检查点持久化（存储在 `workflow_checkpoints.db`）
- 使用 Mem0 作为唯一的记忆存储层（必须启用）
- 支持条件边实现自动跳过已完成步骤
- 支持场景级子工作流（`SceneGenerationState`）
- 支持动态章节扩展（剧情进度评估→大纲扩展→新章节计划）
- 支持递归限制预估机制，防止 `GraphRecursionError`

**代码位置**：
- `novelgen/runtime/orchestrator.py` - 主编排器类
- `novelgen/runtime/workflow.py` - LangGraph 工作流定义
- `novelgen/runtime/nodes.py` - 工作流节点实现

## Requirements

### Requirement: Coordinate Multi-step Novel Generation

The system MUST provide an orchestrator to coordinate the 6-step novel generation process, managing project files, handling dependency relationships, and tracking progress.

#### Scenario: Chain execution with prerequisites

- **WHEN** 执行某步骤时（如 step3_create_characters）
- **THEN** 编排器应验证所需前置数据是否存在
- **AND** 前置数据缺失时应抛出 ValueError 并提示正确的执行顺序

#### Scenario: Save JSON outputs

- **WHEN** 任意生成步骤完成
- **THEN** 编排器应将结果保存到 projects/{project_name}/ 目录的 JSON 文件中
- **AND** 文件名和路径应遵循项目约定

#### Scenario: Reuse existing results

- **WHEN** 调用生成步骤且 force=False（默认）
- **THEN** 若对应 JSON 文件存在且能被 Pydantic 模型解析，应跳过生成并使用现有结果
- **AND** 控制台应打印跳过信息提示用户

#### Scenario: Force regeneration

- **WHEN** 调用生成步骤且 force=True
- **THEN** 系统应忽略现有文件并重新生成内容
- **AND** 覆盖原文件保存新结果

#### Scenario: Batch chapter processing

- **WHEN** 调用 generate_all_chapters()
- **THEN** 系统应遍历 outline.json 中所有章节
- **AND** 依次为每个章节执行 plan 生成和 text 生成
- **AND** 处理失败时应记录错误并继续下一章

#### Scenario: Manage project lifecycle

- **WHEN** 初始化 NovelOrchestrator 时
- **THEN** 应创建项目目录结构（项目和章节子目录）
- **AND** 确保目录可写入

#### Scenario: Provide verbose logging

- **WHEN** verbose=True is set during initialization
- **THEN** the system MUST output detailed generation information
- **AND** MUST include LLM call duration, token usage, prompt content, and other debugging information

### Requirement: Parameterized Chapter Scope for Planning and Text Generation

The orchestrator MUST expose a consistent, parameter-driven API to control which chapters are planned and generated at step5/step6.

#### Scenario: Generate all chapters by default

- **WHEN** 用户直接调用 `generate_all_chapters()` 且未显式限制章节范围
- **THEN** orchestrator MUST 读取 outline.json 中的全部章节编号
- **AND** 对每一章依次执行 `step5_create_chapter_plan` 与 `step6_generate_chapter_text`

#### Scenario: Generate subset of chapters by argument

- **WHEN** 用户调用章节相关 API 并传入特定的章节编号列表（例如 `step5_create_chapter_plan([1,2,3])` 或 `generate_all_chapters(chapter_numbers=[1,2,3])`）
- **THEN** orchestrator MUST 仅为这些章节执行章节计划与章节正文生成
- **AND** 其他章节 MUST 不被修改

### Requirement: Persist Structured Chapter Memory

The orchestrator MUST maintain a structured `chapter_memory.json` ledger that is updated after each chapter generation to capture continuity-critical facts.

#### Scenario: Append chapter memory entry

- **WHEN** step6_generate_chapter_text() 完成
- **THEN** 系统应根据本章场景摘要写入一条记忆记录，字段至少包含时间锚点、地点、主要事件、角色状态、悬念/未决目标
- **AND** 记录应附带章节编号并可供后续步骤查询最近 N 章

#### Scenario: Feed memory into downstream steps

- **WHEN** 执行 step5_create_chapter_plan 或 step6_generate_chapter_text
- **THEN** orchestrator MUST 注入最近 N 章的记忆（列表或聚合摘要）到调用链参数中
- **AND** 缺少记忆文件时应优雅回退到空列表

### Requirement: Run Automatic Consistency Check

The orchestrator MUST run a consistency verification step after each chapter is generated, leveraging accumulated chapter memory.

#### Scenario: Evaluate conflicts after generation

- **WHEN** 某章文本生成后
- **THEN** 系统应调用一致性检测链，输入章节上下文（记忆+大纲依赖）与新章节全文
- **AND** 检测结果需包含冲突列表（字段：类型、涉及角色/事件、描述）
- **AND** 一旦发现冲突，必须记录到项目目录的报告文件，供后续修订

#### Scenario: Optional auto-revision hook

- **WHEN** 检测结果标记为可自动修复级别
- **THEN** orchestrator MUST 触发 revision 链或提示用户手动处理，并在日志中回显处理状态

### Requirement: Force-controlled Chapter Text Generation

The orchestrator MUST support force-controlled reuse and regeneration behavior specifically for step6 chapter text generation.

#### Scenario: Reuse existing chapter text when force is False

- **WHEN** 调用 `step6_generate_chapter_text(chapter_number, force=False)`
- **AND** projects/{project_name}/chapters 目录下存在对应的 `chapter_{chapter_number:03d}.json` 文件且能被 GeneratedChapter 模型解析
- **THEN** orchestrator MUST 直接复用该章节对象，跳过场景级 LLM 生成调用
- **AND** 在控制台输出说明已复用的提示（包含章节编号和文件路径）

#### Scenario: Force regenerate chapter text when force is True

- **WHEN** 调用 `step6_generate_chapter_text(chapter_number, force=True)`
- **AND** 无论 `chapter_{chapter_number:03d}.json` 是否存在
- **THEN** orchestrator MUST 忽略现有文件，重新生成本章所有场景文本并覆盖写入
- **AND** 在控制台输出"强制重算"的提示

#### Scenario: Apply force semantics in batch chapter generation

- **WHEN** 调用 `generate_all_chapters(force=False)`（或等效批量生成入口）
- **AND** 某些章节的 `chapter_{chapter_number:03d}.json` 已存在且可解析
- **THEN** orchestrator MUST 对这些章节复用现有文本，仅为缺失章节调用 step6 生成
- **AND** 当 `force=True` 时，系统 MUST 为所有章节重新生成文本并覆盖旧文件

### Requirement: Consistency Detection and Revision Trigger

编排器在章节生成后 MUST 执行一致性检测，并根据检测结果中是否有修复建议（`fix_instructions`）触发修订流程。

#### Scenario: Trigger auto-apply revision based on fix_instructions

- **WHEN** revision_policy == "auto_apply" 且一致性检测报告包含至少一个带有 `fix_instructions` 的问题
- **THEN** 编排器 MUST：
  - 收集所有带有 `fix_instructions` 的 issue（不再检查 `can_auto_fix` 字段）
  - 拼接所有 `fix_instructions` 为 revision_notes
  - 调用修订链进行自动修复
  - 将修订后的章节写回 JSON

#### Scenario: Generate manual-confirm candidate based on fix_instructions

- **WHEN** revision_policy == "manual_confirm" 且一致性检测报告包含至少一个带有 `fix_instructions` 的问题
- **THEN** 编排器 MUST：
  - 收集所有带有 `fix_instructions` 的 issue
  - 调用修订链生成修订候选
  - 保存修订候选到 `chapter_XXX_revision.json`
  - 标记章节状态为 pending

#### Scenario: No revision needed

- **WHEN** 一致性检测报告中所有 issue 的 `fix_instructions` 均为 None 或空字符串
- **THEN** 编排器 MUST：
  - 跳过修订流程
  - 保持原始章节 JSON 不变
  - 继续后续流程

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

### Requirement: LangGraph Workflow Integration

The orchestrator MUST use LangGraph StateGraph for workflow orchestration with checkpoint persistence.

#### Scenario: Initialize LangGraph workflow

- **WHEN** 初始化 NovelOrchestrator
- **THEN** 系统 MUST 创建 LangGraph StateGraph 工作流
- **AND** 使用 SqliteSaver 作为检查点持久化后端
- **AND** 检查点数据库保存在 `workflow_checkpoints.db`

#### Scenario: Auto-skip completed steps

- **WHEN** 工作流执行时检测到某步骤的输出文件已存在
- **THEN** 系统 MUST 通过条件边自动跳过该步骤
- **AND** 在控制台输出跳过信息

#### Scenario: Resume from checkpoint

- **WHEN** 调用 `resume_workflow()` 恢复执行
- **THEN** 系统 MUST 从最新检查点恢复状态
- **AND** 同步文件系统状态到检查点
- **AND** 继续执行未完成的步骤

### Requirement: Mem0 Integration

The orchestrator MUST require Mem0 as the memory layer and fail fast if not configured.

#### Scenario: Require Mem0 configuration

- **WHEN** 初始化 NovelOrchestrator 且 Mem0 未启用
- **THEN** 系统 MUST 抛出 RuntimeError
- **AND** 错误信息 MUST 说明需要设置 MEM0_ENABLED=true

#### Scenario: Initialize Mem0 manager

- **WHEN** Mem0 已启用且配置正确
- **THEN** 系统 MUST 创建 Mem0Manager 实例
- **AND** 执行健康检查确认连接正常
- **AND** 在控制台输出 Mem0 启用确认信息

### Requirement: Project State Query and Rollback

The orchestrator MUST support querying project state and rolling back to previous steps or chapters.

#### Scenario: Query project state

- **WHEN** 调用 `get_project_state()`
- **THEN** 系统 MUST 返回包含以下信息的字典：
  - steps: 各基础步骤的完成状态
  - chapters: 每个章节的计划、场景、完成状态
  - checkpoint_exists: 检查点数据库是否存在

#### Scenario: Rollback to step

- **WHEN** 调用 `rollback_to_step(step_name)`
- **THEN** 系统 MUST 删除该步骤及之后所有步骤的输出文件
- **AND** 清理相关的章节记忆和 Mem0 记忆
- **AND** 删除检查点数据库

#### Scenario: Rollback to chapter

- **WHEN** 调用 `rollback_to_chapter(chapter_number)`
- **THEN** 系统 MUST 删除该章节及之后所有章节的文件
- **AND** 保留章节计划文件
- **AND** 清理相关记忆

#### Scenario: Rollback to scene

- **WHEN** 调用 `rollback_to_scene(chapter_number, scene_number)`
- **THEN** 系统 MUST 删除该场景及之后所有场景文件
- **AND** 删除该章节的合并文件
- **AND** 精确清理 Mem0 中的场景记忆

### Requirement: Recursion Limit Management

The orchestrator MUST manage LangGraph recursion limits to prevent GraphRecursionError.

#### Scenario: Configure recursion limit

- **WHEN** 初始化工作流
- **THEN** 系统 MUST 从环境变量 LANGGRAPH_RECURSION_LIMIT 读取递归限制（默认 500）
- **AND** 将限制值传入 workflow.invoke() 的 config

#### Scenario: Proactive stop on limit approach

- **WHEN** 节点执行计数接近递归限制
- **THEN** 系统 MUST 预估剩余步数是否足够完成下一章
- **AND** 如果不足，MUST 主动停止并设置 should_stop_early 标志
- **AND** 在控制台输出警告信息

### Requirement: Dynamic Chapter Extension

The orchestrator MUST support dynamic chapter extension based on story progress evaluation.

#### Scenario: Evaluate story progress

- **WHEN** 所有已规划章节生成完毕且大纲未完成
- **THEN** 系统 MUST 调用剧情进度评估节点
- **AND** 评估结果包含 evaluation_result（continue/wrap_up/force_end）

#### Scenario: Extend outline based on evaluation

- **WHEN** 评估结果为 continue 或 wrap_up
- **THEN** 系统 MUST 调用大纲扩展节点生成新章节
- **AND** 更新 Outline.chapters 列表
- **AND** 更新 Outline.current_phase

#### Scenario: Generate plans for new chapters

- **WHEN** 大纲扩展完成
- **THEN** 系统 MUST 为新章节生成章节计划
- **AND** 重新初始化章节循环继续生成

### Requirement: Cleanup and Resource Management

The orchestrator MUST properly cleanup resources on exit.

#### Scenario: Close resources on cleanup

- **WHEN** 调用 `cleanup()` 方法
- **THEN** 系统 MUST 关闭 Mem0 管理器
- **AND** 关闭 SQLite 检查点连接
- **AND** 终止后台线程

#### Scenario: Graceful shutdown on interrupt

- **WHEN** 收到键盘中断信号（Ctrl+C）
- **THEN** 系统 SHOULD 优雅地停止当前工作流
- **AND** 保存当前状态到检查点
- **AND** 输出中断确认信息
