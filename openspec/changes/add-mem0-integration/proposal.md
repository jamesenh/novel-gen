# Add Mem0 Integration

## Why

当前项目使用 JSON 文件、SQLite 数据库和 ChromaDB 三种方式存储记忆数据，但存在以下问题：
1. **实体状态冗余与冲突**：SQLite 中的 `EntityStateSnapshot` 只是时间切片堆叠，无法自动合并或更新矛盾状态
2. **缺乏用户偏好学习**：系统无法记住作者的写作风格偏好和反馈意见，每次生成都是"失忆"的
3. **手动维护负担重**：需要手动决定何时存快照、何时更新向量，缺乏智能的记忆管理

引入 **Mem0** 可以提供智能的记忆层，通过自动去重、冲突解决和时间衰减机制，让 AI 系统具备"真正的记忆能力"。

## What Changes

### 阶段一：用户记忆（User Memory）
- 添加 Mem0 客户端管理模块 `mem0_manager.py`
- ~~在章节修订（`revision`）环节记录用户的修改意图和偏好~~ → **[已变更]** 保留用户偏好功能框架，但不从修订过程中提取（修订是针对具体章节的一致性校验，不应作为长期写作偏好）
- 在场景生成（`scene_text_chain`）时检索用户偏好并注入 Prompt

### 阶段二：实体记忆（Entity Memory）
- 使用 Mem0 替换 SQLite 的 `EntityStateSnapshot` 手动快照逻辑
- 为每个主要角色（Character）在 Mem0 中维护动态状态
- 在场景生成前，从 Mem0 检索角色的最新一致性状态，而不是从 SQLite 查询多条历史快照

## Impact

### Affected Specs
- `orchestration` - 修改章节修订和场景生成流程，集成 Mem0 检索
- 新增 `memory-management` spec - 定义 Mem0 集成的接口和行为

### Affected Code
- **新增文件**：
  - `novelgen/runtime/mem0_manager.py` - Mem0 客户端封装
  - `novelgen/models.py` - 新增 `Mem0Config` 和 `UserPreference` 模型
- **修改文件**：
  - `novelgen/config.py` - 添加 Mem0 配置选项
  - `novelgen/runtime/orchestrator.py` - 集成 Mem0 到修订和生成流程
  - `novelgen/chains/scene_text_chain.py` - 在 Prompt 中注入用户偏好
  - `novelgen/chains/memory_context_chain.py` - 使用 Mem0 检索实体状态

### Dependencies
- 新增 Python 依赖：`mem0ai`
- **无额外部署依赖**：复用项目现有的 ChromaDB 实例（零部署成本）

### Breaking Changes
- 无破坏性变更。Mem0 作为可选功能，通过配置开关控制（`config.mem0_enabled`）
- 现有的 SQLite 快照逻辑保留作为降级方案

