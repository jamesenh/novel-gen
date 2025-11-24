# Migrate to LangGraph

## Why

当前项目使用简单的顺序编排（`NovelOrchestrator`）管理 6 步小说生成流程。随着 MVP 验证完成和功能增长，我们面临以下挑战：

1. **长期记忆能力不足**：现有编排器无法在多步骤之间有效管理和传递上下文记忆，导致后续章节难以引用前文细节
2. **可恢复性差**：生成过程一旦中断，无法从中间状态恢复，只能重新开始或手动管理检查点
3. **扩展性受限**：顺序执行架构难以支持条件分支、并行生成、动态路由等复杂工作流需求
4. **状态管理分散**：记忆、向量存储、数据库等状态分散在多个管理器中，缺乏统一的状态抽象

LangGraph 是 LangChain 生态中专为复杂 AI 工作流设计的状态图框架，提供：
- **Stateful workflow**：通过 `StateGraph` 管理跨节点的状态传递
- **Checkpointing**：内置检查点机制，支持暂停/恢复
- **灵活路由**：支持条件边、并行节点、子图嵌套
- **持久化集成**：与 LangChain 的持久化层无缝集成

将编排逻辑迁移到 LangGraph 是解决上述问题并为未来功能扩展奠定基础的架构升级。

## What Changes

- **新增 LangGraph 依赖**：在 `pyproject.toml` 中添加 `langgraph>=0.2.0`
- **创建 LangGraph 状态模型**：在 `models.py` 中定义 `NovelGenerationState`，统一管理工作流状态
- **实现 LangGraph 工作流**：创建 `novelgen/runtime/workflow.py`，用 `StateGraph` 定义 6 步生成流程
- **节点适配器层**：为现有 chains 创建 LangGraph 节点包装器
- **Checkpointing 配置**：集成 LangGraph 的检查点机制，支持工作流暂停/恢复
- **向后兼容**：保留 `NovelOrchestrator` 作为简化接口，内部委托给 LangGraph 工作流
- **迁移路径文档**：提供现有项目迁移指南

**BREAKING 变更**：
- 无直接破坏性变更，但建议新项目优先使用 LangGraph 工作流 API

## Impact

### 受影响的 specs
- **orchestration**：核心变更，添加 LangGraph 工作流能力

### 受影响的代码
- `novelgen/models.py`：添加 `NovelGenerationState` 状态模型
- `novelgen/runtime/workflow.py`：**新增**，LangGraph 工作流定义
- `novelgen/runtime/orchestrator.py`：重构为 LangGraph 工作流的包装器
- `novelgen/chains/*.py`：添加节点适配器（可选包装层）
- `pyproject.toml`：添加 langgraph 依赖
- `main.py`：更新演示代码以展示 LangGraph 用法

### 用户影响
- **现有项目**：无需立即迁移，`NovelOrchestrator` API 保持兼容
- **新项目**：可直接使用 LangGraph 工作流 API，获得状态管理和恢复能力
- **开发者**：学习成本增加，需了解 LangGraph 基本概念（StateGraph、节点、边）
