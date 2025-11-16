## ADDED Requirements

### Requirement: Export Novel Contents to Readable Format
The system MUST export chapter data in JSON format to standard Chinese novel txt format, providing functionality for single chapter export and complete novel export.

#### Scenario: Export single chapter
- **WHEN** 调用export_chapter(chapter_number=N)
- **THEN** 系统应从chapter_N.json文件读取数据
- **AND** 生成格式化的txt文件包含:
  - 章节标题（如"第一章：XXX"）
  - 各场景文本（场景之间空行分隔）
  - 标准排版格式（UTF-8编码）

#### Scenario: Export entire novel
- **WHEN** 调用export_all_chapters()
- **THEN** 系统应遍历所有chapter_XXX.json文件
- **AND** 按章节顺序合并成完整小说文本
- **AND** 在输出文件中体现章节编号递增（第一章、第二章...）

#### Scenario: Default output paths
- **WHEN** 导出时不指定output_path参数
- **THEN** 单个章节应保存到chapters/chapter_N.txt
- **AND** 完整小说应保存到项目根目录的{project_name}_full.txt

#### Scenario: Custom output paths
- **WHEN** a custom output_path is provided during export
- **THEN** the system MUST write content to the specified path
- **AND** create necessary parent directories

#### Scenario: Handle missing files
- **WHEN** a chapter is specified for export but its JSON file does not exist
- **THEN** the system MUST raise ValueError with message "Please generate the chapter first"
- **AND** prevent generating incomplete export files
