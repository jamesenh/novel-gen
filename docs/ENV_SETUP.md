# NovelGen 环境变量配置

NovelGen 使用 `.env`（配合 `python-dotenv`）读取环境变量。推荐从 `.env.template` 拷贝并按需修改：

```bash
cp .env.template .env
```

## 必需配置

- `OPENAI_API_KEY`：OpenAI（或兼容服务）API Key

可选但常用：
- `OPENAI_API_BASE` 或 `OPENAI_BASE_URL`：自定义 API Base（代理/兼容服务）
- `OPENAI_MODEL_NAME`：默认模型名
- `TEMPERATURE`：默认温度

## 链路级覆盖（可选）

每条链支持独立配置（详见 `.env.template`）：

- `WORLD_CHAIN_*`
- `THEME_CONFLICT_CHAIN_*`
- `CHARACTERS_CHAIN_*`
- `OUTLINE_CHAIN_*`
- `CHAPTERS_PLAN_CHAIN_*`
- `SCENE_TEXT_CHAIN_*`

## Embedding / 向量配置（用于 Mem0 / Chroma）

- `EMBEDDING_MODEL_NAME`
- `EMBEDDING_API_KEY`（不填则复用 `OPENAI_API_KEY`）
- `EMBEDDING_BASE_URL`
- `EMBEDDING_CHUNK_SIZE` / `EMBEDDING_CHUNK_OVERLAP`
- `NOVELGEN_VECTOR_STORE_DIR`：覆盖向量落盘目录（默认 `projects/<id>/data/vectors`）

## Mem0 记忆层（可选）

启用：
- `MEM0_ENABLED=true`

常用：
- `MEM0_REQUEST_TIMEOUT` / `MEM0_MAX_RETRIES` / `MEM0_RETRY_BACKOFF_FACTOR`
- `MEM0_PARALLEL_WORKERS`
- `MEM0_LLM_MODEL_NAME` / `MEM0_LLM_API_KEY` / `MEM0_LLM_BASE_URL`

说明：
- Mem0 内部复用 ChromaDB，默认落盘在 `projects/<id>/data/vectors/`。
- 偏好工具与场景检索工具需要 Mem0 启用（对话中 `/setpref`、`/prefs`、记忆检索等）。

## Kùzu 图谱（可选）

启用开关（默认开启）：
- `NOVELGEN_GRAPH_ENABLED=true|false`

目录覆盖：
- `NOVELGEN_GRAPH_DIR`：覆盖图谱目录（默认 `projects/<id>/data/graph/`）

说明：
- 图谱功能依赖 `kuzu` Python 包；未安装时会自动降级为不可用。

## LangGraph 工作流（可选）

- `LANGGRAPH_RECURSION_LIMIT`：递归限制（防止无限循环）
- `LANGGRAPH_NODES_PER_CHAPTER`：每章节点数估算（用于提前停止并保存检查点）

## 对话式 Agent（可选）

- `NOVELGEN_CHAT_CONFIRM_DEFAULT=true|false`：是否默认对生成类动作要求确认
- `NOVELGEN_CHAT_MAX_TOOL_CALLS`：单轮对话最大工具调用次数
- `NOVELGEN_CHAT_RETRIEVAL_MAX_ATTEMPTS`：信息补齐最大尝试次数

## 逻辑审查质量闸门（可选）

- `NOVELGEN_LOGIC_REVIEW_POLICY=off|blocking`：逻辑审查策略
  - `off`（默认）：关闭逻辑审查
  - `blocking`：启用阻断模式，评分低于阈值或存在高严重性问题时阻止后续生成
- `NOVELGEN_LOGIC_REVIEW_MIN_SCORE`：最低通过分数（0-100，默认 75）

阻断条件：
1. `overall_score < NOVELGEN_LOGIC_REVIEW_MIN_SCORE`
2. 存在 `severity == "high"` 的问题

说明：
- 启用阻断后，章节生成后会自动调用逻辑审查链
- 阻断时生成审查报告（`reviews/chapter_XXX_logic_review.json`）和修订状态（`chapters/chapter_XXX_revision.json`）
- 用户需通过 `/fix` + `/accept` 应用修订，或 `/reject` 跳过阻断，才能继续生成后续章节

## 调试

- `NOVELGEN_DEBUG=1`：启用 CLI 退出调试日志
- `LOG_LEVEL=DEBUG|INFO|WARNING|ERROR`：日志级别（如代码中支持）

