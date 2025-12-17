## Why

当前 `ng chat` 侧虽然已经具备“意图识别 + 约束/范围解析 + 确认策略”，但在真正执行阶段，工具可用性仍然高度依赖 `workflow.run/resume(stop_at=...)` 这一粗粒度入口。由于 LangGraph 工作流节点（尤其 `chapter_planning` 与章节循环生成）偏“批量/顺序/全量”设计，导致：

- 用户/LLM 明确提出“只生成某几章（计划/正文）”时，系统缺少可精确执行该范围的工具，只能降级为全量执行或拒绝。
- 想做精细化补齐（只补缺的 plan、只补缺的正文、只重做某章、只做一致性检查/修订）时，LLM 无法组合出最小代价的操作序列。
- 工作流的“全流程可靠执行”与对话式 Agent 的“局部可控执行”之间缺少一层稳定的“可组合工具层（fine-grained tool layer）”。

本提案的目标是：**在不引入新的 CLI 命令、不改变用户的 `ng run/resume` 使用习惯的前提下**，为 `ng chat` 新增一组细粒度工具，使 Agent 能以更小的执行范围、更低的成本、更可控的副作用完成“部分生成/补齐/修复”。

## What Changes

- **新增 Agent 专用工具层（fine-grained tooling）**：在现有 Tool Registry 体系下新增一组“细粒度生成与维护工具”，覆盖：
  - settings：读取/更新章节数量等关键配置
  - outline：生成/扩展/裁剪（按配置）
  - chapter plan：按章节范围生成/补齐/删除
  - chapter text：按章节范围生成/补齐/删除（默认强制顺序约束，避免跳章破坏一致性）
  - consistency/revision：按章节范围检查与修订（可选分阶段交付）
  - memory/export：按范围重建记忆与导出（可选分阶段交付）
- **范围执行从“降级”升级为“可精确执行（至少针对章节计划/正文）”**：当解析到 `ChapterScope` 且目标为章节计划/正文时，Agent 优先调用新工具精确执行，而不是退回全量工作流。
- **工具契约**：
  - 以 JSON 为真源（projects/<id>/...）为落盘与复用依据，遵守 `force` 与 `missing_only` 语义
  - 明确前置依赖校验（缺失时返回结构化缺失信息，由 Agent 进行计划与确认）
  - 禁止静默扩张执行范围（scope 必须可控、可回显、可确认）

## Impact

- **Affected specs（通过 spec deltas 更新/新增）**
  - 新增能力：`agent-tooling`（Agent 专用细粒度工具层的工具清单与行为契约）
  - `agent-chat`：要求在已解析范围且工具可支持时必须走精确范围工具执行（不再默认降级为全量）
  - `orchestration`：补充“为 agent-tooling 暴露可复用的章节范围生成原语（plan/text）”的契约，避免工具层被迫走全量工作流

- **Affected code（实现阶段将改动/新增）**
  - 新增：`novelgen/tools/settings_tools.py`, `novelgen/tools/outline_tools.py`, `novelgen/tools/chapter_tools.py`（以及可选 `consistency_tools.py` 等）
  - 修改：`novelgen/agent/chat.py`（将章节范围类请求路由到新工具，而非强制降级）
  - 可能修改：`novelgen/runtime/orchestrator.py`/`novelgen/runtime/*`（提供可被工具层复用的章节范围执行原语，或提供无 LangGraph 的“局部执行器”）

- **Dependencies**
  - 本提案依赖 `agent-chat` 基础能力（Tool Registry、确认策略、意图解析）已存在或先落盘（当前见 `add-chat-agent-kuzu`、`update-chat-intent-scope-parsing`、`update-chat-targeted-generation`）。

## Non-Goals（本提案不做）

- 不新增或修改任何 CLI 命令/参数（仅服务 `ng chat` 的内部工具调用）
- 不重写 LangGraph 全流程拓扑；`ng run/resume` 行为保持不变
- 不承诺一次性交付所有工具：将按“最小可用（章节计划/正文范围执行）→ 扩展（scene/consistency/revision/memory/export）”分阶段实现

