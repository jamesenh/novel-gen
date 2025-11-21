# Design: Simplify Consistency Auto-Fix Logic

## Context
当前一致性检测系统要求 LLM 对每个问题返回两个字段：
1. `can_auto_fix: bool` - 是否可以自动修复
2. `fix_instructions: Optional[str]` - 如何修复

这导致了逻辑冗余：
- 如果模型能给出修复指令（`fix_instructions`），说明它认为可以修复
- 如果模型认为不可修复，就不应该给出修复指令
- 让模型同时做两个判断增加了认知负担，可能导致不一致（如 `can_auto_fix=True` 但 `fix_instructions=None`）

## Goals
- **简化数据模型**：移除冗余的 `can_auto_fix` 字段
- **简化 prompt**：减少模型需要理解和输出的字段
- **统一判断标准**：`fix_instructions` 的存在性即为可修复性的唯一标准
- **保持向后兼容**：不影响已有数据的读取

## Non-Goals
- 不改变修订链的行为或输出格式
- 不影响 revision_policy 的配置和执行逻辑
- 不修改 ConsistencyReport 的其他字段

## Key Decisions

### Decision 1: 移除 `can_auto_fix` 而非标记为 deprecated
**选择**：直接从 Pydantic 模型中移除 `can_auto_fix` 字段

**理由**：
- `ConsistencyIssue` 是内部数据模型，不是公开 API
- `consistency_reports.json` 是运行时产物，不是长期存储
- Pydantic 默认忽略模型中未定义的额外字段，读取旧数据不会报错
- 清理冗余字段比维护 deprecated 标记更直接

**替代方案考虑**：
- ❌ 保留字段但标记 `deprecated=True`：增加模型复杂度，延长清理周期
- ❌ 同时保留两个字段：不解决根本问题

### Decision 2: 简化 prompt 而非保留双重判断
**选择**：更新 prompt，只要求模型在可修复时提供 `fix_instructions`

**理由**：
- 减少模型输出结构的复杂度
- prompt 更清晰："只为可修复问题提供 fix_instructions，不可修复的问题留空"
- 避免模型内部判断不一致的风险

### Decision 3: 修订判断逻辑统一为 `if issue.fix_instructions`
**选择**：在所有判断可修复问题的地方，统一使用 `if issue.fix_instructions` 或 `if issue.fix_instructions and issue.fix_instructions.strip()`

**理由**：
- 单一真相来源（Single Source of Truth）
- 代码更简洁可读
- 空字符串也不应被视为有效的修复指令

## Migration Plan

1. **代码变更顺序**：
   ```
   models.py (移除字段)
     ↓
   consistency.py (更新 prompt)
     ↓
   orchestrator.py (更新判断逻辑和日志)
     ↓
   全局搜索清理残留引用
   ```

2. **数据兼容性**：
   - 旧的 `consistency_reports.json` 包含 `can_auto_fix` 字段
   - Pydantic 读取时会自动忽略未定义字段
   - 新生成的报告将不包含该字段
   - 不需要迁移脚本

3. **回滚方案**：
   - 如果需要回滚，恢复 `can_auto_fix` 字段定义
   - 由于 `fix_instructions` 判断逻辑已足够，回滚不会影响功能

## Risks & Trade-offs

### Risk 1: 模型可能给出空或无意义的 fix_instructions
**缓解措施**：
- 在判断逻辑中加入 `issue.fix_instructions.strip()` 检查
- 在 prompt 中明确要求："如果无法修复，不要提供 fix_instructions；如果可以修复，必须给出具体可执行的指令"

## Open Questions
- ❌ 无待解决问题
