## 1. 数据模型

- [x] 1.1 在 `models.py` 中新增 `ThemeConflictVariant` 模型（包含变体 ID、风格标签、简述）
- [x] 1.2 在 `models.py` 中新增 `ThemeConflictVariantsResult` 模型（包含多个候选和原始提示）

## 2. 配置支持

- [x] 2.1 在 `config.py` 中添加 `theme_conflict_variants_file` 属性

## 3. 核心生成链

- [x] 3.1 在 `theme_conflict_chain.py` 中新增 `generate_theme_conflict_variants()` 函数
- [x] 3.2 实现变体生成提示词模板，确保候选风格多样化
- [x] 3.3 支持无用户输入时从世界观自动推导
- [x] 3.4 保持原有 `generate_theme_conflict()` 函数向后兼容
- [x] 3.5 从 `ProjectConfig.world_variants_count` 读取默认候选数量

## 4. 候选选择接口

- [x] 4.1 新增 `select_theme_conflict_variant()` 函数
- [x] 4.2 新增 `save_theme_conflict_variants()` 和 `load_theme_conflict_variants()` 函数

## 5. CLI 集成

- [x] 5.1 更新 `init` 命令，在输入主题时提供 AI 生成选项
- [x] 5.2 新增 `ng theme-variants <project>` 命令生成多候选
- [x] 5.3 新增 `ng theme-select <project> <variant_id>` 命令选择候选
- [x] 5.4 新增 `ng theme-show <project>` 命令展示当前候选

## 6. 验证与测试

- [x] 6.1 验证多候选生成输出符合 Pydantic 模型
- [x] 6.2 验证候选选择后能正确保存并进入后续流程
- [x] 6.3 验证与现有单一生成模式的兼容性
- [x] 6.4 更新 tasks.md 标记所有任务完成

