# memory_chunks 表写入功能修复总结

## 问题描述

在 Phase1 持久化实现中，虽然创建了 `memory_chunks` 表和相关接口，但在实际运行时，该表并未被写入数据。场景内容只被保存到 ChromaDB 向量库，而没有同步保存到 SQLite 数据库的 `memory_chunks` 表。

## 根本原因

`VectorStoreManager.add_scene_content()` 方法将场景内容分块并存入向量库后，没有将创建的 `StoryMemoryChunk` 对象同步保存到数据库。

## 修复内容

### 1. 修改 `novelgen/runtime/vector_store.py`

#### 变更 1.1：修改返回值类型
- **位置**：`VectorStoreManager.add_scene_content()` 方法
- **修改前**：返回 `List[str]`（chunk IDs）
- **修改后**：返回 `List[StoryMemoryChunk]`（完整的记忆块对象）
- **原因**：调用者需要完整的对象才能保存到数据库

```python
# 修改前
def add_scene_content(...) -> List[str]:
    ...
    return chunk_ids

# 修改后
def add_scene_content(...) -> List[StoryMemoryChunk]:
    ...
    # 更新 embedding_id
    for chunk, embedding_id in zip(chunks, chunk_ids):
        chunk.embedding_id = embedding_id
    return chunks
```

#### 变更 1.2：修复 ChromaDB 查询语法
- **位置**：`ChromaVectorStore.get_chunks_by_project()` 方法
- **问题**：多条件查询时 ChromaDB 报错
- **修复**：使用 `$and` 操作符正确组合查询条件

```python
# 修改前
where_clause = {"project_id": project_id}
if chapter_index is not None:
    where_clause["chapter_index"] = chapter_index

# 修改后
if chapter_index is not None:
    where_clause = {
        "$and": [
            {"project_id": {"$eq": project_id}},
            {"chapter_index": {"$eq": chapter_index}}
        ]
    }
else:
    where_clause = {"project_id": {"$eq": project_id}}
```

### 2. 修改 `novelgen/runtime/orchestrator.py`

#### 变更 2.1：同时保存到数据库
- **位置**：`NovelOrchestrator._save_scene_content_to_vector()` 方法
- **功能**：接收向量存储返回的记忆块，并同步保存到数据库

```python
def _save_scene_content_to_vector(self, content: str, chapter_index: int, scene_index: int):
    """保存场景内容到向量存储和数据库"""
    ...
    # 保存到向量存储，并获取创建的记忆块
    chunks = self.vector_manager.add_scene_content(...)
    
    # 同时保存到数据库的 memory_chunks 表
    if chunks and self.db_manager and self.db_manager.is_enabled():
        for chunk in chunks:
            self.db_manager.save_memory_chunk(chunk)
```

#### 变更 2.2：同步删除数据库记录
- **位置**：`NovelOrchestrator._delete_chapter_vector_memory()` 方法
- **功能**：删除章节时，同时清理向量库和数据库中的记忆块

```python
def _delete_chapter_vector_memory(self, chapter_index: int):
    """删除指定章节的所有向量记忆和数据库记录"""
    # 1. 从向量库删除
    ...
    
    # 2. 从数据库删除
    if self.db_manager and self.db_manager.is_enabled():
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM memory_chunks WHERE project_id = ? AND chapter_index = ?",
                (self.project_name, chapter_index)
            )
```

### 3. 更新测试代码

#### 修改 `novelgen/runtime/test_vector_store.py`
- 更新所有使用 `add_scene_content()` 的测试
- 将变量名从 `chunk_ids` 改为 `chunks`
- 增加对返回对象类型的验证
- 修复测试文本长度以确保分块

## 验证结果

### 单元测试
```bash
uv run python -m unittest novelgen.runtime.test_vector_store.TestVectorStoreManager -v
# 全部通过 ✅
```

### 集成测试
```bash
uv run python test_memory_chunks_db.py
# 输出：
✅ 数据库初始化成功
✅ 向量存储初始化成功
📦 向量存储创建了 1 个记忆块
✅ 已将 1 个记忆块保存到数据库
✅ 数据库记录数正确: 1
✅ 通过接口读取到 1 个记忆块
✅ 所有测试通过！memory_chunks 表工作正常
```

## 影响范围

### 修改的文件
1. `novelgen/runtime/vector_store.py` - 2处修改
2. `novelgen/runtime/orchestrator.py` - 2处修改
3. `novelgen/runtime/test_vector_store.py` - 4处测试更新

### 新增的文件
1. `test_memory_chunks_db.py` - 集成测试脚本

### 数据流变化
**修改前**：
```
场景生成 → 文本分块 → 向量库 (ChromaDB)
                      ❌ 数据库 (SQLite)
```

**修改后**：
```
场景生成 → 文本分块 → 向量库 (ChromaDB)
                    → ✅ 数据库 (SQLite)
```

## 设计意图符合度

根据 Phase1 设计文档验证：

✅ **符合规格要求**：`persistence/spec.md` 第18-22行明确要求"记录chunk与项目、章节、场景的关联关系"

✅ **符合数据模型**：`StoryMemoryChunk.embedding_id` 字段的存在表明需要双存储架构

✅ **符合阶段目标**：阶段1的目标是"建立数据存储基础"，为阶段2的查询功能做准备

✅ **向后兼容**：修改不影响现有生成流程，完全遵循降级处理原则

## 后续建议

1. **阶段2准备**：现在数据库已正确存储记忆块，可以开始实现阶段2的只读查询功能

2. **性能监控**：虽然增加了数据库写入，但由于采用了降级处理，对生成流程的影响可控

3. **数据一致性**：建议后续增加数据一致性检查工具，验证向量库和数据库的记忆块是否同步

4. **查询优化**：数据库的 `memory_chunks` 表已有索引，可支持高效的项目级和章节级查询

## 验证命令

```bash
# 运行向量存储测试
uv run python -m unittest novelgen.runtime.test_vector_store.TestVectorStoreManager -v

# 运行数据库写入测试
uv run python test_memory_chunks_db.py

# 查看实际项目的数据库（需要先运行完整生成流程）
sqlite3 projects/<project_name>/data/novel.db
> SELECT COUNT(*) FROM memory_chunks;
> SELECT chapter_index, scene_index, substr(content, 1, 50) FROM memory_chunks LIMIT 5;
```

---

**修复日期**：2025-11-18  
**修复人**：AI Assistant (Cascade)  
**版本**：Phase1 持久化功能补完
