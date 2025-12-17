<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.
<!-- OPENSPEC:END -->

# NovelGen Project Guide

该文件用于指导 AI 助手在本仓库内高效、安全、与现状一致地工作（**保持上方 OpenSpec managed block 不变**）。

## 文档入口（先读这些）

- 文档索引：`docs/README.md`
- 快速开始：`docs/QUICKSTART.md`
- 环境变量配置：`docs/ENV_SETUP.md`
- 目录与落盘约定：`docs/STRUCTURE.md`
- 生成流程全解（以代码为准）：`docs/小说生成完整流程说明.md`
- 对话式 Agent：`docs/对话式Agent使用指南.md`
- Kùzu 知识图谱：`docs/知识图谱使用指南.md`

## Technology Stack

**Core Technologies:**
- **Python 3.10+** with LangChain 1.0+ ecosystem
- **LangGraph** for complex workflow orchestration
- **OpenAI GPT models** (GPT-4, GPT-3.5-turbo) as primary LLM
- **Pydantic 2.0+** for structured output validation
- **ChromaDB** for vector storage and semantic search
- **Mem0** for intelligent memory management (optional)
- **uv** for modern Python package management
- **Typer + Rich** for CLI and UX
- **Kùzu** for embedded knowledge graph (optional)

**Development Tools:**
- **pytest** for testing framework
- **OpenSpec** for spec-driven development and change management
- **dotenv** for environment configuration

## Project Architecture

```
novelgen/
├── novelgen/                 # 主包
│   ├── cli.py                # ng 命令入口（Typer）
│   ├── config.py             # 项目配置/环境变量
│   ├── models.py             # Pydantic 模型
│   ├── llm.py                # LLM 初始化与统一配置
│   ├── chains/               # 各阶段生成链（结构化输出）
│   ├── runtime/              # LangGraph 工作流/节点/编排器
│   ├── agent/                # 对话式 Agent（ng chat）
│   ├── tools/                # Agent 工具（workflow/graph/memory/preference）
│   └── graph/                # Kùzu 图谱（可选）
├── projects/                 # 每个项目一套生成真源（JSON）
├── tests/                    # 测试
├── scripts/                  # 运维/维护脚本（Mem0/向量/查看等）
├── openspec/                 # OpenSpec 配置/变更
└── docs/                     # 文档
```

## 运行入口（以 CLI 为准）

项目脚本入口在 `pyproject.toml` 的 `[project.scripts]`：`ng = "novelgen.cli:app"`。

常用命令（示例）：

```bash
ng init demo_001
ng run demo_001
ng resume demo_001
ng status demo_001
ng state demo_001
ng export demo_001
ng rollback demo_001 --chapter 3
ng chat demo_001
ng graph rebuild demo_001
```

世界观/主题冲突候选（可选但推荐）：

```bash
ng world-variants demo_001 --prompt "修仙世界" --expand
ng world-select demo_001 variant_1
ng theme-variants demo_001 --direction "复仇"
ng theme-select demo_001 variant_1
```

## 数据与落盘约定（关键）

- **JSON 为真源**：`projects/<project_id>/` 下的 `world.json / characters.json / outline.json / chapters/...` 等文件是“事实来源”
- **可选层可降级**：Mem0（向量/偏好/状态）与 Kùzu 图谱均应做到“不可用则静默跳过，不阻断主流程”
- **断点续跑**：LangGraph checkpoint 默认在 `projects/<project_id>/workflow_checkpoints.db`

## 对话式 Agent（ng chat）

- 代码：`novelgen/agent/chat.py` + `novelgen/tools/*`
- 斜杠命令与确认策略：参考 `docs/对话式Agent使用指南.md`

### Code Style Guidelines

**File Headers:**
- Each file must contain Chinese docstring explaining module functionality
- Include author info and date (jamesenh, YYYY-MM-DD)

**Naming Conventions:**
- Functions/variables: English snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

**Import Order:**
1. Standard library
2. Third-party libraries
3. Local modules (use absolute imports)

**Comments:**
- Complex logic requires Chinese comments
- Complete function docstrings with Args, Returns, and functionality description

## Build and Test Commands

### Installation
```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -r requirements.txt
```

### Configuration（.env）

见：`docs/ENV_SETUP.md`（从 `.env.template` 拷贝为 `.env`）

### Running Novel Generation
```bash
# 初始化项目并生成
ng init demo_001
ng run demo_001

# 断点恢复
ng resume demo_001

# 状态/导出/回滚
ng status demo_001
ng export demo_001
ng rollback demo_001 --chapter 3
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_end_to_end.py

# Run with verbose output
pytest -v
```

### Memory Management
```bash
# Mem0 健康检查
python scripts/check_mem0_health.py

# 向量重建
python scripts/reindex_vectors.py

# Mem0 导出/清理
python scripts/export_mem0_to_json.py
python scripts/clear_mem0_memory.py
```

## Configuration Options

### Environment Variables
- **OPENAI_API_KEY**: Required for OpenAI API access
- **OPENAI_MODEL_NAME**: Default model (gpt-4, gpt-3.5-turbo)
- **TEMPERATURE**: Creativity level (0.0-2.0)
- **MEM0_ENABLED**: Enable intelligent memory layer
- **EMBEDDING_MODEL_NAME**: Vector embedding model
- **Chain-specific configs**: Individual model settings per generation step

### Project Settings (settings.json)
```json
{
  "project_name": "demo_001",
  "author": "Jamesenh",
  "llm_model": "gpt-4",
  "temperature": 0.7,
  "persistence_enabled": true,
  "vector_store_enabled": true,
  "world_description": "小说世界观描述...",
  "theme_description": "主题和冲突描述...",
  "num_chapters": 5
}
```

## Testing Strategy

**Current Approach:**
- Manual testing through demo projects (demo_001, demo_002)
- End-to-end workflow validation
- JSON format and Pydantic model validation
- Content quality and consistency checks

**Test Categories:**
- **Unit tests**: Individual component testing
- **Integration tests**: Full workflow validation
- **State persistence tests**: Checkpoint and recovery
- **Memory system tests**: Vector store integration

**Focus Areas:**
- JSON output format correctness
- Pydantic model validation
- Content coherence and consistency
- Prompt execution effectiveness

## Security Considerations

**API Security:**
- OpenAI API keys stored in environment variables
- Support for different API endpoints and providers
- Rate limiting and timeout configurations

**Content Safety:**
- Relies on OpenAI's content filtering
- Chinese market focus with cultural adaptation
- No direct content moderation controls

**Data Handling:**
- Local JSON file storage for generated content
- No database or user authentication system
- Vector storage uses local ChromaDB instance

## Important Constraints

**Technical Limitations:**
- Complete dependency on OpenAI API availability
- JSON format strictness required for pipeline success
- No concurrent generation support
- Memory usage can be high for long texts

**Business Constraints:**
- Chinese language focus only
- AI-generated content cannot be copyrighted
- Content quality varies with LLM randomness
- Cost-sensitive due to GPT-4 pricing

**System Constraints:**
- Stateless design using JSON files
- Single-user focused architecture
- No built-in caching (except generation reuse)
- Network dependency for API calls

## OpenSpec Integration

This project uses OpenSpec for spec-driven development. When making significant changes:

1. **Check existing specs**: `openspec spec list --long`
2. **List active changes**: `openspec list`
3. **Create proposals** for new features, breaking changes, or architecture shifts
4. **Follow three-stage workflow**: Create → Implement → Archive
5. **Use Chinese language** for specs and documentation to match project conventions

For detailed OpenSpec instructions, see `@/openspec/AGENTS.md`.
