## 1. Orchestrator API & Behavior
- [x] 1.1 为 `step6_generate_chapter_text` 增加 `force: bool = False` 参数，并在内部使用 `_maybe_use_existing` 复用章节 JSON
- [x] 1.2 调整 `generate_all_chapters()`，支持传入 `force` 参数并传递给 step6
- [x] 1.3 确保复用时不会重复触发 LLM 场景生成调用

## 2. Logging & UX
- [x] 2.1 在复用已生成章节时输出“跳过本次生成”的控制台日志，包含章节编号和文件路径
- [x] 2.2 在 `force=True` 时输出“强制重算”的提示

## 3. Tests & Validation
- [x] 3.1 为 step6 添加最小单元/集成测试，覆盖 `force=True/False` 以及“文件无法解析”降级重算场景
- [x] 3.2 为 generate_all_chapters() 添加或更新测试/手动脚本，验证在部分章节存在的情况下行为符合预期
- [x] 3.3 运行 `openspec validate add-step6-chapter-text-force --strict` 并修正所有问题
