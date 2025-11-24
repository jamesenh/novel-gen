# LangGraph 迁移指南

本文档说明如何从传统的顺序编排迁移到基于 LangGraph 的状态工作流。

## 概述

NovelGen 已经迁移到 LangGraph 架构，提供以下增强功能：

- ✅ **状态管理**: 统一的工作流状态，自动管理生成进度
- ✅ **Checkpointing**: 支持暂停和恢复生成流程
- ✅ **条件分支**: 基于一致性检测的智能修订流程
- ✅ **向后兼容**: 保留所有原有 API，无需修改现有代码

## 架构变化

### 之前（顺序编排）

```python
orchestrator = NovelOrchestrator('my_novel')

# 手动调用每个步骤
orchestrator.step1_create_world(user_input)
orchestrator.step2_create_theme_conflict()
orchestrator.step3_create_characters()
# ...
```

### 现在（LangGraph 工作流）

```python
orchestrator = NovelOrchestrator('my_novel')

# 方式1：使用原有 API（向后兼容）
orchestrator.step1_create_world(user_input)
orchestrator.step2_create_theme_conflict()

# 方式2：使用新的工作流 API
state = orchestrator.run_workflow()

# 方式3：从检查点恢复
state = orchestrator.resume_workflow()
```

## 核心概念

### 1. NovelGenerationState

所有生成数据统一存储在状态对象中：

```python
from novelgen.models import NovelGenerationState

state = NovelGenerationState(
    project_name='my_novel',
    project_dir='projects/my_novel',
    world=world_setting,
    theme_conflict=theme_conflict,
    characters=characters_config,
    outline=outline,
    chapters_plan={1: chapter1_plan, 2: chapter2_plan},
    chapters={1: chapter1, 2: chapter2},
    current_step='chapter_generation',
    completed_steps=['load_settings', 'world_creation', ...]
)
```

### 2. 工作流节点

生成流程被拆分为独立的节点：

- `load_settings` - 加载项目设置
- `world_creation` - 生成世界观
- `theme_conflict_creation` - 生成主题冲突
- `character_creation` - 生成角色
- `outline_creation` - 生成大纲
- `chapter_planning` - 规划章节
- `chapter_generation` - 生成章节文本
- `consistency_check` - 一致性检测
- `chapter_revision` - 章节修订（条件触发）

### 3. Checkpointing

工作流自动保存检查点，支持暂停和恢复：

```python
# 运行到某个节点后停止
state = orchestrator.run_workflow(stop_at='outline_creation')

# 稍后从检查点恢复
state = orchestrator.resume_workflow()
```

## 迁移步骤

### 步骤 1: 更新依赖

确保安装了 langgraph：

```bash
uv add langgraph>=0.2.0
# 或
pip install langgraph>=0.2.0
```

### 步骤 2: 选择迁移方式

#### 选项 A: 继续使用现有 API（推荐，零修改）

无需修改代码，NovelOrchestrator 保持完全兼容：

```python
# 现有代码继续工作
orchestrator = NovelOrchestrator('my_novel')
orchestrator.step1_create_world(user_input)
orchestrator.step2_create_theme_conflict()
# ...
```

#### 选项 B: 采用新的工作流 API（推荐新项目）

使用新的 `run_workflow()` 方法：

```python
orchestrator = NovelOrchestrator('my_novel')

# 运行完整工作流
final_state = orchestrator.run_workflow()

# 或者分段运行
state = orchestrator.run_workflow(stop_at='outline_creation')
# 做一些手动调整...
state = orchestrator.resume_workflow()
```

### 步骤 3: 利用 Checkpointing

启用自动恢复功能：

```python
orchestrator = NovelOrchestrator('my_novel')

try:
    # 运行工作流
    state = orchestrator.run_workflow()
except Exception as e:
    print(f"生成失败: {e}")
    # 从最后一个检查点恢复
    state = orchestrator.resume_workflow()
```

### 步骤 4: 验证迁移

运行测试确保功能正常：

```bash
# 运行集成测试
uv run python tests/test_langgraph_integration.py

# 运行 checkpointing 测试
uv run python tests/test_checkpointing.py
```

## 新功能使用

### 1. 查看工作流图

```python
from novelgen.runtime.workflow import create_novel_generation_workflow

workflow = create_novel_generation_workflow()

# 生成 Mermaid 图
mermaid_code = workflow.get_graph().draw_mermaid()
print(mermaid_code)
```

### 2. 查看检查点历史

```python
config = {"configurable": {"thread_id": "my_novel"}}
checkpoints = list(workflow.get_state_history(config))

for i, checkpoint in enumerate(checkpoints):
    print(f"检查点 {i}: {checkpoint.values['current_step']}")
```

### 3. 状态导出/导入

```python
from novelgen.runtime.state_sync import (
    state_to_json_files,
    json_files_to_state
)

# 导出状态到 JSON
saved_files = state_to_json_files(state)

# 从 JSON 加载状态
restored_state = json_files_to_state('projects/my_novel')
```

## 性能影响

LangGraph 迁移对性能的影响：

- ✅ **内存**: 轻微增加（~5-10MB，用于状态管理）
- ✅ **速度**: 几乎无影响（节点包装器开销 <1ms）
- ✅ **存储**: 额外的检查点数据（~1-5MB per project）

## 故障排除

### 问题：检查点未保存

**原因**: MemorySaver 只保存在内存中

**解决**: 使用 SqliteSaver 或其他持久化 checkpointer（未来版本）

### 问题：状态与 JSON 不同步

**原因**: 手动修改了 JSON 文件

**解决**: 调用 `sync_state_from_json()`：

```python
from novelgen.runtime.state_sync import sync_state_from_json

updated_state = sync_state_from_json(current_state)
```

### 问题：工作流卡住

**原因**: 节点执行失败但未正确处理

**解决**: 检查 `state.error_messages` 和 `state.failed_steps`：

```python
if state.failed_steps:
    print(f"失败的步骤: {state.failed_steps}")
    print(f"错误信息: {state.error_messages}")
```

## 最佳实践

1. **优先使用 `run_workflow()`**: 新项目推荐使用工作流 API
2. **定期检查点**: 长时间运行的生成任务建议设置中间检查点
3. **错误处理**: 捕获异常并使用 `resume_workflow()` 恢复
4. **状态验证**: 使用 `validate_state_json_consistency()` 确保一致性
5. **测试覆盖**: 为自定义节点编写测试

## 下一步

- 查看 `examples/resume_workflow.py` 了解检查点恢复示例
- 阅读 LangGraph 官方文档: https://langchain-ai.github.io/langgraph/
- 探索自定义节点和条件分支

## 支持

如有问题，请：
1. 查看测试用例: `tests/test_langgraph_*.py`
2. 检查日志输出（启用 `verbose=True`）
3. 提交 Issue 到项目仓库
