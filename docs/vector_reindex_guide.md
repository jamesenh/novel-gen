# 向量索引重建指南

## 概述

向量索引重建功能允许你在以下场景中重新生成项目的向量索引：

- 调整了分块策略（`chunk_size` / `chunk_overlap`）后，希望让旧项目生效新策略
- 修复了 embedding / Chroma 配置错误后，需要重新写入所有记忆块
- 清理脏数据或手动修改数据库记录后，需要重新同步向量库

## 使用方法

### 项目级重建

重建整个项目的向量索引：

```bash
python scripts/reindex_vectors.py <project_id>
```

示例：
```bash
python scripts/reindex_vectors.py demo_003
```

### 章节级重建

只重建指定章节的向量索引：

```bash
python scripts/reindex_vectors.py <project_id> --chapter <chapter_index>
```

示例：
```bash
python scripts/reindex_vectors.py demo_003 --chapter 1
```

### Dry-run 模式

在不实际执行的情况下，查看将被影响的向量数量：

```bash
python scripts/reindex_vectors.py <project_id> --dry-run
```

### 指定项目目录

如果项目不在默认的 `projects/<project_id>` 目录下：

```bash
python scripts/reindex_vectors.py <project_id> --project-dir /path/to/project
```

### 详细日志

启用详细日志输出以便调试：

```bash
python scripts/reindex_vectors.py <project_id> --verbose
```

## 工作原理

### 数据源优先级

重建工具会按以下优先级加载源文本：

1. **数据库 `memory_chunks` 表**（如果持久化已启用且数据库中有记忆块）
2. **章节 JSON 文件**（作为后备策略）

### 重建流程

1. **加载项目配置**：读取项目的 embedding 配置和分块策略
2. **删除旧向量**：清理目标范围（项目或章节）的旧向量
3. **重新生成向量**：
   - 从数据库或章节 JSON 加载源文本
   - 按当前配置重新分块
   - 调用 embedding API 生成向量
   - 写入 ChromaDB
4. **输出统计信息**：显示删除和创建的向量数量

## 注意事项

### 性能考虑

- **重建耗时**：重建过程需要调用 embedding API，对于大项目可能耗时较长
- **建议**：对于大项目，可以分章节重建以减少单次操作时间

### 数据安全

- **先删后建**：重建过程会先删除旧向量，再写入新向量
- **建议**：在重建前先用 `--dry-run` 查看将被影响的数据量
- **备份**：如果担心数据丢失，可以先备份 `projects/<project_id>/data/vectors` 目录

### 配置一致性

- 重建使用的是**当前项目配置**中的 embedding 和分块参数
- 如果你想用新配置重建，请先修改项目配置或环境变量，再执行重建

### 错误处理

- 如果向量存储未启用（`NOVELGEN_VECTOR_STORE_ENABLED=false`），重建会失败并提示错误
- 如果章节 JSON 文件不存在或格式错误，该章节会被跳过，不影响其他章节

## 验证重建结果

重建完成后，可以使用 `query_scene_memory.py` 验证向量检索是否正常：

```bash
python scripts/query_scene_memory.py <project_id> --search "关键词" --limit 5
```

示例：
```bash
python scripts/query_scene_memory.py demo_003 --search "林风" --limit 5
```

## 编程接口

除了 CLI 脚本，你也可以在 Python 代码中直接调用重建函数：

```python
from novelgen.runtime.reindex_tools import reindex_project_vectors, reindex_chapter_vectors

# 项目级重建
stats = reindex_project_vectors(
    project_id="demo_003",
    project_dir=None,  # 可选，默认为 projects/<project_id>
    dry_run=False
)
print(f"删除了 {stats['deleted_chunks']} 个旧向量")
print(f"创建了 {stats['created_chunks']} 个新向量")

# 章节级重建
stats = reindex_chapter_vectors(
    project_id="demo_003",
    chapter_index=1,
    project_dir=None,
    dry_run=False
)
```

## 常见问题

### Q: 重建会影响正常的生成流程吗？

A: 不会。重建是一个独立的运维工具，不会改变正常的章节生成、修订和记忆写入流程。

### Q: 重建失败了怎么办？

A: 检查以下几点：
- 向量存储是否已启用（`NOVELGEN_VECTOR_STORE_ENABLED=true`）
- 项目目录是否存在
- 章节 JSON 文件是否完整
- embedding API 是否可访问

### Q: 可以只重建某些场景的向量吗？

A: 当前版本只支持项目级和章节级重建。如果需要更细粒度的重建，可以考虑在后续版本中扩展。

### Q: 重建后向量数量和之前不一样？

A: 这是正常的，可能的原因：
- 修改了 `chunk_size` 或 `chunk_overlap` 参数
- 章节内容发生了变化（如修订后）
- 之前的向量数据不完整或有错误
