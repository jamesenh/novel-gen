# 数据查询CLI工具

本目录包含用于查询和验证NovelGen项目数据的命令行工具。

## 工具列表

### Mem0 管理工具

#### 1. check_mem0_health.py - Mem0 健康检查

检查 Mem0 连接状态和数据统计。

**使用示例**:

```bash
# 检查默认项目
uv run python scripts/check_mem0_health.py

# 检查指定项目
uv run python scripts/check_mem0_health.py --project demo_001
```

#### 2. export_mem0_to_json.py - Mem0 数据导出

导出 Mem0 记忆数据到 JSON 文件（用于备份）。

**使用示例**:

```bash
# 导出到默认文件名
uv run python scripts/export_mem0_to_json.py --project demo_001

# 导出到指定文件
uv run python scripts/export_mem0_to_json.py --project demo_001 --output backup.json
```

#### 3. clear_mem0_memory.py - Mem0 记忆清理

清空指定项目的 Mem0 记忆数据（用于测试）。

**警告**: 此操作不可逆！建议先导出备份。

**使用示例**:

```bash
# 交互式清理（需要确认）
uv run python scripts/clear_mem0_memory.py --project demo_001

# 直接清理（跳过确认）
uv run python scripts/clear_mem0_memory.py --project demo_001 --confirm
```

### 数据查询工具

#### 4. query_entity.py - 实体状态查询工具

查询指定项目中某个实体的状态信息。

#### 功能特性

- **最新状态查询**: 获取实体的最新状态快照
- **时间线查询**: 获取实体在整个故事中的状态变化历史
- **章节范围过滤**: 可以指定章节范围来查看特定阶段的状态
- **详细/简要模式**: 支持显示完整状态数据或关键字段摘要

#### 使用示例

```bash
# 查询实体最新状态
python scripts/query_entity.py my_project char_001 --latest

# 查询实体完整时间线
python scripts/query_entity.py my_project char_001 --timeline

# 查询指定章节范围的时间线
python scripts/query_entity.py my_project char_001 --timeline --start 1 --end 5

# 显示详细状态数据
python scripts/query_entity.py my_project char_001 --latest --verbose

# 使用自定义数据库路径
python scripts/query_entity.py my_project char_001 --latest --db /path/to/db.sqlite
```

#### 命令行参数

- `project_id`: 项目ID（必需）
- `entity_id`: 实体ID（必需）
- `--latest`: 查询最新状态
- `--timeline`: 查询时间线
- `--start N`: 起始章节索引
- `--end N`: 结束章节索引
- `--db PATH`: 数据库路径（默认从配置读取）
- `-v, --verbose`: 显示详细状态数据

#### 5. query_scene_memory.py - 场景记忆查询工具

查询指定场景或实体相关的记忆块。

#### 功能特性

- **场景记忆查询**: 获取特定场景的所有记忆块
- **实体关联查询**: 查找提及特定实体的记忆块
- **语义搜索**: 基于查询文本搜索相似记忆块
- **多维度过滤**: 支持按内容类型、实体、标签等维度过滤
- **数量限制**: 可控制返回结果数量

#### 使用示例

```bash
# 查询指定场景的记忆块
python scripts/query_scene_memory.py my_project --scene --chapter 1 --scene-index 0

# 根据实体查询相关记忆块
python scripts/query_scene_memory.py my_project --entity char_001 char_002

# 限定章节查询实体相关记忆
python scripts/query_scene_memory.py my_project --entity char_001 --chapter 1

# 搜索记忆块
python scripts/query_scene_memory.py my_project --search "主角决定离开"

# 带过滤条件的搜索
python scripts/query_scene_memory.py my_project --search "战斗" --content-type scene --entities char_001

# 限制返回数量并显示详细内容
python scripts/query_scene_memory.py my_project --chapter 1 --scene-index 0 --limit 5 --verbose

# 使用自定义向量存储路径
python scripts/query_scene_memory.py my_project --scene --chapter 1 --scene-index 0 --vector-store /path/to/chroma
```

#### 命令行参数

- `project_id`: 项目ID（必需）
- `--scene`: 按场景查询模式（需配合--chapter和--scene-index）
- `--entity ID [ID...]`: 按实体ID查询
- `--search QUERY`: 搜索记忆块
- `--chapter N`: 章节索引
- `--scene-index N`: 场景索引
- `--content-type TYPE`: 内容类型过滤
- `--entities ID [ID...]`: 实体过滤（用于搜索）
- `--tags TAG [TAG...]`: 标签过滤
- `--limit N`: 返回记忆块数量限制（默认10）
- `--vector-store PATH`: 向量存储路径（默认从配置读取）
- `-v, --verbose`: 显示完整内容

## 使用前提

1. 确保项目已正确配置数据库和向量存储路径
2. 数据库中已有实体状态快照或记忆块数据
3. 已安装所有必要的依赖（见项目根目录的requirements.txt）

## 配置说明

工具默认从 `novelgen.config.Settings` 读取数据库和向量存储路径。如果需要使用自定义路径，可以通过命令行参数指定。

## 典型工作流

### 1. 验证实体状态演变

```bash
# 查看角色在整个故事中的状态变化
python scripts/query_entity.py my_project char_protagonist --timeline --verbose

# 关注特定章节范围的状态
python scripts/query_entity.py my_project char_protagonist --timeline --start 5 --end 10
```

### 2. 检查场景记忆完整性

```bash
# 查看某个关键场景的记忆块
python scripts/query_scene_memory.py my_project --scene --chapter 3 --scene-index 5 --verbose

# 确认特定实体在该场景中的相关记忆
python scripts/query_scene_memory.py my_project --entity char_001 --chapter 3
```

### 3. 内容一致性检查

```bash
# 搜索包含特定情节点的记忆
python scripts/query_scene_memory.py my_project --search "魔法石失窃" --limit 20

# 查看与多个角色相关的互动记忆
python scripts/query_scene_memory.py my_project --entity char_hero char_villain
```

## 故障排查

### 常见问题

**问题**: "数据库未能成功初始化"
- 检查数据库文件是否存在
- 确认数据库路径配置正确
- 查看文件权限是否允许读取

**问题**: "向量存储未能成功初始化"
- 确认chromadb已安装: `pip install chromadb`
- 检查向量存储目录是否存在
- 查看是否有写入权限

**问题**: "未找到实体/记忆块"
- 确认project_id和entity_id/章节索引正确
- 检查数据是否已通过生成流程写入
- 使用`--verbose`查看更多诊断信息

## 扩展开发

如需添加新的查询功能，可参考现有工具的结构：

1. 从`novelgen.runtime.db`或`novelgen.runtime.vector_store`导入管理器
2. 使用argparse定义命令行接口
3. 实现查询逻辑并格式化输出
4. 添加错误处理和用户友好的提示信息

## 反馈与建议

如果这些工具在使用中遇到问题或有改进建议，请记录issue或提交PR。
