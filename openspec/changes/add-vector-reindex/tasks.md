## 1. 设计与对齐
- [x] 1.1 明确重建向量索引的输入来源优先级（数据库 memory_chunks 表 vs 章节 JSON 文件）
- [x] 1.2 确定最小可行入口形态（CLI 脚本 + 可复用的 runtime 函数）
- [x] 1.3 与现有 persistence / orchestration 规格对齐，确认不改变主生成流程

## 2. 规格与接口
- [x] 2.1 在 persistence 能力下新增「重建向量索引」相关 ADDED Requirements
- [x] 2.2 定义项目级重建接口（例如：reindex_project_vectors(project_id, ...)）
- [x] 2.3 定义章节级重建接口（例如：reindex_chapter_vectors(project_id, chapter_index, ...)）

## 3. 实现
- [x] 3.1 在 runtime 层实现重建索引的核心函数：
  - [x] 3.1.1 加载项目配置和 embedding 配置
  - [x] 3.1.2 根据参数确定重建范围（项目 / 章节）
  - [x] 3.1.3 清理目标范围内的旧向量（复用 VectorStoreManager / ChromaVectorStore）
  - [x] 3.1.4 从数据库或章节 JSON 中读取源文本并重建 StoryMemoryChunk
  - [x] 3.1.5 调用 VectorStoreManager.add_scene_content 或等价逻辑写入向量库
- [x] 3.2 新增 CLI 脚本（如 scripts/reindex_vectors.py）：
  - [x] 3.2.1 支持按项目 ID 重建
  - [x] 3.2.2 支持按项目 ID + 章节索引重建
  - [x] 3.2.3 提供 dry-run / 进度输出

## 4. 验证
- [x] 4.1 在 demo 项目上手动执行项目级重建，确认：
  - [x] 4.1.1 旧向量被删除，新向量数量与章节/场景数量匹配
  - [x] 4.1.2 `scripts/query_scene_memory.py --search` 的语义检索结果符合预期
- [x] 4.2 在 demo 项目上手动执行章节级重建，确认：
  - [x] 4.2.1 仅目标章节的向量发生变化，其他章节不受影响
  - [x] 4.2.2 修订后章节的记忆检索效果与当前文本一致
- [x] 4.3 在持久化被禁用或向量库不可用的情况下运行重建命令，确认：
  - [x] 4.3.1 命令以明确错误或降级提示退出
  - [x] 4.3.2 不破坏现有数据库和项目文件

## 5. 文档与维护
- [x] 5.1 在 docs/ 或 README 中补充重建索引命令的使用说明和注意事项
- [x] 5.2 在 openspec 中记录该能力的使用场景和限制（例如重建成本、执行时间）
- [x] 5.3 通过 `openspec validate add-vector-reindex --strict` 确认变更通过校验
