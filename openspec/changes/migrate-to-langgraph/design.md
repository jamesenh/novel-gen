# LangGraph Migration Design

## Context

NovelGen 当前使用 `NovelOrchestrator` 类进行顺序编排，每个生成步骤作为独立方法调用。这种设计在 MVP 阶段简单有效，但随着以下需求增长而显现局限：

1. **长期记忆需求**：后续章节需要引用前文细节（角色状态、事件、未解之谜），现有架构需要手动传递和查询记忆
2. **可恢复性需求**：长篇小说生成可能耗时数小时，中断后需要从断点恢复而非重新开始
3. **复杂工作流**：未来可能需要条件分支（如一致性检测后的自动修订）、并行生成（多章节并发）、子工作流嵌套

**约束条件**：
- 必须保持现有 6 步生成管道的完整性
- 不能破坏现有项目的 JSON 文件结构
- 学习曲线需要可控，开发者能快速上手
- 性能不能显著下降

**关键决策点**：
- 是否完全替换 `NovelOrchestrator`？
- LangGraph 状态模型如何设计？
- 如何与现有的数据库、向量存储集成？
- Checkpointing 使用什么持久化后端？

## Goals / Non-Goals

### Goals
- ✅ 将 6 步生成流程迁移到 LangGraph `StateGraph`
- ✅ 实现工作流状态的统一管理（包括记忆、上下文）
- ✅ 支持检查点（checkpointing），允许暂停/恢复生成
- ✅ 保持现有 API 的向后兼容性（`NovelOrchestrator` 作为 facade）
- ✅ 提供工作流可视化能力（通过 `.draw()` 或 Mermaid 图）
- ✅ 保持现有 JSON 持久化格式不变

### Non-Goals
- ❌ 重写现有的 LangChain chains（仅添加节点包装器）
- ❌ 改变数据库或向量存储的底层实现
- ❌ 实现复杂的并行生成（留给后续 phase）
- ❌ 迁移所有现有项目（提供选择性迁移路径）

## Decisions

### 1. LangGraph 状态模型设计

**决策**：使用单一 `NovelGenerationState` Pydantic 模型，包含所有生成阶段的状态字段。

**理由**：
- LangGraph 推荐使用 TypedDict 或 Pydantic 模型定义状态
- 单一状态模型更容易管理和调试
- 可以通过字段分组逻辑上区分不同阶段的数据

**状态模型结构**：
```python
class NovelGenerationState(BaseModel):
    # 项目元信息
    project_name: str
    project_dir: str
    
    # 配置
    settings: Optional[Settings] = None
    
    # 6步生成结果
    world: Optional[WorldSetting] = None
    theme_conflict: Optional[ThemeConflict] = None
    characters: Optional[CharactersConfig] = None
    outline: Optional[Outline] = None
    chapters_plan: Dict[int, ChapterPlan] = {}  # chapter_number -> plan
    chapters: Dict[int, GeneratedChapter] = {}  # chapter_number -> chapter
    
    # 记忆与上下文
    chapter_memories: List[ChapterMemoryEntry] = []
    entity_states: Dict[str, EntityStateSnapshot] = {}  # entity_id -> state
    recent_context: List[str] = []  # 最近 N 章的摘要（用于传递给下一步）
    
    # 工作流控制
    current_step: str = "init"  # 当前步骤标识
    completed_steps: List[str] = []  # 已完成步骤列表
    failed_steps: List[str] = []  # 失败步骤列表
    
    # 持久化管理器引用（通过 context 传递，不序列化）
    db_manager: Optional[Any] = None
    vector_manager: Optional[Any] = None
```

### 2. 节点包装器设计

**决策**：为每个 LangChain chain 创建轻量级节点函数，而非修改 chain 本身。

**理由**：
- 保持 chains 的独立性和可测试性
- 节点函数负责：状态提取 → chain 调用 → 状态更新
- 避免 LangChain 和 LangGraph 的耦合

**节点函数模式**：
```python
def world_creation_node(state: NovelGenerationState) -> Dict:
    """世界观生成节点"""
    # 1. 从状态提取输入
    settings = state.settings
    
    # 2. 调用现有 chain
    world = generate_world(settings_dict=settings.model_dump())
    
    # 3. 更新状态
    return {
        "world": world,
        "current_step": "world_creation",
        "completed_steps": state.completed_steps + ["world_creation"]
    }
```

### 3. Checkpointing 策略

**决策**：使用 LangGraph 的 `MemorySaver`（内存后端）作为初期实现，后续可扩展到 SQLite 或 Redis。

**理由**：
- `MemorySaver` 是 LangGraph 的默认检查点实现，零配置
- 对于单机生成场景足够使用
- 后续可通过实现 `BaseCheckpointSaver` 接口扩展到持久化后端

**检查点配置**：
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
workflow = graph.compile(checkpointer=checkpointer)
```

### 4. 向后兼容策略

**决策**：保留 `NovelOrchestrator` 类，重构为 LangGraph 工作流的 facade。

**理由**：
- 最小化用户代码的破坏性变更
- 允许现有项目逐步迁移
- `NovelOrchestrator` 内部调用 LangGraph 工作流，但保持原有方法签名

**实现方案**：
```python
class NovelOrchestrator:
    def __init__(self, project_name: str, ...):
        # 初始化 LangGraph 工作流
        self.workflow = create_novel_generation_workflow(...)
        
    def step1_create_world(self, force=False):
        # 调用 LangGraph 工作流的 world_creation 节点
        result = self.workflow.invoke({"current_step": "world_creation"})
        return result["world"]
```

### 5. 工作流图结构

**决策**：使用线性主流程 + 条件分支（用于修订）的混合结构。

**工作流定义**：
```
START 
  → load_settings
  → world_creation
  → theme_conflict_creation
  → character_creation
  → outline_creation
  → chapters_planning (循环)
  → chapter_generation (循环)
    → consistency_check
    → [条件分支] revision_needed?
       ├─ YES → chapter_revision → 更新 state
       └─ NO → 继续下一章
  → END
```

**条件边实现**：
```python
def should_revise_chapter(state: NovelGenerationState) -> str:
    """判断是否需要修订"""
    if state.consistency_report and state.consistency_report.has_fixable_issues():
        return "revise"
    return "continue"

graph.add_conditional_edges(
    "consistency_check",
    should_revise_chapter,
    {
        "revise": "chapter_revision",
        "continue": "next_chapter"
    }
)
```

## Alternatives Considered

### 替代方案 1：保持现有编排器，仅添加记忆管理层
- **优点**：实现成本低，不改变现有架构
- **缺点**：无法解决可恢复性和复杂工作流需求，技术债累积
- **结论**：❌ 不足以支撑长期发展

### 替代方案 2：使用其他工作流框架（如 Airflow、Prefect）
- **优点**：成熟的工作流引擎，功能强大
- **缺点**：与 LangChain 集成度低，学习成本高，过度工程化
- **结论**：❌ 不适合 LLM 应用场景

### 替代方案 3：自研状态机框架
- **优点**：完全可控，定制化强
- **缺点**：重复造轮子，维护成本高
- **结论**：❌ LangGraph 已提供所需能力

## Risks / Trade-offs

### 风险 1：学习曲线增加
- **影响**：开发者需要学习 LangGraph 概念（StateGraph、节点、边）
- **缓解**：提供完整的迁移文档、示例代码和可视化工具

### 风险 2：性能开销
- **影响**：LangGraph 的状态管理和检查点可能引入轻微性能开销
- **缓解**：初期使用 `MemorySaver`（零序列化开销），后续按需优化

### 风险 3：依赖锁定
- **影响**：进一步绑定到 LangChain 生态
- **缓解**：LangGraph 是开源框架，关键逻辑仍保持在 chains 中，可替换性强

### Trade-off：复杂性 vs. 可扩展性
- **牺牲**：代码复杂度短期增加（节点适配器、状态模型）
- **收益**：长期可扩展性显著提升（条件分支、并行、子工作流）

## Migration Plan

### Phase 1: 基础设施搭建（本次变更）
1. 添加 langgraph 依赖
2. 定义 `NovelGenerationState` 状态模型
3. 实现 `workflow.py` 主工作流
4. 为 6 个核心 chains 创建节点包装器
5. 重构 `NovelOrchestrator` 为 facade
6. 添加单元测试和集成测试

### Phase 2: Checkpointing 增强（未来）
1. 实现 SQLite 检查点后端
2. 添加工作流恢复 CLI
3. 支持长时间运行任务的断点续传

### Phase 3: 高级工作流（未来）
1. 并行章节生成
2. 动态大纲调整（基于生成结果反馈）
3. 多智能体协作（如专门的角色一致性检查 agent）

### 回滚策略
- 保留 `NovelOrchestrator` 原有逻辑的 git tag（如 `v0.1.0-pre-langgraph`）
- 如 LangGraph 引入严重问题，可通过配置项切换回传统编排器

## Open Questions

1. **问题**：是否需要在 Phase 1 立即支持并行章节生成？
   - **建议**：否，先验证基础架构，Phase 2 再引入并行

2. **问题**：Checkpointing 的持久化后端选择（SQLite vs Redis vs 文件）？
   - **建议**：Phase 1 使用 `MemorySaver`，Phase 2 根据实际需求选择 SQLite（单机）或 Redis（分布式）

3. **问题**：如何处理现有项目的迁移（已有 JSON 文件）？
   - **建议**：提供迁移脚本，从 JSON 重建 LangGraph 状态，无缝对接新工作流
