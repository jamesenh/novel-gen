## 1. Specs
- [x] 1.1 在 chapter-planning 能力下新增"基于大纲生成全部章节计划"的 ADDED requirement 与场景
- [x] 1.2 在 orchestration 能力下新增"参数化章节范围"的 ADDED requirement 与场景
- [x] 1.3 运行 `openspec validate add-all-chapter-generation --strict` 并修正所有问题

## 2. Orchestrator API
- [x] 2.1 扩展 `step5_create_chapter_plan`，支持"全部章节"模式（例如 special 值或缺省行为），内部自动读取 outline.chapters
- [x] 2.2 扩展 `generate_all_chapters`，支持通过参数限制章节范围，同时保持现有"全部章节"默认行为
- [x] 2.3 确保 step5 / step6 在多章模式下仍正确传递 `force` 参数并复用章节计划/文本

## 3. Demos & Tests
- [x] 3.1 更新 `main.py` demo，展示全部章节计划和部分章节计划/正文的典型调用方式
- [x] 3.2 添加或更新测试（例如针对 orchestrator），覆盖单章 / 多章 / 全部章节三种模式
- [x] 3.3 在本地运行测试和示例脚本，确认行为符合 spec
