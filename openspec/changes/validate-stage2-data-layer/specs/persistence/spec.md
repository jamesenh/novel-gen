## ADDED Requirements

### Requirement: 数据查询接口扩展
系统MUST提供完整的数据库和向量存储查询接口，支持实体状态跟踪和记忆检索。

#### Scenario: 获取实体最新状态
- **WHEN** 需要查询特定实体在当前时间点的状态
- **THEN** 系统必须提供get_latest_entity_state方法
- **AND** 必须支持通过project_id和entity_id精确查询
- **AND** 必须返回最新的EntityStateSnapshot或None

#### Scenario: 获取实体时间线
- **WHEN** 需要查看实体的状态变化历史
- **THEN** 系统必须提供get_entity_timeline方法
- **AND** 必须支持按时间戳升序排列返回历史快照
- **AND** 必须支持limit参数控制返回数量

#### Scenario: 获取时间点周围事件
- **WHEN** 需要查看特定章节场景附近的实体状态
- **THEN** 系统必须提供get_timeline_around方法
- **AND** 必须支持通过chapter_index和scene_index定位
- **AND** 必须支持window参数控制查询范围

#### Scenario: 带过滤条件的记忆搜索
- **WHEN** 需要在向量存储中进行精确的记忆检索
- **THEN** 系统必须提供search_memory_with_filters方法
- **AND** 必须支持按实体ID、标签、内容类型过滤
- **AND** 必须支持limit参数控制返回数量

#### Scenario: 按实体获取记忆块
- **WHEN** 需要查询与特定实体相关的所有记忆
- **THEN** 系统必须提供get_chunks_by_entities方法
- **AND** 必须支持多个实体ID的批量查询
- **AND** 必须返回按相关性排序的记忆块列表

#### Scenario: 健康检查接口
- **WHEN** 需要验证数据库和向量存储的连接状态
- **THEN** 所有管理器必须提供health_check方法
- **AND** 必须返回布尔值表示连接状态
- **AND** 必须在连接失败时提供错误信息
