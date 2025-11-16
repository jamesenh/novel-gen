## ADDED Requirements

### Requirement: Generate Novel Text from Scene Plans
The system MUST generate high-quality novel scene text based on scene plans, world setting, and character configuration, providing previous scene context for improved coherence.

#### Scenario: Write scene narrative
- **WHEN** 提供scene_plan（类型、强度、地点、角色、目的）
- **THEN** 系统应生成完整的中文小说场景文本
- **AND** 输出必须满足:
  - 字数严格控制在estimated_words上下浮动10%以内
  - 符合scene_type指定的类型（日常/对话/战斗等）风格
  - 体现intensity对应的紧张程度
  - 出场角色符合character配置的性格与能力

#### Scenario: Maintain coherence with previous content
- **WHEN** 提供previous_summary参数（前文概要）
- **THEN** 生成文本应与前文保持连贯性
- **AND** 人物状态、情节发展应与之前内容衔接自然

#### Scenario: Apply world rules and lore
- **WHEN** the world setting defines special rules (e.g., cultivation system, magic system)
- **THEN** the scene text MUST strictly adhere to these settings
- **AND** character behavior MUST reflect ability limitations and social norms in the world setting

#### Scenario: Enforce word count limits
- **WHEN** scene_plan specifies estimated_words as 2000 words
- **THEN** the generated scene.word_count MUST be within 1800-2200 words
- **AND** generations that are too short or too long MUST be considered non-compliant

#### Scenario: Return structured scene data
- **WHEN** 场景文本生成完成
- **THEN** 应返回GeneratedScene对象包含:
  - scene_number: 场景编号
  - content: 场景正文（字符串）
  - word_count: 实际计算的字数（整数）
