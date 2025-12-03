## Why

当前主题冲突生成流程需要用户明确输入主题方向，对于创意尚未成熟的用户来说不够友好。用户往往希望 AI 能根据已创建的世界观自动推导出多个风格各异的主题冲突方案供选择，而不是只能接受单一结果。

## What Changes

- **新增多候选生成模式**：根据世界观自动生成多份风格各异的主题冲突候选
- **复用现有配置**：使用 `WORLD_VARIANTS_COUNT` 环境变量控制候选数量（与世界观生成共用）
- **新增候选选择接口**：提供 API 和 CLI 支持用户选择最终使用的主题冲突
- **新增 Pydantic 模型**：`ThemeConflictVariant` 和 `ThemeConflictVariantsResult`
- **更新 init 命令**：在输入主题时提供 AI 生成多候选选项

## Impact

- Affected specs: `theme-conflict-generation`, `configuration`
- Affected code:
  - `novelgen/chains/theme_conflict_chain.py` - 新增变体生成函数
  - `novelgen/models.py` - 新增数据模型
  - `novelgen/config.py` - 新增 `theme_conflict_variants_file` 属性
  - `novelgen/cli.py` - 更新 init 命令，新增 CLI 命令

