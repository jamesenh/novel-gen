# 阶段2数据层验证提案

## Why
阶段1已实现数据库和向量存储的基础持久化功能，但在「查询接口完整性」以及「面向人工检查的基础 CLI 工具」方面仍然不足。为了验证数据模型和查询设计是否符合实际需求，在不影响现有生成流程的前提下，需要一个只读验证阶段：通过完善数据库/向量库查询接口，并提供最小化的命令行脚本，让开发者能够方便地查看某个项目/场景下的实体状态和相关记忆。

## What Changes
- **完善数据库查询层接口**：添加`get_latest_entity_state`、`get_entity_timeline`、`get_timeline_around`等只读查询方法，为后续 CLI 和调试脚本提供统一入口
- **完善向量库查询层接口**：添加`search_memory_with_filters`、`get_chunks_by_entities`等只读查询方法，支持按实体、标签和内容类型过滤记忆块
- **添加健康检查接口**：在`DatabaseManager`和`VectorStoreManager`中提供`health_check`方法，用于验证连接状态和基础结构是否可用
- **实现基础CLI查询工具**：在`scripts/`目录下提供最小化的命令行工具，支持：
  - 通过`project_id + entity_id` 查询实体最新状态
  - 通过`project_id + chapter_index + scene_index` 查询与场景相关的记忆块

## Impact
- **受影响的规范**：`data-persistence`（扩展查询接口和健康检查要求）、`data-quality-validation`（新增“基础数据检查 CLI”的最小要求；不包含数据质量评分、趋势分析等高级能力）
- **受影响的代码**：`novelgen/runtime/db.py`、`novelgen/runtime/vector_store.py`、`novelgen/runtime/memory_tools.py`（如需）、以及`scripts/`目录下的基础查询脚本
- **非破坏性变更**：所有新增功能都是只读的，不影响现有的生成流程
- **依赖关系**：依赖阶段1的数据库和向量存储基础架构

