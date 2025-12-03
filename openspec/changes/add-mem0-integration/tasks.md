# Implementation Tasks

## 1. Mem0 基础设施搭建
- [x] 1.1 添加 `mem0ai` 依赖到 `pyproject.toml` 和 `requirements.txt`
- [x] 1.2 创建 `novelgen/runtime/mem0_manager.py` 模块
- [x] 1.3 在 `novelgen/models.py` 中添加 `Mem0Config` 数据模型
- [x] 1.4 在 `novelgen/config.py` 中添加 Mem0 配置加载逻辑
- [x] 1.5 编写 Mem0 客户端初始化逻辑（复用现有 ChromaDB，使用独立 collection）
- [x] 1.6 验证 Mem0 与 ChromaDB 的兼容性（测试基本的 add/search/get_all 操作）
- [x] 1.7 编写 Mem0 健康检查方法（`mem0_manager.health_check()`）

## 2. 阶段一：用户记忆（User Memory）实现
- [x] 2.1 在 `mem0_manager.py` 中实现 `add_user_preference()` 方法
- [x] 2.2 在 `mem0_manager.py` 中实现 `search_user_preferences()` 方法
- [x] 2.3 ~~修改 `orchestrator.py` 的 `_handle_revision_stage()` 方法，在修订后记录用户偏好~~ → **[已变更]** 保留用户偏好功能框架，但不从修订过程中提取（修订是针对具体章节的一致性校验）
- [x] 2.4 修改 `orchestrator.py` 在场景生成前注入用户偏好到 `chapter_context`
- [x] 2.5 在 `generate_scene_text()` 调用时传递增强的 `chapter_context`
- [ ] 2.6 编写单元测试：`tests/test_mem0_user_memory.py`
- [ ] 2.7 编写集成测试：验证用户偏好在跨章节生成中的持久性

## 3. 阶段二：实体记忆（Entity Memory）实现
- [x] 3.1 在 `mem0_manager.py` 中实现 `add_entity_state()` 方法（使用 Agent Memory）
- [x] 3.2 在 `mem0_manager.py` 中实现 `get_entity_state()` 方法（检索最新状态）
- [x] 3.3 修改 `orchestrator.py` 在场景生成前从 Mem0 检索实体状态并补充到 `scene_memory_context`
- [x] 3.4 在 `orchestrator.py` 的章节生成后更新角色状态到 Mem0（从 `chapter_memory_entry` 提取）
- [x] 3.5 实现降级逻辑：Mem0 查询失败时回退到 SQLite
- [x] 3.6 在 `orchestrator.py` 的 `step3_create_characters()` 中，角色创建后初始化 Mem0 Agent Memory
- [ ] 3.7 编写单元测试：`tests/test_mem0_entity_memory.py`
- [ ] 3.8 编写集成测试：验证角色状态在多章节中的动态更新和一致性

## 4. 配置与文档
- [x] 4.1 在 `.env.template` 中添加 Mem0 配置项示例（仅需 `MEM0_ENABLED=true` 开关）
- [x] 4.2 更新 `README.md`，添加 Mem0 安装和配置说明（强调零部署特性）
- [x] 4.3 创建 `docs/mem0-setup.md`，说明如何启用 Mem0 和 ChromaDB 复用机制
- [x] 4.4 创建 `docs/mem0-migration.md`，说明如何从纯 SQLite 迁移到 Mem0 增强模式
- [x] 4.5 在 `CHANGELOG.md` 中记录 Mem0 集成的变更

## 5. 工具脚本
- [x] 5.1 创建 `scripts/check_mem0_health.py` - 检查 Mem0 连接状态和数据统计
- [x] 5.2 创建 `scripts/export_mem0_to_json.py` - 导出 Mem0 记忆到 JSON 备份
- [x] 5.3 创建 `scripts/clear_mem0_memory.py` - 清理指定项目的 Mem0 记忆（用于测试）

## 6. 测试与验证
- [ ] 6.1 运行所有单元测试，确保无回归
- [ ] 6.2 创建新项目 `demo_mem0_test`，验证完整的 Mem0 工作流
- [ ] 6.3 ~~验证用户偏好学习：手动修订几次，检查后续生成是否反映偏好~~ → **[已变更]** 验证用户偏好功能框架可用（通过 API 主动设置偏好并检查是否注入到生成 Prompt）
- [ ] 6.4 验证实体状态一致性：生成多章节，检查角色状态是否正确演化
- [ ] 6.5 验证降级机制：禁用 Mem0，确认系统回退到 SQLite
- [ ] 6.6 性能测试：对比启用/禁用 Mem0 时的生成速度差异

