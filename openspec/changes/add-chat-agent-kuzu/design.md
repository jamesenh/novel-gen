## Context

本变更将 NovelGen 的“主要交互模式”从命令式/工作流式升级为 **对话式 Agent**。现有 LangGraph workflow 已经稳定、可断点续跑且以 JSON 落盘为真源，因此应保留其作为 **可靠执行器（Executor）**；新增的 Agent 层只负责“决策、澄清、工具调用与解释”，避免把业务逻辑耦合进 LLM。

同时，为增强人物信息检索能力，引入 **嵌入式图数据库 Kùzu**，通过章节粒度写入（基于 chapter_memory.json 的结构化摘要）建立可解释的知识图谱，解决“关系/事件/证据来源”类查询。

## Goals / Non-Goals

### Goals
- 提供 `ng chat <project_id>` 对话式入口，支持自然语言驱动生成/查询/回滚等动作。
- 默认确认策略：生成类动作需确认；支持 `/auto on` 在会话内关闭确认（破坏性动作仍需确认）。
- 引入 Kùzu（嵌入式、每项目隔离）并实现章节粒度图谱更新与基础查询。
- 场景生成前检索项目级写作偏好（Mem0 user memory）并注入 prompt，使“更懂你”可持续生效。

### Non-Goals
- 场景级别入图与复杂三元组抽取（后续扩展）。
- Web/API 服务化、多用户、鉴权、并发任务队列。
- 从一致性修订自动学习偏好（本阶段仅支持“用户显式设置/确认后写入”）。

## Decisions

### Decision 1: Agent 与 workflow 分层
- **选择**：保留 `novelgen/runtime/workflow.py` 作为执行器；新增 `novelgen/agent` 作为对话与决策层。
- **理由**：workflow 适合确定性步骤与检查点；Agent 适合多轮澄清与工具组合。分层可降低重构风险并保留断点续跑能力。

### Decision 2: Tool Registry + Safety Gate
- **选择**：所有可执行动作通过 Tools 暴露；对话层产出结构化 `ToolPlan`，执行前由 Safety Gate 判断是否需要确认。
- **理由**：避免 LLM 直接调用内部函数导致不可控副作用；将可控性/可解释性/确认策略收敛到一处。

### Decision 3: 项目级偏好存储（Mem0）
- **选择**：偏好按项目隔离（`user_id="author_{project_id}"`），以自然语言存储；生成前检索 TopN 偏好并注入 prompt。
- **理由**：用户明确要求“每项目一套偏好”；自然语言偏好更贴近写作场景且易于对话维护。

### Decision 4: Kùzu 作为嵌入式图谱存储
- **选择**：使用 Kùzu 嵌入式数据库，数据目录位于 `projects/<id>/data/graph/`，每项目隔离。
- **理由**：零部署、易备份、适合本地 CLI 生成；图查询能力强，适合人物关系与证据追溯。

### Decision 5: 章节粒度入图（P0）
- **选择**：以 `chapter_memory.json` 作为章节结构化摘要来源，生成后增量入图；先用 `characters.json` 初始化关系。
- **理由**：低成本、稳定、可解释；避免早期对正文抽取造成成本与误差。

## Tooling & Interfaces

### Tool Categories
- **WorkflowTool**：run/resume/status/rollback/export（对接现有 orchestrator/workflow）
- **PreferenceTool**：set/list/forget（对接 Mem0 User Memory）
- **GraphTool**：whois/relations/events（对接 Kùzu；`rebuild` 为 CLI 管理命令，MVP chat 不默认暴露）
- **MemoryTool**：scene/entity 检索（对接 Mem0 场景分块与角色状态）

### Graph Update Mapping (P0 规则，避免过度抽取)
为满足“章节粒度入图 + 可解释 evidence_ref”的目标，同时避免进入正文三元组抽取，本阶段统一采用 `chapter_memory.json` 的字段做确定性映射：

- **Event 来源**：每条 `ChapterMemoryEntry.key_events[i]` 视为一个事件事实（Event）
- **Event ID**：`event_id = f"ch{chapter_number}_e{i+1}"`（稳定、可复用）
- **参与者（PARTICIPATES）**：
  - 优先从 `characters.json` 的角色名列表做字符串匹配（出现即认为参与）
  - 若无匹配则允许不创建参与边（避免误判）
- **evidence_ref（必填）**：每个 Event 写入时必须携带最小证据引用：
  - `{"chapter_number": N, "source": "chapter_memory.key_events[i]", "snippet": key_events[i]}`
  - 注：落到 Kùzu 属性时可使用 JSON 字符串存储（便于打印与可追溯）

### Confirmation Policy
- 默认：`run/resume` 等生成动作需要确认。
- `/auto on`：关闭会话内的生成确认（仍保留回滚/清理等破坏性动作确认）。
- `/auto off`：恢复默认确认。

## Risks / Trade-offs
- **图谱与 JSON 不一致**：提供 `ng graph rebuild` 从 JSON 全量重建；写入应尽量幂等。
- **嵌入式写入并发**：先限定单进程写入；若引入并行生成，写入层需加锁或队列化。
- **偏好注入导致 prompt 变长**：限制 TopN（默认 5）并做格式化；后续可扩展“按需检索/工具调用”。

## Migration Plan

1. **Milestone 0**：不改变现有 workflow 行为，新增图谱重建命令与基础目录结构（可选启用）。
2. **Milestone 1**：引入 Kùzu，完成人物/关系初始化与章节粒度增量入图；提供 `ng graph` 查询命令。
3. **Milestone 2**：实现 `ng chat` Agent MVP + tools + 默认确认 + `/auto on`；并完成偏好检索注入到场景生成 prompt 的闭环。

## Open Questions

（已确认）
- Kùzu 选型：嵌入式
- 图谱更新粒度：按章节
- 自然语言覆盖：支持触发动作（A）
- 确认策略：默认确认（A），提供 `/auto on` 关闭确认（会话内）


