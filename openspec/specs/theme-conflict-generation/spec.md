# theme-conflict-generation Specification

## Purpose

主题冲突生成模块负责根据世界观设定，提炼并构建故事的核心主题、次要主题、主要冲突和次要冲突结构。该模块定义故事的中心矛盾和叙事基调，为后续角色塑造和情节发展提供方向。

**技术实现**：
- 使用 LangChain `ChatPromptTemplate` 构建结构化提示词
- 输出符合 `ThemeConflict` Pydantic 模型
- 支持用户方向性输入来引导主题倾向
- 生成结果保存到 Mem0 便于后续检索

**代码位置**：`novelgen/chains/theme_conflict_chain.py`

## Requirements

### Requirement: Generate Theme and Conflict Structure

The system MUST generate a theme and conflict structure including core theme, sub-themes, main conflict, sub-conflicts, and narrative tone based on the world setting.

#### Scenario: Derive themes from world setting

- **WHEN** 调用主题冲突生成功能并提供 WorldSetting 属性
- **THEN** 系统应分析世界观并提炼出符合设定的核心主题（如复仇、成长、守护等）
- **AND** 识别 2-3 个次要主题丰富故事层次

#### Scenario: Define conflict hierarchy

- **WHEN** 系统生成主题结构
- **THEN** 必须明确主要冲突（推动主线剧情的核心矛盾）
- **AND** 列出 2-4 个次要冲突（人物关系、内心挣扎、支线故事等）

#### Scenario: Set narrative tone

- **WHEN** 生成主题冲突数据
- **THEN** 必须包含 tone 字段描述整体作品基调
- **AND** 基调应体现严肃/轻松、黑暗/明亮、快节奏/慢热、悲剧/喜剧等属性

#### Scenario: Accept user direction input

- **WHEN** the user provides a story direction description (e.g., "a tragic story about revenge")
- **THEN** the system MUST deepen and refine the theme and conflict structure in the specified direction

### Requirement: Validate Output Structure

The system MUST ensure the generated theme conflict data conforms to the ThemeConflict Pydantic model.

#### Scenario: Validate required fields

- **WHEN** 主题冲突生成完成
- **THEN** 输出 MUST 包含以下必需字段：
  - core_theme: 核心主题（字符串）
  - sub_themes: 次要主题列表（字符串数组）
  - main_conflict: 主要冲突（字符串）
  - sub_conflicts: 次要冲突列表（字符串数组）
  - tone: 作品基调（字符串）
