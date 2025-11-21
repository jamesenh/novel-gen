## 1. 数据查询接口实现
- [x] 1.1 完善数据库查询层接口
  - [x] 1.1.1 在DatabaseInterface中添加get_latest_entity_state抽象方法
  - [x] 1.1.2 在DatabaseInterface中添加get_entity_timeline抽象方法
  - [x] 1.1.3 在DatabaseInterface中添加get_timeline_around抽象方法
  - [x] 1.1.4 在SQLiteDatabase中实现上述所有查询方法
  - [x] 1.1.5 在DatabaseManager中添加对应的包装方法
  - [x] 1.1.6 编写单元测试验证查询方法的正确性

- [x] 1.2 完善向量库查询层接口
  - [x] 1.2.1 在VectorStoreInterface中添加search_memory_with_filters抽象方法
  - [x] 1.2.2 在VectorStoreInterface中添加get_chunks_by_entities抽象方法
  - [x] 1.2.3 在ChromaVectorStore中实现上述所有查询方法
  - [x] 1.2.4 在VectorStoreManager中添加对应的包装方法
  - [x] 1.2.5 编写单元测试验证向量查询方法的正确性

- [x] 1.3 添加健康检查接口
  - [x] 1.3.1 在DatabaseManager中实现health_check方法（已存在）
  - [x] 1.3.2 在VectorStoreManager中实现health_check方法（已存在）
  - [x] 1.3.3 测试健康检查在正常和异常情况下的行为
 
## 2. 基础CLI工具实现
- [x] 2.1 创建基础脚本结构
  - [x] 2.1.1 创建`scripts`目录结构（如尚未存在）
  - [x] 2.1.2 为数据查询脚本添加统一的入口（如`novelgen-cli`或单文件脚本）

- [x] 2.2 实现实体状态查询命令
  - [x] 2.2.1 设计`query-entity`命令接口（接收project_id和entity_id）
  - [x] 2.2.2 调用`DatabaseManager.get_latest_entity_state`获取最新EntityStateSnapshot
  - [x] 2.2.3 以易读的表格或结构化文本形式输出关键字段

- [x] 2.3 实现场景记忆查询命令
  - [x] 2.3.1 设计`query-scene-memory`命令接口（接收project_id、chapter_index、scene_index以及可选limit）
  - [x] 2.3.2 调用向量查询接口获取相关记忆块列表
  - [x] 2.3.3 输出每个记忆块的text、entities、tags等关键信息

- [x] 2.4 为CLI添加基础文档和示例
  - [x] 2.4.1 在README或单独文档中添加命令使用说明
  - [x] 2.4.2 提供1-2个典型调用示例
  - [x] 2.4.3 添加基础错误处理和提示信息

## 3. 轻量测试与验证
- [x] 3.1 查询接口回归测试
  - [x] 3.1.1 在现有测试项目上验证数据库查询接口行为
  - [x] 3.1.2 在现有测试项目上验证向量查询接口行为

- [ ] 3.2 CLI 手动验证
  - [ ] 3.2.1 使用`query-entity`命令检查一两个典型角色在不同场景下的状态
  - [ ] 3.2.2 使用`query-scene-memory`命令检查某个场景相关记忆是否符合预期

