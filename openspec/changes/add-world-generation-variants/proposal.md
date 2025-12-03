## Why

当前世界观生成流程要求用户提供完整的世界描述，对于创意尚未成熟的用户来说门槛较高。用户往往只有模糊的想法（如"修仙世界"或"赛博朋克"），需要 AI 帮助扩展和具体化。同时，用户希望能从多个风格各异的世界观中选择最符合心意的方案，而不是只能接受单一结果。

## What Changes

- **新增多候选生成模式**：根据简短提示生成多份风格各异的世界观候选
- **新增配置支持**：通过环境变量 `WORLD_VARIANTS_COUNT` 控制默认候选数量（默认3）
- **新增 AI 扩写模式**：将用户的简短描述扩展为完整的世界观描述
- **新增候选选择接口**：提供 API 和 CLI 支持用户选择最终使用的世界观
- **新增 Pydantic 模型**：`WorldVariant` 和 `WorldVariantsResult` 用于多候选结果
- **修改现有 world_chain**：增加变体生成函数，保持原有单一生成向后兼容

## Impact

- Affected specs: `world-creation`, `configuration`
- Affected code:
  - `novelgen/chains/world_chain.py` - 新增变体生成函数
  - `novelgen/models.py` - 新增数据模型
  - `novelgen/config.py` - 新增世界观变体数量配置
  - `novelgen/runtime/workflow.py` - 新增交互式世界观选择节点（可选）
  - `novelgen/cli.py` - 新增 CLI 命令支持候选选择

