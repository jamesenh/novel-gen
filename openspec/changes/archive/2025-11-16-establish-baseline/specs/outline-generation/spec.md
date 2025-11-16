## ADDED Requirements

### Requirement: Generate Structured Story Outline
The system MUST generate a structured story outline including story premise, five-act structure (beginning, development, climax, resolution), and chapter list based on the world setting, theme conflict, and character configuration.

#### Scenario: Define story premise
- **WHEN** 生成大纲时
- **THEN** 系统应总结故事前提，清晰阐述"这是一个关于什么的故事"
- **AND** 前提应体现世界观和主题冲突的核心元素

#### Scenario: Build five-act structure
- **WHEN** 生成大纲结构
- **THEN** 必须包含并用1-2段描述:
  - beginning: 故事开端（引入世界、人物、初始冲突）
  - development: 发展过程（冲突升级、人物成长、关系演变）
  - climax: 高潮（冲突顶点、重大转折、决定性时刻）
  - resolution: 结局（冲突解决、人物归宿、世界变化）

#### Scenario: Plan chapter sequence
- **WHEN** 用户指定章节数量num_chapters（默认20章）
  - 应适配不同长度需求（短篇10章，中篇20章，长篇50章等）
- **THEN** 系统应生成对应数量的章节摘要列表
- **AND** 每个章节包含:
  - chapter_number: 章节序号
  - chapter_title: 章节标题
  - summary: 章节概要（本章节发生的主要事件）
  - key_events: 关键事件列表（推动剧情的重要节点）

#### Scenario: Maintain pacing and progression
- **WHEN** planning the chapter sequence
- **THEN** chapter content MUST reflect reasonable pacing (alternating tension and relaxation)
- **AND** MUST ensure plot progression from beginning → development → climax → resolution
