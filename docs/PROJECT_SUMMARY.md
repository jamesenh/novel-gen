# 📊 NovelGen 项目概览（持续更新）

本文档用于提供“当前实现”的快速全貌：核心能力、目录结构、落盘约定与文档入口。

## 项目信息

- **项目名称**：NovelGen - AI 中文小说生成系统
- **技术栈**：Python 3.10+ / LangChain / LangGraph / Pydantic / Typer / ChromaDB / Mem0（可选）/ Kùzu（可选）
- **工作流形态**：LangGraph 状态工作流 + 章节循环 + 场景子工作流
- **真源**：`projects/<project>/` 下的结构化 JSON 文件

## 核心能力（当前已实现）

- **端到端生成**：世界观 → 主题冲突 → 角色 → 大纲 → 章节计划 → 场景生成 → 章节合并
- **断点续跑**：LangGraph SQLite checkpoint（`workflow_checkpoints.db`）
- **章节循环**：逐章生成 + 一致性检测 +（可选）自动修订 + 进入下一章
- **动态扩展大纲**：根据剧情进度评估继续/收束/强制结束，更新 `outline.json`
- **场景级落盘**：逐场景写入 `scene_XXX_YYY.json`，便于断点续跑与定位问题
- **Mem0 记忆层（可选）**：项目偏好注入 + 角色状态 + 场景向量检索（ChromaDB 落盘）
- **Kùzu 图谱（可选）**：角色/关系/事件查询，支持 CLI 与对话式 Agent 调用
- **对话式 Agent（MVP）**：`ng chat` + 斜杠命令 + 安全确认机制
- **CLI 工具链**：初始化、候选选择、运行/恢复、状态、回滚、导出、图谱管理

## 仓库结构（概览）

```
novel-gen/
  novelgen/
    cli.py
    agent/
    tools/
    chains/
    runtime/
    graph/
  projects/
  docs/
  tests/
  scripts/
  openspec/
```

## projects/<project_id>/ 落盘约定（摘要）

- `settings.json`：项目输入与参数
- `world.json` / `theme_conflict.json` / `characters.json` / `outline.json`：阶段产物
- `chapters/`：
  - `chapter_XXX_plan.json`：章节计划
  - `scene_XXX_YYY.json`：场景（可断点续跑）
  - `chapter_XXX.json`：整章合并
- `chapter_memory.json`：章节记忆（用于上下文与图谱增量更新）
- `consistency_reports.json`：一致性报告集合
- `workflow_checkpoints.db`：LangGraph checkpoint
- `data/vectors/`：Mem0/Chroma（可选）
- `data/graph/`：Kùzu 图谱（可选）

## 文档入口

- `docs/README.md`：文档索引
- `docs/QUICKSTART.md`：快速开始
- `docs/ENV_SETUP.md`：环境变量配置
- `docs/STRUCTURE.md`：目录与真源约定
- `docs/小说生成完整流程说明.md`：流程全解（以代码为准）

## 运行与测试

```bash
uv sync
pytest
```

   - [ ] API 服务

3. **提示优化**
   - [ ] 根据实际效果优化各 chain 的 prompt
   - [ ] 添加更多示例到提示中
   - [ ] 实现 few-shot learning

4. **质量提升**
   - [ ] 添加单元测试
   - [ ] 添加集成测试
   - [ ] 实现 logging
   - [ ] 添加错误处理和重试机制

## 学习价值

这个项目非常适合学习：

- ✅ **LangChain 核心概念**
  - ChatPromptTemplate
  - PydanticOutputParser
  - Chain 组合
  - Runnable 接口

- ✅ **AI 应用架构**
  - 模块化设计
  - 数据流设计
  - 状态管理
  - 错误处理

- ✅ **Prompt Engineering**
  - 结构化提示设计
  - JSON Schema 约束
  - 角色设定
  - 任务分解

- ✅ **Python 最佳实践**
  - Pydantic 数据验证
  - 类型注解
  - 文档字符串
  - 项目组织

## 致谢

本项目严格遵循预定的项目哲学和代码规范构建，所有模块都已经过验证。

---

**状态**: ✅ 项目结构初始化完成  
**作者**: Jamesenh  
**日期**: 2025-11-14  
**版本**: 0.1.0

🎉 **NovelGen 已准备就绪，开始你的 AI 小说创作之旅吧！**
