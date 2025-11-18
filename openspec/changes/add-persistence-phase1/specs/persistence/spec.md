## ADDED Requirements

### Requirement: 数据持久化基础设施
系统MUST提供数据库和向量存储的持久化能力，用于存储生成过程中的状态快照和文本记忆。

#### Scenario: 数据库初始化
- **WHEN** 系统首次启动或检测到新项目
- **THEN** 系统必须自动创建SQLite数据库和必要的表结构
- **AND** 必须创建Chroma向量存储集合
- **AND** 必须验证存储连接的可用性

#### Scenario: 状态快照保存
- **WHEN** 任何生成链执行完成并输出Pydantic模型
- **THEN** 系统必须将输出序列化为JSON并保存到数据库
- **AND** 必须记录项目ID、链类型、执行时间戳等元数据
- **AND** 必须确保数据完整性和一致性

#### Scenario: 文本内容向量化
- **WHEN** 场景文本生成完成
- **THEN** 系统必须将GeneratedScene.content分块为适合向量化的大小
- **AND** 必须为每个chunk生成向量嵌入并存储到向量库
- **AND** 必须记录chunk与项目、章节、场景的关联关系

#### Scenario: 存储抽象接口
- **WHEN** 运行时代码需要访问存储功能
- **THEN** 必须通过runtime/db.py和runtime/vector_store.py的抽象接口
- **AND** 接口必须与具体实现解耦，支持未来技术栈切换
- **AND** 必须提供统一的错误处理和降级机制

### Requirement: 数据模型扩展
系统MUST扩展现有的Pydantic模型以支持持久化需求。

#### Scenario: 实体状态快照模型
- **WHEN** 需要记录角色或物品在特定时间点的状态
- **THEN** 必须使用EntityStateSnapshot模型存储状态信息
- **AND** 必须包含项目ID、实体ID、章节场景索引、状态字典等字段
- **AND** 必须支持状态版本化和时间序列查询

#### Scenario: 记忆块存储模型
- **WHEN** 需要存储和检索文本记忆片段
- **THEN** 必须使用StoryMemoryChunk模型存储文本块信息
- **AND** 必须包含文本内容、实体关联、标签、嵌入ID等字段
- **AND** 必须支持按项目和场景范围的组织管理

#### Scenario: 记忆上下文聚合模型
- **WHEN** 需要将检索结果传递给生成链
- **THEN** 必须使用SceneMemoryContext模型聚合相关记忆
- **AND** 必须包含实体状态、近期记忆、时间线上下文等信息
- **AND** 必须保持与现有链输入接口的兼容性

### Requirement: 向后兼容性保证
系统MUST在不影响现有生成流程的前提下引入持久化功能。

#### Scenario: 降级模式运行
- **WHEN** 数据库或向量存储不可用
- **THEN** 系统必须自动降级到仅使用JSON文件的原始模式
- **AND** 必须记录警告日志但不中断生成流程
- **AND** 必须保持所有现有API和链接口不变

#### Scenario: 可选持久化配置
- **WHEN** 用户希望禁用持久化功能
- **THEN** 必须通过配置选项控制持久化的启用/禁用
- **AND** 禁用时系统行为必须与原始版本完全一致
- **AND** 必须支持运行时动态切换而不影响正在进行的生成任务
