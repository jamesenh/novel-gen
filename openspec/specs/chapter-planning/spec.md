# chapter-planning Specification

## Purpose
TBD - created by archiving change establish-baseline. Update Purpose after archive.
## Requirements
### Requirement: Generate Detailed Chapter Plans
The system MUST break down a chapter summary into a detailed plan containing multiple scenes, where each scene defines scene number, location, characters, purpose, key actions, and estimated word count.

#### Scenario: Plan scenes for chapter
- **WHEN** 输入chapter_summary（标题、概要、关键事件）
- **THEN** 系统应将章节分解为3-5个连贯的场景
- **AND** 每个场景必须包含:
  - scene_number: 场景编号（1,2,3...）
  - location: 具体场景地点
  - characters: 出场角色名称列表
  - purpose: 场景目的（达成什么叙事目标）
  - key_actions: 关键动作列表
  - estimated_words: 预计字数（根据场景复杂度）
  - scene_type: 场景类型（日常/对话/战斗/发展/高潮/结局）
  - intensity: 强度等级（低/中/高）

#### Scenario: Ensure scene variety
- **WHEN** 生成章节计划时
- **THEN** 场景类型应多样化（避免连续多个相同类型场景）
- **AND** 场景强度应有起伏变化，形成节奏感

#### Scenario: Link scenes logically
- **WHEN** generating multiple scenes
- **THEN** scenes MUST have clear causal relationships or emotional transitions
- **AND** MUST ensure the scene sequence advances the chapter's key events and overall objectives

#### Scenario: Support batch processing
- **WHEN** a list of chapter numbers is provided for chapter plan generation
- **THEN** the system MUST batch generate plans for all specified chapters
- **AND** return a list of ChapterPlan objects

