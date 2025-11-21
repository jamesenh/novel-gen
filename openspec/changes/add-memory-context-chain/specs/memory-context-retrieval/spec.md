# memory-context-retrieval Specification Delta

## ADDED Requirements

### Requirement: Intelligent Memory Retrieval Chain
系统MUST提供独立的记忆上下文检索链，根据场景计划智能检索相关的历史记忆和实体状态。

#### Scenario: Analyze scene and retrieve relevant memories
- **WHEN** 提供ScenePlan（包含场景类型、地点、出场角色、关键动作）
- **THEN** 链应使用LLM分析场景需求，识别需要查询的实体
- **AND** 生成合适的向量检索查询关键词
- **AND** 调用向量存储搜索相关的历史记忆块

#### Scenario: Retrieve entity states
- **WHEN** 场景计划中包含特定角色
- **THEN** 链应查询这些角色的最新状态快照
- **AND** 状态信息包含在输出的SceneMemoryContext中

#### Scenario: Output structured context
- **WHEN** 记忆检索完成
- **THEN** 链MUST输出SceneMemoryContext Pydantic对象
- **AND** 对象MUST包含project_id、chapter_index、scene_index、entity_states、relevant_memories、retrieval_timestamp字段
- **AND** 对象MAY包含timeline_context字段，用于聚合时间线上下文信息
- **AND** 输出MUST写入JSON文件：`projects/<id>/scene_<chapter>_<scene>_memory.json`

### Requirement: Memory Tools Abstraction Layer
系统MUST提供封装良好的工具函数层，简化记忆检索操作。

#### Scenario: Search story memory with filters
- **WHEN** 调用search_story_memory_tool()函数
- **THEN** 函数应接受project_id（项目ID）、query（查询关键词）、entities（实体过滤）、content_type（内容类型）、tags（标签）、top_k（返回数量）参数
- **AND** 当未显式提供top_k时，系统MUST使用合理的默认值（例如10）
- **AND** 函数返回List[StoryMemoryChunk]对象列表

#### Scenario: Get entity state by ID
- **WHEN** 调用get_entity_state_tool()函数
- **THEN** 函数应接受project_id、entity_id、可选的chapter_index和scene_index参数
- **AND** 返回EntityStateSnapshot或None

#### Scenario: Get recent timeline context
- **WHEN** 调用get_recent_timeline_tool()函数
- **THEN** 函数应接受project_id、chapter_index、context_window参数
- **AND** 返回List[EntityStateSnapshot]，包含指定章节前后的实体状态快照

### Requirement: Graceful Degradation
记忆检索失败MUST NOT阻塞主生成流程。

#### Scenario: Vector store unavailable
- **WHEN** 向量存储不可用或检索失败
- **THEN** relevant_memories字段返回空列表
- **AND** 记录警告日志但继续执行
- **AND** 链正常完成并输出SceneMemoryContext

#### Scenario: Database query failure
- **WHEN** 数据库查询失败
- **THEN** entity_states字段返回空列表
- **AND** 记录警告日志但继续执行
- **AND** 链正常完成并输出SceneMemoryContext

#### Scenario: JSON write failure
- **WHEN** JSON文件写入失败
- **THEN** 记录错误日志
- **AND** 不抛出异常，允许orchestrator继续后续步骤

#### Scenario: Partial capability implementation
- **WHEN** 实现阶段仅启用search_story_memory_tool而尚未接入实体状态或时间线工具
- **THEN** 链MUST仍然成功执行并输出有效的SceneMemoryContext对象
- **AND** entity_states字段MAY为空列表，timeline_context字段MAY为null
- **AND** relevant_memories字段MUST基于向量检索结果正确填充

### Requirement: Chain Independence and Testability
记忆上下文检索链MUST保持独立性，支持单独运行和测试。

#### Scenario: Run chain independently
- **WHEN** 提供必需的输入参数（ScenePlan、CharactersConfig、project_id、chapter_index、scene_index）
- **THEN** 链应能够独立执行，不依赖orchestrator
- **AND** 输出完整的SceneMemoryContext对象

#### Scenario: Orchestrator integration with optional context
- **WHEN** orchestrator在调用链时额外提供Settings或ChapterPlan中的部分信息
- **THEN** 链MAY在Prompt中使用这些额外上下文
- **AND** 这些可选输入MUST NOT成为链运行的硬性前置条件

#### Scenario: Test with mock data
- **WHEN** 使用测试数据库和向量存储
- **THEN** 链应正常工作
- **AND** 测试应验证检索逻辑和输出格式

#### Scenario: Follow project conventions
- **WHEN** 实现链代码
- **THEN** MUST遵循项目规范：
  - 链保持无状态
  - 通过Pydantic模型定义输入输出
  - 通过JSON文件传递信息
  - 不在LangChain中嵌入业务逻辑
  - 使用PydanticOutputParser确保结构化输出
