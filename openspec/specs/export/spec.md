# export Specification

## Purpose

导出模块负责将 JSON 格式的章节数据转换为标准的中文小说 txt 格式。支持单章导出和全书导出，遵循中文小说的排版规范，包括章节标题格式化、场景分隔和段落排版。

**技术实现**：
- 从 `GeneratedChapter` Pydantic 模型读取章节数据
- 章节编号转换为中文（第一章、第二章等）
- 场景之间用空行分隔，章节之间用三个空行分隔
- 输出使用 UTF-8 编码

**代码位置**：`novelgen/runtime/exporter.py`

## Requirements

### Requirement: Export Novel Contents to Readable Format

The system MUST export chapter data in JSON format to standard Chinese novel txt format, providing functionality for single chapter export and complete novel export.

#### Scenario: Export single chapter

- **WHEN** 调用 export_chapter(chapter_number=N)
- **THEN** 系统应从 chapter_N.json 文件读取数据
- **AND** 生成格式化的 txt 文件包含:
  - 章节标题（如"第一章：XXX"）
  - 各场景文本（场景之间空行分隔）
  - 标准排版格式（UTF-8 编码）

#### Scenario: Export entire novel

- **WHEN** 调用 export_all_chapters()
- **THEN** 系统应遍历所有 chapter_XXX.json 文件
- **AND** 按章节顺序合并成完整小说文本
- **AND** 在输出文件中体现章节编号递增（第一章、第二章...）

#### Scenario: Default output paths

- **WHEN** 导出时不指定 output_path 参数
- **THEN** 单个章节应保存到 chapters/chapter_N.txt
- **AND** 完整小说应保存到项目根目录的 {project_name}_full.txt

#### Scenario: Custom output paths

- **WHEN** a custom output_path is provided during export
- **THEN** the system MUST write content to the specified path
- **AND** create necessary parent directories

#### Scenario: Handle missing files

- **WHEN** a chapter is specified for export but its JSON file does not exist
- **THEN** the system MUST raise ValueError with message "Please generate the chapter first"
- **AND** prevent generating incomplete export files

### Requirement: Format Chapter Numbers in Chinese

The system MUST convert numeric chapter numbers to Chinese format.

#### Scenario: Format single digit chapters

- **WHEN** 章节编号为 1-10
- **THEN** 系统 MUST 输出"第一章"到"第十章"

#### Scenario: Format double digit chapters

- **WHEN** 章节编号为 11-99
- **THEN** 系统 MUST 正确组合中文数字
- **AND** 例如 15 输出为"第十五章"，20 输出为"第二十章"

### Requirement: Apply Chinese Novel Formatting

The system MUST apply standard Chinese novel formatting conventions.

#### Scenario: Format chapter header

- **WHEN** 导出章节时
- **THEN** 章节标题格式 MUST 为："{中文章节号} {章节标题}"
- **AND** 标题后 MUST 有一个空行

#### Scenario: Format scene separators

- **WHEN** 章节包含多个场景
- **THEN** 场景之间 MUST 有两个空行分隔
- **AND** 最后一个场景后不需要额外空行

#### Scenario: Format chapter separators

- **WHEN** 导出全书包含多个章节
- **THEN** 章节之间 MUST 有三个空行分隔
- **AND** 最后一章后不需要额外空行

### Requirement: Provide Export Statistics

The system SHOULD provide statistics after export operations.

#### Scenario: Output single chapter statistics

- **WHEN** 单章导出完成
- **THEN** 系统 SHOULD 在控制台输出：
  - 导出文件路径
  - 章节标题
  - 总字数

#### Scenario: Output full novel statistics

- **WHEN** 全书导出完成
- **THEN** 系统 SHOULD 在控制台输出：
  - 导出文件路径
  - 总章节数
  - 总字数
