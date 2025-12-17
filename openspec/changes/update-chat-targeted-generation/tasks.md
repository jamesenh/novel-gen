## 1. Implementation

- [x] 1.1 在 `ng chat` 自然语言路径中增加"生成目标"抽取与标准化（世界观/主题冲突/人物角色/大纲等）
- [x] 1.2 建立目标→前置依赖的规则表，并通过 `workflow.status`（或等效文件状态）判定缺失项
- [x] 1.3 缺少前置时生成"范围确认"（补齐前置 + stop_at 目标）提示，等待 `/yes` 才执行；该确认不受 `/auto on` 影响
- [x] 1.4 用户确认后执行 `workflow.run(stop_at=<target_node>)`，并在到达目标节点后停止（不继续后续节点）
- [x] 1.5 更新帮助与文档示例：明确"生成 X"为目标型生成，"开始/继续/一键"为全流程

## 2. Validation

- [x] 2.1 添加/更新测试用例覆盖：
  - "生成人物角色"在前置齐全/缺少前置/用户拒绝补齐 的行为
  - "开始生成/继续生成"触发全流程的行为不回归
- [x] 2.2 运行 `openspec validate update-chat-targeted-generation --strict` 并通过

## 3. Docs

- [x] 3.1 更新 `docs/对话式Agent使用指南.md`：新增目标型生成说明、示例对话与注意事项

