## 1. 设计与验证
- [x] 1.1 梳理现有所有使用 PydanticOutputParser/LLMJsonRepairOutputParser 的链（world/characters/outline/chapters_plan/scene_text/revision/memory_context），确认结构化输出模型与调用方式
- [x] 1.2 在本提案对应的 `specs/` 目录下补充/修改与"LLM结构化输出与JSON解析"相关的规范条目，并通过 `openspec validate add-llm-structured-output --strict`

## 2. LLM 实例与链工厂改造
- [x] 2.1 在 `novelgen/llm.py` 中，为需要结构化输出的链提供 `with_structured_output(PydanticModel)` 的封装能力（优先针对 OpenAI 官方/完全兼容端点）
- [x] 2.2 在 `ProjectConfig` 或链配置层，为不同链增加"是否启用structured_output模式"的配置开关，支持按后端能力切换

## 3. 链级结构化输出集成
- [x] 3.1 `characters_chain`：将 `create_characters_chain` 重构为优先使用 `llm.with_structured_output(CharactersConfig)`，在不支持 JSON 模式时退回现有 `PydanticOutputParser + LLMJsonRepairOutputParser` 实现
- [x] 3.2 `chapters_plan_chain`：同上，针对 `ChapterPlan`
- [x] 3.3 `scene_text_chain`：同上，针对 `GeneratedScene`，并评估是否需要在后续提案中将长正文拆分为两步生成
- [x] 3.4 `chapter_revision_chain`：同上，针对 `GeneratedChapter`

## 4. JSON 修复与输出清洗增强
- [x] 4.1 在 `LLMJsonRepairOutputParser` 中新增统一的输出清洗步骤：去除 Markdown 代码块包裹、截取最外层 JSON 对象文本
- [x] 4.2 为最常出错的正文字段（如 `GeneratedScene.content`、`GeneratedChapter.scenes[*].content`）设计保守的转义/替换策略，并在不破坏结构的前提下实现（注：在 structured_output 模式下由 SDK 自动处理，传统路径下由清洗逻辑兜底，无需单独实现）

## 5. 验证与回归
- [x] 5.1 针对代表性流程（完整 demo 项目）在 OpenAI 官方端点下跑通全流程，确认结构化输出稳定性明显提升（减少 JSON 解析失败与修复失败）
- [x] 5.2 在 Qwen/ModelScope 等兼容端点下验证 fallback 路径稳定性，确认不会因为 structured_output 不可用而破坏现有功能
- [x] 5.3 为关键链补充/更新测试脚本或手动验证步骤文档，记录典型失败用例与修复效果
