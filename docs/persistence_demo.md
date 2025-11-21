# 持久化功能示例（Phase1）

Phase1 的目标是：在 **不改变现有生成逻辑** 的前提下，为 NovelGen 建立数据库 + 向量存储的持久化基础设施。
本说明文档展示如何开启/关闭持久化、如何配置路径，以及如何运行一个最小 Demo 并查看结果。

> 注意：所有示例命令都假设你在仓库根目录下执行，并已正确配置 OpenAI API Key。

---

## 1. 开启 / 关闭持久化

持久化开关由 `ProjectConfig` 字段和环境变量共同控制：

- `ProjectConfig.persistence_enabled`  / 环境变量 `NOVELGEN_PERSISTENCE_ENABLED`
- `ProjectConfig.vector_store_enabled` / 环境变量 `NOVELGEN_VECTOR_STORE_ENABLED`

环境变量的解析规则（不区分大小写）：

- 视为 **开启**：`"true"`, `"1"`, `"yes"`, `"on"`
- 其他值或未设置时，使用 `ProjectConfig` 默认值（True）

典型用法：

```bash
# 显式开启数据库和向量存储持久化（默认即为开启）
export NOVELGEN_PERSISTENCE_ENABLED=true
export NOVELGEN_VECTOR_STORE_ENABLED=true

# 显式关闭持久化（只使用 JSON 文件）
export NOVELGEN_PERSISTENCE_ENABLED=false
export NOVELGEN_VECTOR_STORE_ENABLED=false
```

在运行时，`NovelOrchestrator` 会在初始化阶段打印当前持久化状态，例如：

- `✅ 数据库持久化已启用: ...`
- `✅ 向量存储已启用: ...`
- `ℹ️ 已通过配置关闭数据库持久化（ProjectConfig.persistence_enabled=False）`

---

## 2. 配置数据库路径和向量存储目录

Phase1 中新增了两个项目级配置字段（定义在 `ProjectConfig` 中）：

- `db_path: Optional[str]`
  - 数据库文件路径
  - 可以是 **绝对路径**，也可以是 **相对于 `project_dir` 的相对路径**
  - 默认值：`project_dir/data/novel.db`
- `vector_store_dir: Optional[str]`
  - 向量存储持久化目录
  - 同样支持绝对路径或相对于 `project_dir` 的相对路径
  - 默认值：`project_dir/data/vectors`

这两个字段也可以通过环境变量覆盖：

- `NOVELGEN_DB_PATH` → `ProjectConfig.db_path`
- `NOVELGEN_VECTOR_STORE_DIR` → `ProjectConfig.vector_store_dir`

示例：

```bash
# 将数据库文件放到 project_dir/custom_data/novel.db
export NOVELGEN_DB_PATH="custom_data/novel.db"

# 将向量存储放到 project_dir/custom_vectors
export NOVELGEN_VECTOR_STORE_DIR="custom_vectors"
```

> 说明：如果提供的是相对路径，则会自动拼接在当前项目的 `project_dir` 下面；
> 如果提供的是绝对路径，则按绝对路径使用。

---

## 3. 运行一个最小持久化 Demo

下面的命令会在 `projects/demo_persistence_001` 下创建一个新项目，并跑通核心 6 步流程（会调用 LLM）：

```bash
export NOVELGEN_PERSISTENCE_ENABLED=true
export NOVELGEN_VECTOR_STORE_ENABLED=true

python - << 'PY'
from novelgen.runtime.orchestrator import NovelOrchestrator

orchestrator = NovelOrchestrator(
    project_name="demo_persistence_001",
    base_dir="projects",
    verbose=False,
)

# 运行一个缩减版流程
orchestrator.step1_create_world("一个用于持久化示例的世界观", force=True)
orchestrator.step2_create_theme_conflict("一个关于勇气与成长的主题", force=True)
orchestrator.step3_create_characters(force=True)
orchestrator.step4_create_outline(num_chapters=3, force=True)
orchestrator.step5_create_chapter_plan(1, force=True)
orchestrator.step6_generate_chapter_text(1, force=True)

orchestrator.close()
PY
```

运行结束后，你可以在以下位置看到生成的数据：

- 项目 JSON 文件：`projects/demo_persistence_001/*.json`
- SQLite 数据库（默认）：`projects/demo_persistence_001/data/novel.db`
- 向量存储目录（默认）：`projects/demo_persistence_001/data/vectors/`

> 如果未安装 ChromaDB，则向量存储会自动降级为禁用状态，运行流程不会因此失败。

---

## 4. 手动查看数据库内容（简要）

SQLite 数据库中主要有两张表：`entity_snapshots`（实体状态快照）和 `memory_chunks`（文本记忆块）。
你可以使用 `sqlite3` 命令行或任意 SQLite GUI 工具浏览这些表，以验证持久化结果是否符合预期。

---

## 5. 性能影响验证脚本说明

Phase1 中增加了一个轻量级性能基准脚本：`novelgen/runtime/persistence_benchmark.py`。

用法：

```bash
python -m novelgen.runtime.persistence_benchmark
```

脚本会在临时目录下分别运行：

1. **开启持久化**（数据库 + 向量存储）
2. **关闭持久化**（仅使用 JSON 文件）

并在控制台输出两者耗时及差值，用于粗略评估持久化引入的额外开销。
由于耗时高度依赖于 LLM 延迟和本机性能，建议在本地多次运行并结合实际需求进行评估。

---

## 6. 关于配置“热重载”的边界说明

- `NovelOrchestrator` 会在 **实例化时** 读取 `ProjectConfig` 和相关环境变量；
- 如果你修改了环境变量或配置文件，**需要重新创建一个新的 `NovelOrchestrator` 实例** 才能生效；
- 现有实例正在进行的任务不会受到影响，这与 OpenSpec 中对“运行时热重载”的要求保持一致（以实例生命周期为粒度）。

这也意味着：在 CLI / 单次运行场景下，只需在运行前调整配置，然后启动新的 Orchestrator 即可。

