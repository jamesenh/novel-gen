## Why
当前系统已经具备将场景文本分块并写入 Chroma 向量库的能力，但缺少统一的「重建索引」机制。

在以下场景中，需要能够安全、可控地重建向量索引：
- 调整分块策略（chunk_size / overlap）后，希望让旧项目生效新策略
- 修复 embedding / Chroma 配置错误后，需要重新写入所有记忆块
- 清理脏数据或手动修改数据库记录后，需要重新同步向量库

目前只能通过手动删除向量目录或重新跑整本书生成流程，成本高且容易出错。

## What Changes
- 为持久化/向量存储能力新增「重建向量索引」的统一入口
- 支持两种重建粒度：
  - 整个项目：基于项目 ID，重建该项目下所有章节/场景的向量索引
  - 指定章节：基于项目 ID + 章节索引，只重建该章节的向量索引
- 入口形式可以是：
  - 一个 CLI 脚本（例如 scripts/reindex_vectors.py）
  - 或 runtime 层的 Python 函数接口（例如 runtime/db_or_vector_tools 中的函数），供脚本和后续工具复用
- 重建流程应复用现有的持久化能力：
  - 从 SQLite 的 memory_chunks（或章节 JSON）中读取源文本
  - 调用 VectorStoreManager / ChromaVectorStore 完成写入
  - 在重建前清理对应项目/章节的旧向量条目
- 提供最小可用的进度和结果反馈（标准输出日志或函数返回值），方便在脚本中查看重建进度。

## Impact
- 受影响的能力：
  - persistence：新增「重建向量索引」相关要求
  - orchestration / runtime：可能需要补充工具函数或脚本
- 受影响的代码：
  - novelgen/runtime/vector_store.py（复用或扩展 VectorStoreManager 能力）
  - novelgen/runtime/db.py（如果需要从数据库恢复记忆块）
  - novelgen/runtime/orchestrator.py（如需要复用已有的场景保存逻辑）
  - scripts/*（新增或扩展 CLI 命令）
- 行为变化：
  - 正常生成流程不变
  - 新增一个显式的「重建向量索引」通道，供开发者在参数调整或修复后主动调用
