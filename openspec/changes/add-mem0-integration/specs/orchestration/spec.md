# Orchestration Spec Delta

## MODIFIED Requirements

### Requirement: Consistency Detection and Revision Trigger
编排器在章节生成后 MUST 执行一致性检测，并根据检测结果中是否有修复建议（`fix_instructions`）触发修订流程。

**注意**：修订过程不记录用户偏好，因为基于一致性检测的修订是针对具体章节/场景与计划的一致性校验，不应作为作者的长期写作偏好。

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

### Requirement: Apply manual-confirmed revision
当用户确认修订时，系统 MUST 应用修订候选并更新相关状态。

#### Scenario: Apply manual-confirmed revision
- **WHEN** 调用显式的「应用修订」操作（例如 CLI 命令或 runtime 函数）针对某一章
- **THEN** 系统 MUST：
  - 读取修订状态文件中的修订候选 GeneratedChapter
  - 直接使用该 GeneratedChapter 覆盖写回 `chapter_XXX.json`
  - 更新修订状态为 "accepted"，并记录确认时间
- **AND** 系统 SHOULD 触发或指导调用方重建该章的章节记忆

## ADDED Requirements

### Requirement: Inject User Preferences into Scene Generation
编排器在场景生成前 MUST 检索 Mem0 中的用户偏好，并将其注入到生成 Prompt 中。

**注意**：此功能为预留框架，配合 User Preference Storage 功能使用。当用户通过其他方式（如主动设置、UI 交互）添加偏好后，场景生成将自动参考这些偏好。

#### Scenario: Retrieve and inject user preferences
- **WHEN** 调用 `step6_generate_chapter_text()` 生成章节
- **AND** 进入场景生成循环（`generate_scene_text()`）
- **AND** Mem0 已启用且可用
- **THEN** 系统 MUST 从 Mem0 检索用户偏好（使用 `user_id="author_{project_name}"`）
- **AND** 将检索到的偏好格式化为 Prompt 的 `{user_preferences}` 部分
- **AND** 如果检索失败或无偏好，将 `{user_preferences}` 设为空字符串

#### Scenario: Fallback when Mem0 unavailable
- **WHEN** Mem0 未启用或不可用
- **THEN** 系统 MUST 将 `{user_preferences}` 设为空字符串
- **AND** 场景生成流程应正常继续（不因缺失 Mem0 而中断）

### Requirement: Update Entity States to Mem0 After Chapter Generation
编排器在章节生成完成后 MUST 将角色状态更新写入 Mem0 Agent Memory。

#### Scenario: Update entity states after chapter generation
- **WHEN** 完成章节生成（`step6_generate_chapter_text()`）
- **AND** Mem0 已启用且可用
- **THEN** 系统 MUST 识别章节中出现的主要角色（通过场景计划的 `characters` 字段）
- **AND** 为每个角色更新 Mem0 Agent Memory（使用 `agent_id="{project_id}_{character_name}"`）
- **AND** 更新内容应包含：章节编号、场景编号、角色在本章的行为摘要
- **AND** 如果 Mem0 写入失败，记录警告日志但不中断流程

#### Scenario: Dual-write entity states to SQLite
- **WHEN** 向 Mem0 写入实体状态
- **THEN** 系统 MUST 同时写入 SQLite 的 `entity_snapshots` 表（保持双写策略）
- **AND** 如果 Mem0 写入失败而 SQLite 写入成功，记录警告日志
- **AND** 如果两者都失败，记录错误日志

### Requirement: Initialize Entity States to Mem0 During Character Creation
编排器在角色创建步骤（`step3_create_characters()`）完成后 MUST 为每个主要角色初始化 Mem0 Agent Memory。

#### Scenario: Initialize agent memory for characters
- **WHEN** 执行 `step3_create_characters()` 完成
- **AND** Mem0 已启用且可用
- **THEN** 系统 MUST 为主角（protagonist）、反派（antagonist，如有）、配角（supporting_characters）初始化 Mem0 Agent Memory
- **AND** 使用 `agent_id="{project_id}_{character_name}"` 作为唯一标识
- **AND** 初始状态应包含角色的基础属性：姓名、角色定位、外貌、性格、背景、动机
- **AND** 如果 Mem0 初始化失败，记录警告日志但不中断流程

#### Scenario: Skip initialization when Mem0 disabled
- **WHEN** Mem0 未启用或不可用
- **THEN** 系统 MUST 跳过 Mem0 初始化
- **AND** 仅执行现有的 SQLite 实体快照保存逻辑

