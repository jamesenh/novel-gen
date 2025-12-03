## 1. 配置支持

- [x] 1.1 在 `config.py` 的 `ProjectConfig` 中新增 `world_variants_count` 字段（默认值 3）
- [x] 1.2 支持环境变量 `WORLD_VARIANTS_COUNT` 覆盖默认候选数量
- [x] 1.3 添加候选数量范围验证（2-5）

## 2. 数据模型

- [x] 2.1 在 `models.py` 中新增 `WorldVariant` 模型（包含变体 ID、风格标签、简述）
- [x] 2.2 在 `models.py` 中新增 `WorldVariantsResult` 模型（包含多个候选和原始提示）

## 3. 核心生成链

- [x] 3.1 在 `world_chain.py` 中新增 `generate_world_variants()` 函数，支持生成多个候选
- [x] 3.2 新增 `expand_world_prompt()` 函数，将简短提示扩展为详细描述
- [x] 3.3 实现变体生成提示词模板，确保候选风格多样化
- [x] 3.4 保持原有 `generate_world()` 函数向后兼容
- [x] 3.5 从 `ProjectConfig` 读取默认候选数量配置

## 4. 候选选择接口

- [x] 4.1 新增 `select_world_variant()` 函数，根据用户选择返回完整 WorldSetting
- [x] 4.2 支持将选中的候选保存到项目目录

## 5. CLI 集成

- [x] 5.1 新增 `ng world-variants <project>` 命令生成多候选
- [x] 5.2 新增 `ng world-select <project> <variant_id>` 命令选择候选
- [x] 5.3 新增 `--expand` 选项支持 AI 扩写模式
- [x] 5.4 新增 `--count` 选项覆盖配置的候选数量

## 6. 验证与测试

- [x] 6.1 验证多候选生成输出符合 Pydantic 模型
- [x] 6.2 验证候选选择后能正确保存并进入后续流程
- [x] 6.3 验证与现有单一生成模式的兼容性
- [x] 6.4 验证环境变量配置生效

