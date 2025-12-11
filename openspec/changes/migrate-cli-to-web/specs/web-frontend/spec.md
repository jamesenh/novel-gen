## ADDED Requirements

### Requirement: Frontend Technology Stack

系统 MUST 使用 React + TypeScript + Vite 构建前端，搭配 Tailwind CSS 和 React Router v6。

#### Scenario: Initialize frontend project

- **WHEN** 初始化前端项目
- **THEN** 系统 MUST 使用 Vite + React + TypeScript 模板
- **AND** MUST 配置 Tailwind CSS v3 作为样式框架
- **AND** MUST 使用 React Router v6 进行路由管理
- **AND** MUST 使用 Zustand 进行状态管理

### Requirement: Project List Page

系统 MUST 提供项目列表页面，展示所有已创建的小说项目。

#### Scenario: Display project list

- **WHEN** 用户访问项目列表页
- **THEN** 系统 MUST 展示所有项目的卡片列表
- **AND** 每个卡片 MUST 显示项目名称、创建时间、生成状态

#### Scenario: Create new project

- **WHEN** 用户点击"创建项目"按钮
- **THEN** 系统 MUST 显示创建项目表单弹窗
- **AND** 表单 MUST 包含：项目名称、世界观描述、主题描述、初始章节数
- **AND** 提交后 MUST 刷新项目列表

#### Scenario: Search and filter projects

- **WHEN** 用户在搜索框输入关键词
- **THEN** 系统 MUST 实时筛选匹配的项目
- **AND** 匹配 MUST 基于项目名称

#### Scenario: Navigate to project detail

- **WHEN** 用户点击项目卡片
- **THEN** 系统 MUST 导航到该项目的详情页

### Requirement: Project Detail Page

系统 MUST 提供项目详情页，展示项目状态和提供操作入口。

#### Scenario: Display project overview

- **WHEN** 用户访问项目详情页
- **THEN** 系统 MUST 显示：
  - 项目基本信息（名称、创建时间）
  - 6 步生成流程的完成状态
  - 章节生成进度概览

#### Scenario: Navigate to sub-pages

- **WHEN** 用户点击导航链接
- **THEN** 系统 MUST 能导航到：生成控制、内容阅读、世界观、角色、大纲 等子页面

### Requirement: Generation Control Page

系统 MUST 提供生成控制页面，支持启动、停止、恢复生成任务。

#### Scenario: Start generation

- **WHEN** 用户点击"开始生成"按钮
- **THEN** 系统 MUST 调用生成 API 并显示进度
- **AND** 按钮 MUST 变为"停止"状态

#### Scenario: Display real-time progress

- **WHEN** 生成任务执行中
- **THEN** 系统 MUST 通过 WebSocket 显示实时进度
- **AND** MUST 显示：当前步骤、当前章节（如适用）、进度百分比
- **AND** MUST 显示日志输出

#### Scenario: Select stop-at step

- **WHEN** 用户在生成前选择 stop_at 目标步骤
- **THEN** 系统 MUST 将 stop_at 参数随启动请求提交
- **AND** UI MUST 显示当前 stop_at 设定并允许修改或清除

#### Scenario: Stop generation

- **WHEN** 用户点击"停止"按钮
- **THEN** 系统 MUST 调用停止 API 并更新 UI
- **AND** MUST 显示停止确认

#### Scenario: Resume generation

- **WHEN** 用户点击"恢复"按钮（存在检查点时可见）
- **THEN** 系统 MUST 从检查点恢复生成

#### Scenario: Handle WebSocket disconnect

- **WHEN** WebSocket 连接断开
- **THEN** 系统 MUST 自动尝试重连
- **AND** MUST 显示连接状态指示器
- **AND** MUST 使用 HTTP 进度/日志接口恢复最新状态与日志

### Requirement: Chapter Reader Page

系统 MUST 提供章节阅读页面，展示生成的小说内容。

#### Scenario: Display chapter list

- **WHEN** 用户访问阅读页面
- **THEN** 系统 MUST 显示章节列表侧边栏
- **AND** 每章 MUST 显示章节号、标题、字数、完成状态

#### Scenario: Read chapter content

- **WHEN** 用户选择某一章
- **THEN** 系统 MUST 在主区域显示该章所有场景内容
- **AND** 场景之间 MUST 有清晰的分隔

#### Scenario: Navigate between scenes

- **WHEN** 用户点击场景导航
- **THEN** 系统 MUST 滚动到对应场景位置

#### Scenario: Full book reading mode

- **WHEN** 用户选择"全书阅读"模式
- **THEN** 系统 MUST 连续显示所有章节内容

### Requirement: Content Display Components

系统 MUST 提供结构化内容展示组件，用于显示世界观、角色、大纲等数据。

#### Scenario: Display world setting

- **WHEN** 用户访问世界观页面
- **THEN** 系统 MUST 结构化展示世界设定各字段
- **AND** MUST 包括：世界名称、时代背景、地理环境、社会结构、力量体系等

#### Scenario: Display character list

- **WHEN** 用户访问角色页面
- **THEN** 系统 MUST 以卡片形式展示所有角色
- **AND** 卡片 MUST 包含：角色名、角色类型（主角/反派/配角）、简介

#### Scenario: Display character detail

- **WHEN** 用户点击角色卡片
- **THEN** 系统 MUST 显示角色详细信息
- **AND** MUST 包括：背景故事、性格特征、动机目标、能力等

#### Scenario: Display outline tree

- **WHEN** 用户访问大纲页面
- **THEN** 系统 MUST 以树形结构展示章节大纲
- **AND** MUST 显示故事阶段、每章摘要、章节依赖关系

### Requirement: Content Editing UI

系统 MUST 提供内容编辑界面以更新世界观、角色、大纲、章节与场景。

#### Scenario: Edit world setting

- **WHEN** 用户在世界观编辑器中修改字段
- **THEN** 系统 MUST 执行表单校验并调用 PUT /world
- **AND** 保存后 MUST 刷新展示数据

#### Scenario: Edit characters

- **WHEN** 用户在角色编辑器新增/修改角色
- **THEN** 系统 MUST 校验必填字段与角色唯一性
- **AND** MUST 调用 PUT /characters 提交最新列表

#### Scenario: Edit outline

- **WHEN** 用户在大纲编辑器调整章节节点
- **THEN** 系统 MUST 保持章节顺序一致并调用 PUT /outline

#### Scenario: Edit chapter and scenes

- **WHEN** 用户在章节编辑器修改章节元数据或场景文本
- **THEN** 系统 MUST 支持分场景保存/整体保存
- **AND** MUST 调用 PUT /chapters/{num}

#### Scenario: Delete chapter or scene

- **WHEN** 用户在编辑器中删除章节或场景
- **THEN** 系统 MUST 弹出确认对话框
- **AND** MUST 调用 DELETE /chapters/{num}（可带 scene 参数）并刷新列表

### Requirement: Export Functionality

系统 MUST 提供导出功能，支持下载生成的小说。

#### Scenario: Export full novel

- **WHEN** 用户点击"导出全书"按钮
- **THEN** 系统 MUST 下载包含所有章节的 TXT 文件

#### Scenario: Export single chapter

- **WHEN** 用户在章节阅读页点击"导出本章"
- **THEN** 系统 MUST 下载该章节的 TXT 文件

#### Scenario: Export with format options

- **WHEN** 用户选择导出格式（TXT/Markdown/JSON）
- **THEN** 系统 MUST 调用对应导出接口并下载文件

### Requirement: Responsive Layout

系统 MUST 支持响应式布局，适配不同屏幕尺寸。

#### Scenario: Desktop layout

- **WHEN** 在桌面设备访问
- **THEN** 系统 MUST 显示完整的侧边栏导航和多列布局

#### Scenario: Mobile layout

- **WHEN** 在移动设备访问
- **THEN** 系统 MUST 隐藏侧边栏，显示汉堡菜单
- **AND** 内容 MUST 自适应屏幕宽度

### Requirement: Loading and Error States

系统 MUST 正确处理加载状态和错误情况。

#### Scenario: Display loading state

- **WHEN** 数据正在加载
- **THEN** 系统 MUST 显示加载指示器（骨架屏或 spinner）

#### Scenario: Display error state

- **WHEN** API 请求失败
- **THEN** 系统 MUST 显示友好的错误信息
- **AND** MUST 提供重试选项

#### Scenario: Display empty state

- **WHEN** 列表数据为空
- **THEN** 系统 MUST 显示空状态提示
- **AND** MUST 提供创建/生成的引导

