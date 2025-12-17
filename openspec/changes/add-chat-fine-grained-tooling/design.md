## 设计目标

为 `ng chat` 提供一组**可组合、可控范围、可复用落盘语义**的细粒度工具，使 Agent 能够以最小必要操作完成章节计划/正文的生成与补齐，并为后续一致性/修订/记忆等精细操作预留接口。

## 核心原则

1. **JSON 为真源**：工具以 `projects/<id>/` 下 JSON 文件为事实来源与复用依据。
2. **显式范围（Scope-first）**：章节相关工具必须接受显式 `ChapterScope` 或 `list[int]`；禁止隐式扩张。
3. **幂等与可复用**：在 `force=false` 时，已存在且可解析的文件应跳过生成并复用。
4. **前置依赖可解释**：缺失前置时返回结构化 `missing_deps`，由 Agent 进行计划与确认。
5. **与全流程兼容**：不破坏 `ng run/resume`；工具落盘的产物应被后续工作流正确识别并跳过重复生成。

## 分层结构

- **Agent 层**（`novelgen/agent/chat.py`）
  - 负责解析意图、回显、确认、把请求映射为 1..N 次工具调用序列。
- **工具层**（`novelgen/tools/*_tools.py`）
  - 提供细粒度、确定性、可测试的操作：get/update/generate/ensure/delete/check/apply 等。
- **运行时原语层**（`novelgen/runtime/*` 或独立 helper）
  - 提供可被工具复用的“章节范围执行原语”（例如读取 outline、生成某章 plan、生成某章 scenes→chapter），避免工具层直接依赖 LangGraph 全量执行。

## 工具命名与参数约定（摘要）

- `settings.get() -> {settings}`
- `settings.update(patch, persist=true) -> {settings}`
- `outline.generate(num_chapters|initial_chapters|max_chapters, force=false)`
- `outline.extend(additional_chapters, force=false)`
- `chapter.plan.generate(chapter_scope|chapter_numbers|None, force=false, missing_only=true)`
- `chapter.text.generate(chapter_scope|chapter_numbers, force=false, missing_only=true, sequential=true)`

## 顺序约束（chapter.text）

章节正文默认 **sequential=true**，避免“跳章生成”导致上下文与记忆不一致：

- 若请求生成 `[5]` 但 `[1..4]` 缺失：
  - 工具返回 `blocked_by_missing=[1..4]`，不生成第 5 章
  - Agent 应提示用户选择：顺序补齐到第 5 章 / 取消 /（可选）强制跳章但标记风险

## 与 LangGraph/检查点的关系

- 工具层不直接操作 LangGraph 检查点数据库（避免复杂度与状态漂移）。
- 通过文件落盘实现“事实推进”，后续 `ng run/resume` 通过文件存在性与状态推断逻辑识别已完成产物并跳过。
- 对于场景级工具（Phase C），需要明确 scene 文件与 chapter 文件的合并/覆盖策略，避免与场景子工作流冲突。

