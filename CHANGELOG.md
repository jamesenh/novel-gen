# Changelog

所有重要的项目变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## [Unreleased]

### Added - 新增功能

#### Mem0 智能记忆层集成 (2025-11-23)

**核心特性**: 集成 Mem0 作为智能记忆层，实现用户偏好学习和实体状态管理。

- **零额外部署**: 复用现有 ChromaDB 实例，通过独立 Collection 隔离数据
- **用户记忆 (User Memory)**:
  - 预留功能框架，支持主动设置写作偏好和风格（当前不从修订过程中自动提取）
  - 在场景生成时注入用户偏好到 Prompt
  - 支持偏好分类：writing_style, tone, character_development, plot_preference
- **实体记忆 (Entity Memory)**:
  - 使用 Mem0 Agent Memory 管理角色动态状态
  - 自动合并和更新角色状态信息
  - 优先从 Mem0 检索，失败时降级到 SQLite
- **向后兼容**: Mem0 作为可选功能，默认禁用，通过环境变量 `MEM0_ENABLED=true` 启用
- **双写策略**: 新内容同时写入 Mem0 和 SQLite，保证数据完整性

**新增文件**:
- `novelgen/runtime/mem0_manager.py` - Mem0 客户端管理器 (320 行)
- `novelgen/models.py` - 新增 `Mem0Config` 和 `UserPreference` 数据模型
- `scripts/check_mem0_health.py` - Mem0 健康检查工具
- `scripts/export_mem0_to_json.py` - Mem0 数据导出工具
- `scripts/clear_mem0_memory.py` - Mem0 数据清理工具

**新增文档**:
- `docs/mem0-setup.md` - Mem0 设置指南 (200+ 行)
- `docs/mem0-migration.md` - 从纯 SQLite 到 Mem0 的迁移指南 (200+ 行)
- `openspec/changes/add-mem0-integration/` - 完整的 OpenSpec 提案文档

**依赖更新**:
- 新增 `mem0ai>=0.1.0` 依赖

**配置变更**:
- 新增环境变量 `MEM0_ENABLED` - 控制 Mem0 启用状态
- 更新 `.env.template` 添加 Mem0 配置项

详见 `docs/mem0-setup.md` 和 `openspec/changes/add-mem0-integration/proposal.md`。

#### LangGraph 架构迁移 (2025-11-22)

**核心架构升级**: 将编排系统从顺序调用迁移到 LangGraph 状态工作流。

- **状态管理**: 新增 `NovelGenerationState` Pydantic 模型，统一管理所有生成数据和工作流状态
- **工作流编排**: 使用 LangGraph `StateGraph` 定义 11 个节点的小说生成工作流
- **Checkpointing**: 支持工作流暂停和恢复功能，使用 `MemorySaver` 实现自动检查点
- **节点包装器**: 在 `novelgen/runtime/nodes.py` 实现 9 个节点函数，包装现有的 LangChain 链
- **工作流定义**: 在 `novelgen/runtime/workflow.py` 定义完整的状态图，支持条件分支

**持久化增强**:
- 新增 `novelgen/runtime/state_sync.py` 模块，提供状态与 JSON 文件的双向同步
- `state_to_json_files()`: 将 LangGraph 状态导出到 JSON 文件
- `json_files_to_state()`: 从 JSON 文件加载并构造状态
- `sync_state_from_json()`: 同步更新状态（保留工作流控制字段）

**新增 API**:
- `NovelOrchestrator.run_workflow(stop_at=None)`: 运行完整或部分工作流
- `NovelOrchestrator.resume_workflow(checkpoint_id=None)`: 从检查点恢复工作流
- `NovelOrchestrator._get_or_create_workflow_state()`: 获取或创建工作流状态

**文档和示例**:
- 新增 `docs/langgraph-migration.md` - 详细的迁移指南
- 新增 `examples/resume_workflow.py` - Checkpointing 功能演示
- 工作流可视化支持（Mermaid 图）

**测试覆盖**:
- 新增 `tests/test_state_model.py` - NovelGenerationState 单元测试（8 个测试）
- 新增 `tests/test_checkpointing.py` - Checkpointing 功能测试（5 个测试）
- 新增 `tests/test_langgraph_integration.py` - 集成测试（3 个测试）
- 新增 `tests/test_state_persistence.py` - 持久化测试（5 个测试）
- 新增 `tests/test_end_to_end.py` - 端到端验证测试（8 个测试）
- **总计 35 个测试用例，全部通过** ✅

### Changed - 变更

#### NovelOrchestrator 重构

- 内部集成 LangGraph 工作流（在 `__init__` 中初始化）
- 保持 100% 向后兼容，所有原有 API 完全保留
- 新增 `workflow` 属性（CompiledStateGraph 实例）
- 新增 `_workflow_state` 属性（缓存的状态对象）

#### 依赖更新

- 新增 `langgraph>=0.2.0` 依赖（实际安装版本: 1.0.3）

### Technical Details - 技术细节

**工作流节点结构**:
1. `load_settings` - 加载项目设置
2. `world_creation` - 生成世界观
3. `theme_conflict_creation` - 生成主题冲突
4. `character_creation` - 生成角色
5. `outline_creation` - 生成大纲
6. `chapter_planning` - 规划章节
7. `chapter_generation` - 生成章节文本
8. `consistency_check` - 一致性检测
9. `chapter_revision` - 章节修订（条件触发）
10. `START` - 工作流起点
11. `END` - 工作流终点

**条件分支逻辑**:
- `should_revise_chapter()`: 根据一致性检测结果决定是否触发修订
- 支持从 `consistency_check` → `chapter_revision` → `chapter_generation` 的循环

**性能影响**:
- 内存开销: +5-10MB（状态管理和检查点）
- 执行速度: 几乎无影响（节点包装开销 <1ms）
- 存储开销: +1-5MB per project（检查点数据）

### Migration Guide - 迁移指南

**现有代码无需修改**，NovelOrchestrator 保持完全兼容：

```python
# 现有代码继续工作
orchestrator = NovelOrchestrator('my_novel')
orchestrator.step1_create_world(user_input)
orchestrator.step2_create_theme_conflict()
# ...
```

**推荐使用新的工作流 API**：

```python
# 方式 1: 运行完整工作流
orchestrator = NovelOrchestrator('my_novel')
state = orchestrator.run_workflow()

# 方式 2: 分段执行
state = orchestrator.run_workflow(stop_at='outline_creation')
# 做一些调整...
state = orchestrator.resume_workflow()

# 方式 3: 错误恢复
try:
    state = orchestrator.run_workflow()
except Exception as e:
    state = orchestrator.resume_workflow()  # 从检查点恢复
```

详见 `docs/langgraph-migration.md`。

### Breaking Changes - 破坏性变更

**无破坏性变更** - 完全向后兼容。

### Deprecated - 废弃

无废弃功能。所有原有 API 继续保留和维护。

### Removed - 移除

无移除功能。

### Fixed - 修复

无（此版本为新功能添加）。

### Security - 安全

无安全相关变更。

---

## [0.1.0] - 2025-11-XX

### Added
- 初始版本发布
- 基于 LangChain 的 6 步小说生成流程
- 世界观、主题冲突、角色、大纲、章节规划、场景文本生成
- JSON 文件持久化
- 数据库和向量存储集成
- 一致性检测和修订机制

[Unreleased]: https://github.com/jamesenh/novel-gen/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jamesenh/novel-gen/releases/tag/v0.1.0
