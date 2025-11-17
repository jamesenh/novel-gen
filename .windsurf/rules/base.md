---
trigger: always_on
---

## 项目哲学（必须遵守）

1. 模块化设计：每一步小说生成流程都必须是一个独立 chain。
2. 结构化输出优先：所有链的输出必须对应一个 Pydantic 模型。
3. 可迭代可修改：每个 chain 必须可以独立运行，不依赖 UI。
4. 无状态，但接受输入文件：链之间只通过 JSON 文件 (projects/*) 传递信息。
5. LangChain 是调度工具，不负责业务模型：
6. 数据结构（世界观/角色/大纲）必须放在 models.py
7. LangChain 不能内嵌业务结构，避免耦合
8. Prompt 要高度结构化：避免使用自由输出，要尽量使用 JSON schema 约束。
9. 每个 chain 的逻辑是：
    Input → PromptTemplate → LLM → OutputParser → Python对象 → 写入JSON

## 项目结构要求

所有代码必须写在以下模块结构中：

```
novelgen/
  models.py
  config.py
  llm.py
  chains/
    world_chain.py
    theme_conflict_chain.py
    characters_chain.py
    outline_chain.py
    chapters_plan_chain.py
    scene_text_chain.py
  runtime/
    orchestrator.py
    summary.py
    revision.py
```

## models.py 内必须定义

- Settings
- WorldSetting
- ThemeConflict
- Character
- CharactersConfig
- Outline
- ChapterPlan
- ScenePlan
- GeneratedScene
均使用 Pydantic BaseModel。

## LangChain 代码规范

1. 所有链必须使用：
    - ChatPromptTemplate
    - LLMChain 或 RunnableSequence
    - PydanticOutputParser 或 with_structured_output
2. 所有提示必须包含：
    - 「你的任务」
    - 「输入说明」
    - 「输出格式（JSON schema）」
    - 「注意事项」
3. 输出严格使用 JSON，不允许 Markdown 包裹 JSON。
4. 使用langchain 1.0+的版本的语法

## 项目运行

1. 使用uv,不要直接使用系统默认的python