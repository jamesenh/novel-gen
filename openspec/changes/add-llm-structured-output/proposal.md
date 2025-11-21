## Why
当前各个链（角色生成、章节计划、场景文本、章节修订等）在调用 LLM 时，主要通过：
- 在 Prompt 中内嵌 PydanticOutputParser 生成的 `format_instructions` 文本
- 依赖 LLM 自觉遵守 JSON schema 和转义规范
- 在解析失败时使用自定义 `LLMJsonRepairOutputParser` 再调用一次 LLM 进行 JSON 修复

在长文本、复杂 JSON 结构、混合创作与结构输出的场景下，这种“纯提示词约束 + 事后修复”的方案仍然会概率性失败，典型问题包括：
- JSON 中包含未转义的英文双引号导致解析失败
- 输出结构与 `format_instructions` 描述的 Pydantic 模型不完全一致

同时，LangChain 1.x 已提供更稳健的结构化输出能力（如 `with_structured_output`，以及基于 OpenAI JSON 模式 / 工具调用的协议级约束），当前实现尚未利用这些能力。

## What Changes
- 为支持 JSON 模式 / 工具调用的 LLM 后端（如 OpenAI 官方端点），在链级引入基于 `with_structured_output(PydanticModel)` 的结构化输出方案：
  - 角色生成链：`CharactersConfig`
  - 章节计划链：`ChapterPlan`
  - 场景文本链：`GeneratedScene`
  - 章节修订链：`GeneratedChapter`
- 对于不支持 JSON 模式的兼容后端（如部分 Qwen / ModelScope 兼容接口），保留现有 `PydanticOutputParser + LLMJsonRepairOutputParser` 路径作为兜底实现，并在解析前增加轻量级输出清洗：
  - 去除 Markdown 代码块包裹（如 ```json ... ```）
  - 截取最外层 JSON 对象文本
- 为长正文场景（尤其是场景文本与章节修订）预留后续演进空间：
  - 在规范层明确允许将“结构信息”和“长正文内容”拆分为两步生成，并在代码侧用 Pydantic 模型组装最终 JSON，减少对 LLM 手动转义的依赖。

## Impact
- **Affected specs / capabilities**：
  - LLM 调用与结构化输出规范（现有 specs 中涉及链输出 JSON 结构与错误修复约束的部分）
- **Affected code (high-level)**：
  - `novelgen/llm.py`：为链提供可配置的 structured_output / 非 structured_output LLM 实例
  - `novelgen/chains/characters_chain.py`
  - `novelgen/chains/chapters_plan_chain.py`
  - `novelgen/chains/scene_text_chain.py`
  - `novelgen/chains/chapter_revision_chain.py`
  - `novelgen/chains/output_fixing.py`：在现有 JSON 修复解析器中增加统一的输出清洗逻辑
- **Non-goals（本次不做）**：
  - 不更改项目既有的 6 步生成流程与链划分
  - 不新增外部依赖，仅在 LangChain 1.x 现有能力范围内演进
  - 不一次性重构为“结构 + 正文完全两步生成”，仅在规范中预留方向，后续根据需要追加提案
