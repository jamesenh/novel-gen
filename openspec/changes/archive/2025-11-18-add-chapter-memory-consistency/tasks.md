## 1. Chapter Memory Infrastructure
- [x] 1.1 Define `chapter_memory.json` schema（角色状态、悬念、时间/地点、风险、未决事件）
- [x] 1.2 在 orchestrator 中写入/读取记忆，支持增量附加与最近N章查询
- [x] 1.3 为 chapter plan/scene 生成步骤注入记忆数据，并添加单元测试

## 2. Scene Summaries & Context
- [x] 2.1 在 step6 中为每个 GeneratedScene 生成真实摘要，并替换 previous_summary
- [x] 2.2 更新 scene_text_chain prompt，新增 `chapter_context` 字段与相关指令
- [x] 2.3 扩展 models/config，传递可配置的「引用最近N章」参数

## 3. Consistency Check Automation
- [x] 3.1 设计并实现一致性校验链（输入章上下文+全文，输出冲突列表）
- [x] 3.2 在 orchestrator 中对每章触发校验，发现冲突时记录、可选触发 revision
- [x] 3.3 添加测试/fixtures，确保检测逻辑可控

## 4. Outline Timeline & Dependencies
- [x] 4.1 更新 outline-generation spec & models，支持 `timeline_anchor` 与 `dependencies`
- [x] 4.2 在大纲生成链里填充上述字段，同时定义校验规则
- [x] 4.3 实现分阶段依赖验证：step5阶段只验证逻辑有效性（不依赖未来章节），step6开始前验证实际依赖满足情况（基于章节内容文件存在性）

## 5. Documentation & Validation
- [x] 5.1 更新 README/开发文档，解释记忆表、自检流程及配置
- [x] 5.2 扩充测试覆盖面，确保CI通过
- [x] 5.3 运行 `openspec validate add-chapter-memory-consistency --strict` 并修正所有问题
