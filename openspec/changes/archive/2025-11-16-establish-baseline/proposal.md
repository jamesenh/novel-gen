## Why

NovelGen系统已具备完整的小说生成能力，但尚未建立规范文档。本提案将捕获当前系统的全部核心行为，为后续开发和维护建立明确的规范基线。

## What Changes

- 建立系统核心能力的规范文档（9个核心能力）
  - 世界观生成（world-creation）
  - 主题冲突生成（theme-conflict-generation）
  - 角色生成（character-generation）
  - 故事大纲生成（outline-generation）
  - 章节计划生成（chapter-planning）
  - 场景文本生成（scene-text-generation）
  - 编排协调（orchestration）
  - 导出功能（export）
  - 配置管理（configuration）

## Impact

- **受影响的规范**: 新建立9个核心能力规范
- **受影响的代码**: novelgen/ 目录下所有核心模块（models.py, config.py, chains/, runtime/）
