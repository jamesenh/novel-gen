# Verbose 模式使用说明

## 概述

Verbose 模式是 NovelGen 的一个强大功能，允许你在 AI 调用时查看：

1. **完整的提示词**（包含格式化后嵌入的字符）
2. **LLM 响应的总时间**
3. **Token 使用情况**（提示词 Token、生成 Token、总 Token）

## 如何启用

### 方法 1: 通过 NovelOrchestrator

在创建 `NovelOrchestrator` 时，设置 `verbose=True`：

```python
from novelgen.runtime.orchestrator import NovelOrchestrator

# 启用详细日志
orchestrator = NovelOrchestrator(
    project_name="my_novel",
    verbose=True  # 启用详细模式
)

# 正常调用各个步骤
world = orchestrator.step1_create_world("一个修真世界，有五大宗门")
```

### 方法 2: 直接调用 Chain 函数

每个 chain 函数都支持 `verbose` 参数：

```python
from novelgen.chains.world_chain import generate_world
from novelgen.chains.theme_conflict_chain import generate_theme_conflict
from novelgen.chains.characters_chain import generate_characters
from novelgen.chains.outline_chain import generate_outline
from novelgen.chains.chapters_plan_chain import generate_chapter_plan
from novelgen.chains.scene_text_chain import generate_scene_text

# 启用详细日志
world = generate_world("一个修真世界", verbose=True)
theme = generate_theme_conflict(world, "个人奋斗", verbose=True)
characters = generate_characters(world, theme, verbose=True)
outline = generate_outline(world, theme, characters, verbose=True)
```

## 输出示例

当启用 verbose 模式时，你会看到类似以下的输出：

```
================================================================================
🤖 LLM调用开始
================================================================================

📝 完整提示词：
--------------------------------------------------------------------------------

[对话 1]

[System]
你是一位专业的小说世界观设计师。

你的任务：根据用户提供的简要描述，设计一个完整的小说世界观。

输入说明：用户会提供世界的基本设定（如类型、风格等）

输出格式：{format_instructions}

注意事项：
1. 世界观要自洽、有逻辑
2. 细节要丰富，但不冗余
3. 要为后续的故事发展留出空间
4. 严格按照JSON格式输出，不要使用Markdown包裹

[HumanMessage]
一个修真世界，有五大宗门，主角从小宗门崛起
--------------------------------------------------------------------------------

================================================================================
✅ LLM调用完成
================================================================================

⏱️  响应时间: 3.45 秒

🎯 Token使用情况:
  • 提示词Token: 1234
  • 生成Token: 567
  • 总计Token: 1801

================================================================================
```

## 使用场景

### 1. 调试提示词

当生成结果不符合预期时，查看完整提示词可以帮助你：
- 确认输入数据是否正确传递
- 检查格式化是否正确
- 理解 AI 看到的完整上下文

### 2. 优化性能

通过查看响应时间和 Token 使用情况：
- 识别耗时较长的步骤
- 评估成本（基于 Token 使用量）
- 优化提示词长度

### 3. 学习和理解

通过查看完整提示词：
- 学习 LangChain 如何构造提示
- 了解 JSON Schema 如何嵌入提示词
- 理解系统的工作原理

## 实际示例

### 示例 1: 查看世界观生成的完整提示词

```python
from novelgen.runtime.orchestrator import NovelOrchestrator

orchestrator = NovelOrchestrator(project_name="test", verbose=True)
world = orchestrator.step1_create_world("赛博朋克世界，2077年的东京")
```

### 示例 2: 测试单个 chain 的性能

```python
from novelgen.chains.characters_chain import generate_characters
from novelgen.models import WorldSetting, ThemeConflict

# 假设已有 world 和 theme_conflict
characters = generate_characters(world, theme_conflict, verbose=True)
# 查看输出的 Token 使用情况和响应时间
```

### 示例 3: 在测试函数中使用

```python
def test_chapter_plan():
    """测试章节计划生成并查看详细日志"""
    orchestrator = NovelOrchestrator(
        project_name="test_world_chain",
        verbose=True  # 启用详细日志
    )
    chapter_plan = orchestrator.step5_create_chapter_plan(chapter_number=1)
    print(f"生成的场景数: {len(chapter_plan.scenes)}")

if __name__ == "__main__":
    test_chapter_plan()
```

## 技术实现

Verbose 模式通过 LangChain 的 `BaseCallbackHandler` 实现：

- **VerboseCallbackHandler**: 自定义回调处理器
  - `on_chat_model_start`: 捕获并打印提示词
  - `on_llm_end`: 记录响应时间和 Token 使用情况
  - `on_llm_error`: 处理错误情况

所有 chain 函数都通过 `get_llm(verbose=True)` 来启用这个功能。

## 注意事项

1. **日志量大**: Verbose 模式会产生大量输出，建议仅在调试或分析时使用
2. **性能影响**: 打印大量日志可能会略微影响性能
3. **隐私**: 提示词可能包含敏感数据，注意不要在公开环境中暴露日志
4. **生产环境**: 建议在生产环境中设置 `verbose=False`（默认值）

## 快速开始

在 `main.py` 中已经提供了示例：

```python
# 运行测试函数（已启用 verbose）
python main.py

# 测试函数默认启用了 verbose=True
# 你可以直接看到详细的输出
```

## 总结

Verbose 模式是一个强大的开发和调试工具，帮助你：
- ✅ 理解 AI 的输入输出
- ✅ 优化提示词和性能
- ✅ 监控成本（Token 使用）
- ✅ 学习系统工作原理

建议在开发和测试阶段充分利用这个功能！

