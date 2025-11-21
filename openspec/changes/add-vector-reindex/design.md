## Context
- 当前已有持久化 Phase1 能力：
  - 使用 SQLite 存储实体状态和记忆块（memory_chunks）
  - 使用 Chroma 向量库存储分块后的场景记忆
- 向量写入逻辑分散在：
  - runtime/vector_store.py（VectorStoreManager + ChromaVectorStore）
  - runtime/orchestrator.py（_save_scene_content_to_vector）
- 目前缺少统一的「重建向量索引」能力，导致：
  - 调整 chunk_size / overlap 或 embedding 配置后，旧项目无法方便地更新
  - 修复 embedding / Chroma 初始化问题后，需要手动删除目录和重跑生成流程

## Goals / Non-Goals
- Goals
  - 提供显式、可控的重建入口，支持项目级和章节级重建
  - 尽量复用现有持久化和分块逻辑，避免复制业务规则
  - 保证在重建过程中向量库与数据库状态一致（删旧写新）
- Non-Goals
  - 不改变正常生成流水线的行为（仅增加运维/工具能力）
  - 不引入新的持久化后端（仍然使用 SQLite + Chroma）
  - 不在本提案中设计自动重建或在线重建机制

## Decisions
- Decision: 重建入口放在 runtime 层，提供纯 Python 函数，CLI 作为薄包装
  - 便于脚本、工具和后续自动化复用
- Decision: 数据源优先级
  - 优先从数据库的 memory_chunks 表重建（如果存在且启用持久化）
  - 若 memory_chunks 不可用，可以退回从章节 JSON 文件重建（作为后备策略）
- Decision: 重建策略
  - 对目标范围（项目 / 章节）执行「先删后建」：
    - 先通过 VectorStoreManager / ChromaVectorStore 删除目标范围的向量
    - 再批量写入新向量，保持 embedding 配置与当前项目配置一致

## Risks / Trade-offs
- 风险：重建过程可能耗时较长
  - 缓解：通过 CLI 日志输出明显的进度信息，建议对大项目分章节重建
- 风险：错误的重建命令可能删除本应保留的向量
  - 缓解：
    - 明确区分项目级和章节级入口
    - 可选提供 dry-run 选项，仅统计将被影响的条目数量

## Migration Plan
- 新增 change `add-vector-reindex`，在 changes/ 下实现 proposal/specs/tasks/design
- 在后续实现阶段：
  - 添加 runtime 层的重建函数
  - 添加 CLI 脚本并更新文档
  - 在 demo 项目上验证行为

## Open Questions
- 是否需要支持更细粒度（例如按实体、按标签）重建？（当前不在本提案范围内）
- 是否需要在 UI / 上层工具中暴露重建入口？（当前项目主要通过 CLI 驱动，可后续提案再扩展）
