## ADDED Requirements

### Requirement: 基础数据检查CLI
系统MUST提供基础的命令行工具，用于查询数据库和向量存储中的关键状态信息，以便人工验证数据设计和查询接口的正确性。

#### Scenario: 查询实体当前状态
- **WHEN** 用户在命令行中提供project_id和entity_id
- **THEN** 系统必须通过数据库查询接口获取该实体最新的EntityStateSnapshot
- **AND** 必须以内嵌或表格形式输出关键字段，便于人工检查

#### Scenario: 查询场景相关记忆块
- **WHEN** 用户在命令行中提供project_id、chapter_index和scene_index
- **THEN** 系统必须通过向量存储查询接口获取与该场景相关的记忆块列表
- **AND** 必须输出每个记忆块的text、entities和tags等关键信息
- **AND** 必须支持限制返回数量以控制输出长度

