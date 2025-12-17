## MODIFIED Requirements

### Requirement: Inject User Writing Preferences

Scene generation MUST consume user writing preferences from Mem0 to personalize output style on a per-project basis.

#### Scenario: Search and inject preferences

- **WHEN** 场景生成开始
- **THEN** 系统 MUST 从 Mem0 检索用户写作偏好（使用 `user_id="author_{project_id}"`，查询 "写作风格和偏好"，限制返回前 5 条）
- **AND** 将检索到的偏好以结构化格式注入到 prompt（建议附加到 `chapter_context` 或等效字段）
- **AND** 若检索失败或无偏好，系统 MUST 优雅降级（注入空字符串/空列表），且不应阻止生成流程

#### Scenario: Apply preferences to generation

- **WHEN** 用户偏好包含特定风格要求（如"多使用心理描写"、"避免过多对话"）
- **THEN** 生成的场景文本 MUST 反映这些偏好
- **AND** 偏好 MUST 不覆盖场景计划的核心约束（字数、场景目的、角色出场与关键动作）


