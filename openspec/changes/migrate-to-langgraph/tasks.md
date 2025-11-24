# Implementation Tasks

## 1. 依赖与基础设施
- [x] 1.1 在 `pyproject.toml` 中添加 `langgraph>=0.2.0` 依赖
- [x] 1.2 更新 `requirements.txt`（运行 `uv pip compile pyproject.toml`）
- [x] 1.3 验证 langgraph 安装成功（`python -c "import langgraph; print(langgraph.__version__)"`）

## 2. 状态模型定义
- [x] 2.1 在 `novelgen/models.py` 中定义 `NovelGenerationState` Pydantic 模型
- [x] 2.2 包含所有必需字段：项目信息、6步结果、记忆、工作流控制
- [x] 2.3 添加状态模型的单元测试（验证序列化/反序列化）

## 3. 节点包装器实现
- [x] 3.1 创建 `novelgen/runtime/nodes.py` 模块
- [x] 3.2 实现 `load_settings_node` - 加载项目配置到状态
- [x] 3.3 实现 `world_creation_node` - 包装 `generate_world` chain
- [x] 3.4 实现 `theme_conflict_creation_node` - 包装 `generate_theme_conflict` chain
- [x] 3.5 实现 `character_creation_node` - 包装 `generate_characters` chain
- [x] 3.6 实现 `outline_creation_node` - 包装 `generate_outline` chain
- [x] 3.7 实现 `chapter_planning_node` - 包装 `generate_chapter_plan` chain（支持批量/单章）
- [x] 3.8 实现 `chapter_generation_node` - 包装 `generate_scene_text` chain（支持批量/单章）
- [x] 3.9 实现 `consistency_check_node` - 包装一致性检测逻辑
- [x] 3.10 实现 `chapter_revision_node` - 包装章节修订 chain

## 4. 工作流图定义
- [x] 4.1 创建 `novelgen/runtime/workflow.py` 模块
- [x] 4.2 定义 `create_novel_generation_workflow()` 函数，返回编译后的 StateGraph
- [x] 4.3 添加 6 步生成的线性节点序列
- [x] 4.4 实现章节循环逻辑（基于 outline.chapters 列表）
- [x] 4.5 添加一致性检测后的条件分支（`should_revise_chapter` 判断函数）
- [x] 4.6 配置 `MemorySaver` 作为 checkpointer
- [x] 4.7 添加工作流可视化导出（`.draw()` 方法或 Mermaid 图）

## 5. Orchestrator 重构
- [x] 5.1 重构 `NovelOrchestrator.__init__`，内部初始化 LangGraph 工作流
- [x] 5.2 将 `step1_create_world` 等方法改为调用工作流的对应节点（保留原有方法）
- [x] 5.3 保持原有方法签名和返回值格式（向后兼容）
- [x] 5.4 添加 `run_workflow()` 方法，支持完整流程执行
- [x] 5.5 添加 `resume_workflow(checkpoint_id)` 方法，支持从检查点恢复

## 6. 持久化集成
- [x] 6.1 确保 LangGraph 状态与现有 JSON 文件双向同步
- [x] 6.2 在节点执行后保存结果到 JSON（保持现有文件格式）
- [x] 6.3 在节点执行前从 JSON 加载已有结果（支持 force 参数跳过）
- [x] 6.4 实现状态到 JSON 的导出工具（`state_to_json_files()`）
- [x] 6.5 实现 JSON 到状态的导入工具（`json_files_to_state()`）

## 7. 测试
- [x] 7.1 为 `NovelGenerationState` 编写单元测试
- [ ] 7.2 为每个节点包装器编写单元测试（mock chain 调用）
- [x] 7.3 为工作流图编写集成测试（使用 demo 项目）
- [x] 7.4 测试 checkpointing 功能（暂停后恢复）
- [x] 7.5 测试向后兼容性（现有 `NovelOrchestrator` API 仍可用）
- [ ] 7.6 测试条件分支逻辑（一致性检测 → 修订）

## 8. 文档与示例
- [ ] 8.1 更新 `README.md`，添加 LangGraph 使用说明
- [x] 8.2 创建 `docs/langgraph-migration.md` 迁移指南
- [ ] 8.3 更新 `main.py`，添加 LangGraph 工作流示例
- [x] 8.4 添加工作流图可视化到文档（PNG 或 Mermaid 图）
- [x] 8.5 创建 `examples/resume_workflow.py` 演示检查点恢复

## 9. 清理与优化
- [x] 9.1 移除或重命名旧的编排逻辑（如果完全替换）- 保留向后兼容
- [x] 9.2 检查并删除未使用的导入和死代码 - 代码库整洁
- [ ] 9.3 运行 linting 和格式化（`ruff check`, `black`）- 可选
- [x] 9.4 更新 `.windsurf/rules/base.md` 反映 LangGraph 架构 - 已反映

## 10. 验证与部署
- [x] 10.1 运行完整生成流程验证（demo_001 项目）- 端到端测试通过
- [x] 10.2 验证检查点功能（中断后恢复）- Checkpointing 测试通过
- [x] 10.3 验证向后兼容性（现有代码仍可用）- 兼容性测试通过
- [x] 10.4 性能基准测试（对比迁移前后）- 轻量级开销验证
- [x] 10.5 更新 CHANGELOG.md，记录架构变更
