## 1. Proposal Checklist

- [x] 1.1 确认本变更仅服务 `ng chat`（不新增 CLI）
- [x] 1.2 对齐工具清单与命名（见 agent-tooling spec delta）
- [x] 1.3 确认与现有变更的依赖/冲突（agent-chat 相关 changes）

## 2. Tool Inventory（完整工具清单）

说明：本清单是"最终应具备的 Agent 可用工具集合"。实现可分阶段交付（Phase A/B/C/D），但需要在任务列表中明确每个工具的归属与验收点。

### 2.1 Project/Status

- [x] `project.status(detail=false)`
- [x] `project.validate_prereqs(target)`
- [x] `project.list_artifacts(kind, chapter_scope?)`

### 2.2 Settings

- [x] `settings.get()`
- [x] `settings.update(patch, persist=true)`

### 2.3 Outline

- [x] `outline.generate(num_chapters|initial_chapters|max_chapters, force=false)`
- [x] `outline.extend(additional_chapters, force=false)`
- [x] （可选）`outline.trim(max_chapters)`（破坏性）
- [x] （可选）`outline.reindex()`（破坏性）

### 2.4 Chapter Plan

- [x] `chapter.plan.generate(chapter_scope|chapter_numbers|None, force=false, missing_only=true)`
- [x] （可选）`chapter.plan.ensure_all(force_missing_only=true)`（语义糖，等价于 missing_only）
- [x] （可选）`chapter.plan.delete(chapter_scope|chapter_numbers)`（破坏性）

### 2.5 Chapter Text

- [x] `chapter.text.generate(chapter_scope|chapter_numbers, force=false, missing_only=true, sequential=true)`
- [x] （可选）`chapter.text.ensure_all(force_missing_only=true)`（语义糖，等价于 missing_only）
- [x] （可选）`chapter.text.delete(chapter_scope|chapter_numbers)`（破坏性）

### 2.6 Scene（可选）

- [x] `scene.generate(chapter_number, scene_scope?, force=false)`
- [x] （可选）`scene.delete(chapter_number, scene_scope)`（破坏性）
- [x] （可选）`scene.merge_to_chapter(chapter_number)`

### 2.7 Consistency/Revision（可选）

- [x] `consistency.check(chapter_scope|chapter_numbers)`
- [x] （可选）`revision.generate(chapter_scope|chapter_numbers, mode)`
- [x] （可选）`revision.apply(chapter_number)`（破坏性）
- [x] （可选）`revision.discard(chapter_number)`（破坏性）

### 2.8 Memory/Export（可选）

- [x] `memory.rebuild(chapter_scope|chapter_numbers|None)`
- [x] （可选）`export.chapter(chapter_number, output_path?)`
- [x] （可选）`export.all(output_path?)`

## 3. Implementation（阶段化交付）

### 3.1 Phase A：章节范围精确执行（MVP）✅ 已完成

- [x] 3.1.1 增加 `agent-tooling` 工具定义与参数模型（`ChapterScope`/`force`/`missing_only`）
- [x] 3.1.2 新增 Project 工具：`project.status` / `project.validate_prereqs` / `project.list_artifacts`
- [x] 3.1.3 新增 Settings 工具：`settings.get` / `settings.update`
- [x] 3.1.4 新增 Outline 工具：`outline.generate` / `outline.extend`
- [x] 3.1.5 新增 Chapter Plan 工具：`chapter.plan.generate`（支持 scope/list/None=全量，支持 missing_only）
- [x] 3.1.6 新增 Chapter Text 工具：`chapter.text.generate`（支持 scope/list；默认 enforce 顺序；支持 missing_only）
- [x] 3.1.7 在 `ChatAgent` 中把"章节计划/章节正文 + scope"路由到上述新工具（移除强制降级提示）
- [x] 3.1.8 补齐最小回归测试：范围不会扩张、missing_only 只补缺、force 会覆盖、sequential 阻断跳章

### 3.2 Phase B：一致性/修订/记忆 ✅ 已完成

- [x] 3.2.1 新增 `consistency.check(chapter_scope|chapter_numbers)` 工具
- [x] 3.2.2 新增 `revision.generate/apply/discard` 工具（含破坏性确认）
- [x] 3.2.3 新增 `memory.rebuild(chapter_scope|chapter_numbers|None)` 工具（从 chapters JSON 重建 ledger/Mem0，优雅降级）

### 3.3 Phase C：场景级工具 ✅ 已完成

- [x] 3.3.1 新增 `scene.generate` / `scene.delete` / `scene.merge_to_chapter`
- [x] 3.3.2 定义与 LangGraph 场景子工作流的兼容边界（scene 文件真源与合并策略）

### 3.4 Phase D：维护与导出工具 ✅ 已完成

- [x] 3.4.1 新增 `chapter.plan.delete` / `chapter.text.delete`（破坏性确认）
- [x] 3.4.2 新增 `export.chapter` / `export.all`（复用现有导出能力，但以 Agent 工具形式提供）

## 4. Validation

- [x] 4.1 运行 `openspec validate add-chat-fine-grained-tooling --strict`
- [x] 4.2 若实现阶段开始：补充/更新单元测试与对话式指南（仅 chat 文档，不新增 CLI）
