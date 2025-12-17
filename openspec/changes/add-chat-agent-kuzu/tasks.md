## 1. Implementation

### 1.1 Milestone 0（基线保障）
- [x] 1.1.1 新增项目级图谱目录约定：`projects/<id>/data/graph/`（不改变现有 JSON 真源）
- [x] 1.1.2 新增 `ng graph rebuild <project>`：从 JSON（characters.json + chapter_memory.json）全量重建图谱（幂等）
- [x] 1.1.3 为图谱层添加开关配置（默认启用，依赖存在则可用；失败则优雅降级）

### 1.2 Milestone 1（Kùzu 图谱最小闭环）
- [x] 1.2.1 引入 Kùzu Python 依赖（`kuzu`），并更新 `pyproject.toml`/锁文件
- [x] 1.2.2 实现 `novelgen/graph/kuzu_store.py`：连接/初始化 schema/基础 CRUD/查询封装
- [x] 1.2.3 实现 `novelgen/graph/updater.py`：  
  - 从 `characters.json` 初始化 Character 与 RELATES_TO  
  - 从 `chapter_memory.json`（或单条 ChapterMemoryEntry）写入 Chapter/Event/参与关系与 evidence_ref
- [x] 1.2.4 将 GraphUpdater 挂接到章节完成点：在章节记忆写入成功后增量更新 Kùzu（失败不阻断生成）
  - 注意：必须覆盖所有会写入 `chapter_memory.json` 的路径（`novelgen/runtime/nodes.py` 与 `novelgen/runtime/orchestrator.py`），建议抽公共的"append + hook"函数以避免漏挂
- [x] 1.2.5 新增 `ng graph whois/relations/events <project> <name>` 查询命令（返回证据引用）
  - `relations` 应支持 pair query：`ng graph relations <project> A --with B`（优先返回 A↔B 直接关系）

### 1.3 Milestone 2（P1：对话式 Agent MVP）
- [x] 1.3.1 新增 `novelgen/agent/chat.py`：`ng chat <project>` REPL 会话（加载项目状态/偏好/图谱可用性）
- [x] 1.3.2 新增 `novelgen/tools/registry.py`：工具注册、max tool calls、确认门槛（Safety Gate）
- [x] 1.3.3 实现工具集：
  - [x] 1.3.3.1 `workflow_tools.py`：run/resume/status/rollback/export（复用现有 orchestrator/workflow）
  - [x] 1.3.3.2 `preference_tools.py`：/setpref /prefs /forget（Mem0 user memory，项目隔离）
  - [x] 1.3.3.3 `graph_tools.py`：/whois /relations /events（Kùzu 查询）
  - [x] 1.3.3.4 `memory_tools.py`：可选的 Mem0 场景/实体检索工具（用于问答与解释）
- [x] 1.3.4 实现自然语言覆盖（A）：  
  - 意图分类（Generate/QueryGraph/SetPref/Rollback/Export/Status/Explain）  
  - 参数缺失时提问 1-3 个澄清问题  
  - 生成结构化 ToolPlan 并执行
- [x] 1.3.4.1 实现"信息充足性自评 + 工具优先补齐"循环：  
  - 生成/继续生成：先 `WorkflowTool.status` 获取进度与可恢复性  
  - 知识问答：优先 GraphTool/MemoryTool 检索候选与证据，再进行澄清提问  
  - 明确缺失信息清单（MissingInfo）并输出给用户
- [x] 1.3.4.2 实现检索上限与停止条件：  
  - 工具调用补齐最多 N 次（默认 3，可配置）  
  - 达到上限仍不足：输出缺失信息清单并提问  
  - 信息足够：停止检索/提问，进入确认/回答阶段
- [x] 1.3.5 默认确认策略（A）+ `/auto on|off`：  
  - 默认生成动作需确认  
  - `/auto on` 会话内关闭确认（回滚/清理仍需确认）
- [x] 1.3.6 关键验收：偏好注入闭环  
  - 场景生成前从 Mem0 检索项目偏好（Top 5）  
  - 构建最小 `chapter_context`：最近 N 章 `chapter_memory.json` 聚合（summary/key_events/character_states/unresolved_threads）+ 偏好（Top 5），并注入到 prompt  
  - 任意入口（非 chat）运行 workflow 时也应生效

## 2. Validation

- [x] 2.1 单元测试：Kùzu schema 初始化/重建幂等/查询返回证据
- [x] 2.2 单元测试：偏好写入/检索（Mem0）与注入 prompt 的数据路径（不要求真实 LLM）
- [x] 2.3 集成测试：`ng chat` 基本交互（slash 命令 + 计划确认 + `/auto on`）
- [ ] 2.4 OpenSpec：`openspec validate add-chat-agent-kuzu --strict` 通过

## 3. Docs

- [x] 3.1 更新 `README.md`：新增 `ng chat` 与 `ng graph` 的使用说明
- [x] 3.2 在 `重构文档.md` 中标注 Milestone 0-2 的落地状态与命令示例

