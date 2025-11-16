## ADDED Requirements

### Requirement: Generate Theme and Conflict Structure
The system MUST generate a theme and conflict structure including core theme, sub-themes, main conflict, sub-conflicts, and narrative tone based on the world setting.

#### Scenario: Derive themes from world setting
- **WHEN** 调用主题冲突生成功能并提供WorldSetting属性
- **THEN** 系统应分析世界观并提炼出符合设定的核心主题（如复仇、成长、守护等）
- **AND** 识别2-3个次要主题丰富故事层次

#### Scenario: Define conflict hierarchy
- **WHEN** 系统生成主题结构
- **THEN** 必须明确主要冲突（推动主线剧情的核心矛盾）
- **AND** 列出2-4个次要冲突（人物关系、内心挣扎、支线故事等）

#### Scenario: Set narrative tone
- **WHEN** 生成主题冲突数据
- **THEN** 必须包含tone字段描述整体作品基调
- **AND** 基调应体现严肃/轻松、黑暗/明亮、快节奏/慢热、悲剧/喜剧等属性

#### Scenario: Accept user direction input
- **WHEN** the user provides a story direction description (e.g., "a tragic story about revenge")
- **THEN** the system MUST deepen and refine the theme and conflict structure in the specified direction
