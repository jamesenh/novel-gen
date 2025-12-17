## ADDED Requirements

### Requirement: Configure Embedded Knowledge Graph Layer (Kùzu)

The system MUST support configuring the embedded knowledge graph layer and its storage location per project.

#### Scenario: Enable graph layer by configuration

- **WHEN** 用户启用图谱层（默认启用，或通过环境变量显式启用）
- **THEN** 系统 MUST 使用 `projects/<project_id>/data/graph/` 作为默认图谱目录
- **AND** 系统 MUST 支持环境变量 `NOVELGEN_GRAPH_ENABLED`（默认 true）以显式启用/禁用图谱层
- **AND** 系统 MAY 支持环境变量 `NOVELGEN_GRAPH_DIR` 覆盖默认图谱目录（若为相对路径，应相对于项目目录解析）
- **AND** 系统 MUST 在图谱不可用（依赖缺失/初始化失败）时优雅降级并输出提示

### Requirement: Configure Chat Agent Confirmation Defaults

The system MUST support configuring chat agent confirmation defaults and allow session-level override via `/auto on|off`.

#### Scenario: Default confirm is enabled

- **WHEN** 用户启动 `ng chat <project_id>`
- **THEN** 系统 MUST 默认启用 run/resume 的确认步骤
- **AND** 系统 MUST 支持环境变量 `NOVELGEN_CHAT_CONFIRM_DEFAULT`（默认 true）以调整默认确认策略
- **AND** 系统 MUST 支持环境变量 `NOVELGEN_CHAT_MAX_TOOL_CALLS`（默认 10）以限制单轮输入可触发的总工具调用次数
- **AND** 系统 MUST 支持环境变量 `NOVELGEN_CHAT_RETRIEVAL_MAX_ATTEMPTS`（默认 3）以控制“工具优先补齐”循环的最大尝试次数
- **AND** 用户可通过 `/auto on` 在会话内关闭确认


