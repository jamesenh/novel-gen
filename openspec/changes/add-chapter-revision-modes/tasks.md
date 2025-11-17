## 1. Implementation
- [x] 1.1 在 `ProjectConfig` 中增加 `revision_policy` 字段，并支持从环境变量/构造参数配置
- [x] 1.2 升级修订链为结构化输出：
  - [x] 1.2.1 在 `novelgen/chains/` 下创建或重构修订链（如 `chapter_revision_chain.py`）
  - [x] 1.2.2 使用 `ChatPromptTemplate` + `with_structured_output(GeneratedChapter)` 或 `PydanticOutputParser`
  - [x] 1.2.3 定义修订链输入：原始 `GeneratedChapter` JSON + `revision_notes` 字符串
  - [x] 1.2.4 定义修订链输出：完整的已修订 `GeneratedChapter` 结构
  - [x] 1.2.5 在提示词中明确约束：保持 chapter_number/chapter_title 不变，优先修改场景内容而非增删场景
- [x] 1.3 在 `NovelOrchestrator.step6_generate_chapter_text` 中按 `revision_policy` 接入修订阶段（不改变默认行为）
- [x] 1.4 为 auto_apply 模式实现：
  - [x] 1.4.1 收集可自动修复的 issue 并构造 `revision_notes`
  - [x] 1.4.2 调用升级后的修订链，直接获取结构化的 `GeneratedChapter`
  - [x] 1.4.3 使用修订链返回的 `GeneratedChapter` 覆盖写回 `chapter_XXX.json`
  - [x] 1.4.4 视情况重建章节记忆
  - [x] 1.4.5 可选：将修订后的 GeneratedChapter 导出为可读文本 `chapter_XXX_revised.txt` 供审阅
- [x] 1.5 为 manual_confirm 模式实现：
  - [x] 1.5.1 调用修订链生成结构化的修订候选 `GeneratedChapter`
  - [x] 1.5.2 将修订候选 GeneratedChapter 及元数据（问题列表、revision_notes、时间戳等）写入 `chapter_XXX_revision.json`
  - [x] 1.5.3 不修改 `chapter_XXX.json`，保持原始版本
  - [x] 1.5.4 标记章节为「pending」状态
  - [x] 1.5.5 可选：将修订候选导出为可读文本以便人工对比
  - [x] 1.5.6 在 `generate_all_chapters()` 中检测待确认章节，默认阻止后续章节生成并给出可读错误

## 2. CLI / Runtime APIs
- [x] 2.1 增加显式「应用修订」操作（CLI 命令或 runtime 函数），完成从 pending → accepted 的状态迁移
- [x] 2.2 在应用修订时：
  - [x] 2.2.1 读取修订候选文本与状态文件
  - [x] 2.2.2 更新 `chapter_XXX.json` 与章节记忆
  - [x] 2.2.3 更新修订状态为 accepted，并记录时间戳

## 3. Logging & UX
- [x] 3.1 在 auto_apply / manual_confirm 路径中增加清晰的日志输出：
  - [x] 3.1.1 当前修订策略
  - [x] 3.1.2 检测到的可自动修复问题数量
  - [x] 3.1.3 修订结果保存位置
- [x] 3.2 为 manual 模式下被阻断的 `generate_all_chapters()` 提供明确错误信息，列出需要先处理的章节编号

## 4. Testing & Validation
- [ ] 4.1 为 auto_apply 模式添加集成测试：
  - [ ] 4.1.1 构造含可修复 issue 的章节，一致性检测后 JSON 被更新
  - [ ] 4.1.2 导出整书 txt 使用修订后的内容
- [ ] 4.2 为 manual_confirm 模式添加集成测试：
  - [ ] 4.2.1 生成 pending 修订候选
  - [ ] 4.2.2 验证 `generate_all_chapters()` 在存在 pending 时默认阻断
  - [ ] 4.2.3 验证应用修订后，章节 JSON 与导出结果发生预期变化
- [x] 4.3 通过 `openspec validate add-chapter-revision-modes --strict` 校验 spec 完整性
