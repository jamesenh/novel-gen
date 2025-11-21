# 添加记忆上下文检索链提案

## Why
阶段1和阶段2已完成数据库和向量存储的基础设施建设及只读验证。当前场景生成链依赖静态的JSON文件传递上下文，无法动态检索历史记忆和实体状态。为了提升生成内容的连贯性和一致性，需要引入智能记忆检索机制，让LLM能够根据场景需求主动查找相关的历史片段和角色状态。

## What Changes
- **新增记忆上下文检索链**：创建`chains/memory_context_chain.py`，使用LLM分析场景计划并智能检索相关记忆
- **实现记忆工具函数**：在`runtime/memory_tools.py`中封装便捷的检索接口，供链调用
- **定义输出JSON格式**：生成的`SceneMemoryContext`对象写入`projects/<id>/scene_<chapter>_<scene>_memory.json`
- **保持链独立性**：链通过`DatabaseManager`和`VectorStoreManager`访问数据，不直接操作底层存储
- **支持降级处理**：当记忆检索失败时不影响主流程，降级到原有模式

## Impact
- **受影响的规范**：新增`memory-context-retrieval` capability规范
- **受影响的代码**：
  - 新增：`novelgen/chains/memory_context_chain.py`（~150-200行）
  - 新增：`novelgen/runtime/memory_tools.py`（~100行，可选）
  - 新增测试：`test_memory_context_chain.py`
- **非破坏性变更**：不修改现有链的行为，仅新增可选的记忆检索步骤
- **依赖关系**：依赖阶段1的持久化基础设施和阶段2的查询接口
- **后续集成**：为阶段4（scene_text_chain接入记忆上下文）做准备

## 与阶段3方案文档的关系

- 本变更落地的是《数据库与向量库渐进式落地方案》中阶段3提出的 `memory_context_chain` 能力，但在实施过程中对部分细节做了演化：
  - 以 `novelgen/models.py` 中的 `SceneMemoryContext` 为数据结构真源，规范中字段设计与该模型保持一致（包括 `retrieval_timestamp`、可选的 `timeline_context` 等）。
  - 将原方案中的 `get_entity_state` / `get_timeline` / `search_story_memory` 抽象更新为 `get_entity_state_tool` / `get_recent_timeline_tool` / `search_story_memory_tool`，接口参数与当前数据模型和过滤需求对齐（如 `project_id`、`top_k`、content_type、tags 等）。
  - 明确 `memory_context_chain` 的最小必需输入为 `ScenePlan`、`CharactersConfig`、`project_id`、`chapter_index`、`scene_index`，其它如 `Settings`、`ChapterPlan` 视为可选的 orchestrator 级集成输入。
  - 规范按“目标能力”描述（同时支持记忆检索、实体状态和时间线窗口），但实现允许从“仅接入 `search_story_memory_tool`”开始渐进落地，依赖降级策略保证链在部分能力尚未实现时仍然可用。
