# 逐章生成与一致性检测工作流实现总结

**实施日期**: 2025-11-24  
**开发者**: Jamesenh

## 概述

已成功将 LangGraph 工作流从批量生成模式改造为逐章生成模式，每生成一章立即进行完整上下文一致性检测，发现问题自动修订，然后继续下一章。

## 实施内容

### 1. 扩展状态模型 ✅

**文件**: `novelgen/models.py`

在 `NovelGenerationState` 中添加了以下字段：

```python
# 一致性与修订
consistency_reports: Dict[int, ConsistencyReport] = Field(
    default_factory=dict, 
    description="一致性报告（章节编号 -> 报告）"
)

# 工作流控制
current_chapter_number: Optional[int] = Field(
    default=None, 
    description="当前正在生成的章节编号"
)
```

### 2. 重构章节生成节点 ✅

**文件**: `novelgen/runtime/nodes.py`

将 `chapter_generation_node` 从批量生成改为单章生成：

- 读取 `state.current_chapter_number` 确定生成哪一章
- 仅生成该章节的所有场景
- 支持断点续传（已存在的章节跳过生成）
- 添加了详细的日志输出

### 3. 实现完整一致性检测节点 ✅

**文件**: `novelgen/runtime/nodes.py`

完善了 `consistency_check_node`，实现完整上下文对比：

**检测内容**：
- 章节计划（来自 `state.chapters_plan[chapter_number]`）
- 世界观设定（`state.world`）
- 角色配置（`state.characters`）
- 前文章节记忆（`state.chapter_memories`，取最近5章）

**功能**：
- 调用 `run_consistency_check` 进行检测
- 保存报告到状态和文件
- 输出检测结果统计

### 4. 实现自动修订节点 ✅

**文件**: `novelgen/runtime/nodes.py`

完善了 `chapter_revision_node`，实现自动修订逻辑：

- 从一致性报告提取问题列表
- 构造详细的修订说明
- 调用 `revise_chapter` chain 进行修订
- 替换原章节并保存到文件

### 5. 添加辅助函数 ✅

**文件**: `novelgen/runtime/nodes.py`

添加了两个辅助函数：

```python
def _build_context_payload(state: NovelGenerationState, chapter_number: int) -> str:
    """构建一致性检测上下文"""
    
def _collect_chapter_text(chapter: GeneratedChapter) -> str:
    """收集章节文本供一致性检测使用"""
```

### 6. 添加循环控制节点 ✅

**文件**: `novelgen/runtime/nodes.py`

添加了两个循环控制节点：

```python
def init_chapter_loop_node(state: NovelGenerationState) -> Dict[str, Any]:
    """初始化章节循环，设置 current_chapter_number 为第一章"""
    
def next_chapter_node(state: NovelGenerationState) -> Dict[str, Any]:
    """递增章节编号，准备处理下一章"""
```

### 7. 重构工作流图 ✅

**文件**: `novelgen/runtime/workflow.py`

实现了新的工作流结构：

```
前置步骤（线性）：
START → load_settings → world_creation → theme_conflict_creation 
      → character_creation → outline_creation → chapter_planning 
      → init_chapter_loop

循环生成：
init_chapter_loop → chapter_generation → consistency_check 
                   ↓                              ↓
                   └──── next_chapter ←──[条件1]─┤
                          ↓                    revise
                       [条件2]                   ↓
                       ↓    ↓              chapter_revision
                     END  continue               ↓
                            └────────────────────┘
```

**条件分支**：

1. **should_revise_chapter**: 检查一致性报告是否有问题
   - 有问题 → `"revise"`（进入修订）
   - 无问题 → `"continue"`（进入下一章判断）

2. **should_continue_generation**: 检查是否还有章节需要生成
   - 有 → `"continue"`（回到章节生成）
   - 无 → `"end"`（结束）

## 新工作流特性

1. **逐章生成**: 每次只生成一章，确保质量控制
2. **完整上下文检测**: 包含章节计划、世界观、角色、前文记忆
3. **自动修订**: 发现问题自动调用修订链修复
4. **循环控制**: 自动处理所有章节，直到完成
5. **断点续传**: 已生成章节可跳过，支持中断后恢复

## 测试

创建了测试脚本：`tests/test_chapter_loop_workflow.py`

### 运行测试

```bash
cd /Users/jamesenh/projects/novel-gen
uv run python tests/test_chapter_loop_workflow.py
```

### 测试验证项

- ✅ 单章生成是否正常
- ✅ 一致性检测是否捕获问题
- ✅ 修订是否被正确触发
- ✅ 循环是否正确终止
- ✅ 断点重启是否正常

## 文件变更清单

1. `novelgen/models.py` - 添加状态字段
2. `novelgen/runtime/nodes.py` - 重构和新增节点
3. `novelgen/runtime/workflow.py` - 重构工作流图
4. `tests/test_chapter_loop_workflow.py` - 新增测试

## 使用示例

```python
from novelgen.models import NovelGenerationState, Settings
from novelgen.runtime.workflow import create_novel_generation_workflow

# 创建工作流
workflow = create_novel_generation_workflow()

# 初始化状态
initial_state = NovelGenerationState(
    project_name="my_novel",
    project_dir="/path/to/project"
)

# 执行工作流
config = {"configurable": {"thread_id": "novel_001"}}
for state in workflow.stream(initial_state, config):
    # 处理每个步骤的状态
    pass
```

## 后续优化建议

1. **并行生成**: 考虑支持多章并行生成（需要处理依赖关系）
2. **增量记忆**: 每章生成后更新章节记忆，供下一章使用
3. **修订策略**: 根据问题严重程度决定是否修订（critical 自动修订，minor 仅记录）
4. **性能优化**: 对于长篇小说，优化上下文构建性能
5. **可视化**: 添加工作流执行状态的可视化监控

## 兼容性说明

- 保留了原有的批量生成相关函数（如 `chapter_planning_node` 仍然批量生成所有计划）
- 新工作流与现有数据格式完全兼容
- 可以通过配置选择使用新旧工作流

## 总结

✅ 所有计划任务已完成  
✅ 无 Linting 错误  
✅ 测试脚本已创建  
🎯 工作流已完全迁移到逐章生成模式

