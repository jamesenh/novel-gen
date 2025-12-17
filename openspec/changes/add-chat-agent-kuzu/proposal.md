## Why

当前 NovelGen 已具备稳定的 LangGraph 工作流执行能力（断点续跑/回滚/文件落盘）以及 Mem0 记忆层，但缺少“对话式 Agent”这一决策与交互层，无法通过多轮对话完成创作驱动与个性化偏好管理；同时人物信息检索主要依赖 JSON/向量检索，难以回答“关系/事件/证据”类结构化问题。

本提案将项目目标明确转为 **Agent-first**：以对话式 Agent 作为主入口与决策核心，保留现有 workflow 作为可靠执行器；并引入 **嵌入式图数据库 Kùzu**（按章节粒度更新）增强人物/关系/事件检索能力，交付到 `重构文档.md` 的 **Milestone 0-2（包含 Kùzu + 对话式 Agent MVP）**。

## What Changes

- **新增对话式入口**：提供 `ng chat <project_id>` 作为主交互入口，支持自然语言驱动生成/查询/回滚等动作，以及斜杠命令直达。
- **新增工具系统（Tool Registry）**：将 workflow、Mem0 偏好、Mem0 记忆检索、Kùzu 图谱查询封装为可调用工具，并加入确认门槛与最大调用次数控制。
- **新增 Kùzu 图谱层（按项目隔离）**：
  - 在 `projects/<id>/data/graph/` 初始化嵌入式 Kùzu 数据库
  - 从 `characters.json` 初始化人物与关系
  - 在每章 `chapter_memory.json` 写入成功后，增量写入 Chapter/Event/参与关系与证据引用（Event 以 `key_events` 为来源，避免正文抽取）
  - 提供 `ng graph ...` 基础查询命令（whois/relations/events）与重建命令（rebuild）
- **完成“更懂你”的关键链路（项目级偏好）**：
  - 偏好以自然语言存储到 Mem0（项目隔离：`user_id="author_{project_id}"`）
  - 场景生成前检索偏好并注入到 prompt（默认需要确认执行；支持 `/auto on` 关闭确认）
- **交互安全策略**：
  - 默认所有生成类动作需要确认（确认策略 A）
  - 提供 `/auto on` 在当前会话内关闭确认（但回滚/清理等破坏性动作仍需确认）

## Impact

- **Affected specs（将通过 spec deltas 更新/新增）**
  - `scene-text-generation`（偏好检索与注入从 SHOULD 提升为 MUST）
  - `configuration`（新增 Kùzu 图谱层与 chat agent 相关配置）
  - `orchestration`（新增“每章后更新知识图谱”的编排要求）
  - 新增能力：`agent-chat`、`knowledge-graph`

- **Affected code（后续实现阶段会改动/新增）**
  - 新增：`novelgen/agent/*`, `novelgen/tools/*`, `novelgen/graph/*`
  - 修改：`novelgen/cli.py`, `novelgen/runtime/nodes.py`, `novelgen/config.py`, `novelgen/models.py`
  - 依赖：新增 `kuzu` Python 依赖（嵌入式）

## Non-Goals（本提案不做）

- 场景级别入图（仅章节粒度入图）
- 从正文自动抽取复杂三元组/事件（P2+ 扩展）
- Web 应用/API 服务化（仅 CLI 对话式）
- 多用户/鉴权/并发任务队列


