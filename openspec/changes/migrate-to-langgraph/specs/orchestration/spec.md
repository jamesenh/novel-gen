## ADDED Requirements

### Requirement: LangGraph Stateful Workflow
系统 MUST 使用 LangGraph StateGraph 实现小说生成工作流，提供统一的状态管理、检查点（checkpointing）和灵活的流程控制能力。

#### Scenario: 定义工作流状态模型
- **WHEN** 初始化 LangGraph 工作流时
- **THEN** 系统 MUST 定义 `NovelGenerationState` Pydantic 模型，包含以下字段组：
  - 项目元信息（project_name, project_dir）
  - 配置（settings）
  - 6步生成结果（world, theme_conflict, characters, outline, chapters_plan, chapters）
  - 记忆与上下文（chapter_memories, entity_states, recent_context）
  - 工作流控制（current_step, completed_steps, failed_steps）
- **AND** 状态模型 MUST 支持 Pydantic 序列化/反序列化

#### Scenario: 创建 StateGraph 工作流
- **WHEN** 调用 `create_novel_generation_workflow()` 函数时
- **THEN** 系统 MUST 返回编译后的 LangGraph StateGraph，包含：
  - 至少 6 个核心节点（对应 6 步生成流程）
  - 线性边连接主流程节点
  - 条件边支持分支逻辑（如一致性检测后的修订）
  - MemorySaver 作为默认 checkpointer
- **AND** 工作流 MUST 支持通过 `.draw()` 方法可视化

#### Scenario: 节点包装现有 chains
- **WHEN** 定义工作流节点时
- **THEN** 每个节点 MUST 遵循以下模式：
  1. 从 `NovelGenerationState` 提取所需输入
  2. 调用现有的 LangChain chain（不修改 chain 本身）
  3. 返回字典更新状态（仅包含变更字段）
- **AND** 节点函数 MUST 具有签名 `(state: NovelGenerationState) -> Dict`

#### Scenario: 工作流执行与状态传递
- **WHEN** 调用工作流的 `.invoke(initial_state)` 方法时
- **THEN** 系统 MUST 按图定义的顺序执行节点
- **AND** 每个节点执行后 MUST 更新状态
- **AND** 后续节点 MUST 能访问前序节点更新的状态字段
- **AND** 执行完成后返回最终的 `NovelGenerationState`

### Requirement: Checkpointing 支持工作流暂停与恢复
系统 MUST 实现 LangGraph checkpointing 机制，允许长时间运行的生成任务在中断后从断点恢复。

#### Scenario: 自动保存检查点
- **WHEN** 工作流执行过程中
- **THEN** LangGraph MUST 在每个节点执行后自动保存检查点
- **AND** 检查点 MUST 包含完整的 `NovelGenerationState` 快照
- **AND** 使用 `MemorySaver` 时，检查点保存在内存中

#### Scenario: 从检查点恢复执行
- **WHEN** 调用工作流的 `.invoke()` 并提供 `checkpoint_id` 参数时
- **THEN** 系统 MUST 从指定检查点加载状态
- **AND** MUST 从中断节点的下一个节点继续执行
- **AND** 已完成的节点 MUST 不被重新执行

#### Scenario: 检查点标识与查询
- **WHEN** 用户需要查看或恢复检查点时
- **THEN** 系统 MUST 提供检查点列表查询功能
- **AND** 每个检查点 MUST 包含：时间戳、当前步骤标识、项目名称
- **AND** 支持通过项目名称过滤检查点

### Requirement: 条件分支与动态路由
系统 MUST 支持基于状态条件的工作流分支，实现复杂逻辑（如一致性检测后的自动修订）。

#### Scenario: 定义条件边
- **WHEN** 在 StateGraph 中添加条件边时
- **THEN** 系统 MUST 支持通过判断函数决定下一个节点
- **AND** 判断函数 MUST 接收 `NovelGenerationState` 并返回目标节点标识（字符串）
- **AND** 条件边 MUST 支持多路分支（字典映射返回值到节点）

#### Scenario: 一致性检测后的修订分支
- **WHEN** 章节生成后执行一致性检测节点
- **THEN** 系统 MUST 根据检测结果中的 `fix_instructions` 字段判断是否需要修订
- **AND** 如果需要修订，MUST 路由到 `chapter_revision` 节点
- **AND** 如果不需要修订，MUST 继续下一章生成或结束流程

#### Scenario: 章节循环控制
- **WHEN** 执行章节生成流程时
- **THEN** 系统 MUST 根据 `outline.chapters` 列表动态生成循环
- **AND** 每次循环 MUST 更新状态中的当前章节编号
- **AND** 所有章节完成后 MUST 路由到工作流结束节点

### Requirement: 向后兼容的 Orchestrator 接口
系统 MUST 保留 `NovelOrchestrator` 类作为 LangGraph 工作流的 facade，确保现有代码无破坏性变更。

#### Scenario: 内部委托给 LangGraph 工作流
- **WHEN** 初始化 `NovelOrchestrator` 时
- **THEN** 系统 MUST 内部创建 LangGraph 工作流实例
- **AND** 原有的 `step1_create_world()` 等方法 MUST 改为调用工作流的对应节点
- **AND** 方法签名和返回值格式 MUST 保持不变

#### Scenario: 支持原有 force 参数语义
- **WHEN** 调用 `stepX` 方法并传入 `force=False` 时
- **THEN** 系统 MUST 先检查对应的 JSON 文件是否存在
- **AND** 如果存在且可解析，MUST 跳过节点执行并返回已有结果
- **AND** 如果 `force=True`，MUST 执行节点并覆盖现有结果

#### Scenario: 新增工作流完整执行方法
- **WHEN** 用户调用 `NovelOrchestrator.run_workflow()` 时
- **THEN** 系统 MUST 执行完整的 LangGraph 工作流（从 START 到 END）
- **AND** MUST 返回最终的 `NovelGenerationState`
- **AND** SHOULD 支持传入 `start_from_step` 参数以跳过前序步骤

#### Scenario: 新增检查点恢复方法
- **WHEN** 用户调用 `NovelOrchestrator.resume_workflow(checkpoint_id)` 时
- **THEN** 系统 MUST 从指定检查点恢复工作流执行
- **AND** MUST 返回恢复后的执行结果
- **AND** 如果检查点不存在，MUST 抛出 ValueError

### Requirement: 状态与 JSON 文件双向同步
系统 MUST 确保 LangGraph 状态与现有 JSON 持久化文件格式的双向同步，保持数据一致性。

#### Scenario: 节点执行后保存 JSON
- **WHEN** 任意生成节点执行完成时
- **THEN** 系统 MUST 将结果保存到对应的 JSON 文件（如 `world.json`, `characters.json`）
- **AND** JSON 文件格式 MUST 与现有格式完全兼容
- **AND** 文件路径 MUST 遵循项目约定（`projects/{project_name}/`）

#### Scenario: 节点执行前加载 JSON
- **WHEN** 节点执行前且 `force=False` 时
- **THEN** 系统 MUST 尝试从对应 JSON 文件加载已有结果
- **AND** 如果加载成功，MUST 将结果填充到状态中并跳过节点执行
- **AND** 如果加载失败（文件不存在或格式错误），MUST 执行节点生成新结果

#### Scenario: 状态导出为 JSON
- **WHEN** 调用 `state_to_json(state, output_dir)` 工具函数时
- **THEN** 系统 MUST 将 `NovelGenerationState` 中的所有生成结果导出为 JSON 文件
- **AND** MUST 按现有文件命名约定保存（`world.json`, `characters.json` 等）
- **AND** 章节数据 MUST 保存为 `chapters/chapter_XXX.json`

#### Scenario: JSON 导入为状态
- **WHEN** 调用 `json_to_state(project_dir)` 工具函数时
- **THEN** 系统 MUST 从项目目录加载所有 JSON 文件
- **AND** MUST 解析为对应的 Pydantic 模型并填充到 `NovelGenerationState`
- **AND** 缺失的文件 MUST 对应状态字段保持为 None

### Requirement: 工作流可视化
系统 MUST 提供工作流图的可视化能力，帮助开发者和用户理解生成流程结构。

#### Scenario: 导出工作流图为图片
- **WHEN** 调用工作流的 `.draw()` 方法时
- **THEN** 系统 MUST 生成工作流的可视化图（PNG 或 SVG 格式）
- **AND** 图中 MUST 显示所有节点和边
- **AND** 条件边 MUST 标注判断逻辑或条件

#### Scenario: 导出工作流图为 Mermaid
- **WHEN** 调用 `export_workflow_mermaid(workflow)` 工具函数时
- **THEN** 系统 MUST 生成 Mermaid 格式的工作流图定义
- **AND** 图定义 MUST 可直接嵌入 Markdown 文档
- **AND** MUST 包含节点、边、条件判断的完整信息

#### Scenario: 工作流图包含在文档中
- **WHEN** 更新项目文档时
- **THEN** README.md 或迁移文档 MUST 包含工作流可视化图
- **AND** 图 MUST 展示完整的 6 步生成流程和分支逻辑
- **AND** SHOULD 添加图例说明节点类型和边的含义
