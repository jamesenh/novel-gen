## 1. 数据模型设计
- [x] 1.1 在models.py中添加EntityStateSnapshot模型
- [x] 1.2 在models.py中添加StoryMemoryChunk模型
- [x] 1.3 在models.py中添加SceneMemoryContext模型
- [x] 1.4 验证新模型与现有模型的兼容性（通过 runtime/db、runtime/vector_store 以及相关单元测试间接验证）

## 2. 数据库抽象层实现
- [x] 2.1 创建runtime/db.py，定义数据库抽象接口
- [x] 2.2 实现SQLite基础数据库操作（包括迁移表结构 entity_snapshots / memory_chunks）
- [x] 2.3 创建数据库初始化和迁移脚本（novelgen/runtime/db_migrations.py）
- [x] 2.4 编写数据库操作的单元测试（novelgen/runtime/test_db.py）

## 3. 向量存储抽象层实现
- [x] 3.1 创建runtime/vector_store.py，定义向量存储抽象接口
- [x] 3.2 实现Chroma向量存储基础操作（在未安装 chromadb 时自动降级）
- [x] 3.3 实现文本分块和向量化逻辑（TextChunker + VectorStoreManager.add_scene_content）
- [x] 3.4 编写向量存储操作的单元测试（novelgen/runtime/test_vector_store.py）

## 4. Orchestrator集成
- [x] 4.1 修改runtime/orchestrator.py，添加数据库保存钩子
- [x] 4.2 在每个链执行后保存状态快照（step1-6 调用 _save_entity_snapshot）
- [x] 4.3 在场景生成后保存文本分块到向量库（step6 调用 _save_scene_content_to_vector）
- [x] 4.4 确保现有生成流程不受影响（通过 DatabaseManager / VectorStoreManager 降级逻辑和集成测试验证）

## 5. 验证和测试
- [x] 5.1 端到端测试：完整生成流程验证数据正确存储（novelgen/runtime/test_orchestrator_integration.py）
- [x] 5.2 性能测试：确保持久化不显著影响生成速度（新增脚本 novelgen/runtime/persistence_benchmark.py，作为手动基准工具，不在CI中强制运行）
- [x] 5.3 数据一致性测试：验证状态快照的准确性（见 test_db.py 与 orchestrator 集成测试中的快照断言）
- [x] 5.4 创建示例项目展示持久化功能（通过 docs/persistence_demo.md 提供使用说明和示例命令）
