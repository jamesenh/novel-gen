# NovelGen 快速开始

本文档目标：在本地从 0 跑通一次“初始化项目 → 生成 → 断点恢复 → 导出”，并可选体验 `ng chat` 与图谱查询。

## 1. 安装依赖

推荐使用 `uv`：

```bash
uv sync
```

或使用 `pip`：

```bash
pip install -r requirements.txt
```

## 2. 配置环境变量

```bash
cp .env.template .env
```

编辑 `.env`，至少配置：

- `OPENAI_API_KEY=...`

更多可选项见：`docs/ENV_SETUP.md`。

## 3. 初始化项目（交互式）

```bash
ng init demo_001
```

说明：
- 默认会询问是否生成“世界观候选/主题冲突候选”供选择。
- 生成类动作会写入 `projects/demo_001/`。

## 4. 运行工作流（可指定停止点）

完整运行：

```bash
ng run demo_001
```

仅生成到大纲（示例）：

```bash
ng run demo_001 --stop-at outline
```

## 5. 断点恢复

当运行中断（Ctrl+C 或异常）后，可直接恢复：

```bash
ng resume demo_001
```

## 6. 查看状态 / 导出

```bash
ng status demo_001
ng state demo_001
ng export demo_001
```

## 7. 对话式 Agent（可选）

```bash
ng chat demo_001
```

常用命令（对话中）：

- `/status` 查看状态
- `/run` 开始生成（默认需要确认）
- `/resume` 继续生成（默认需要确认）
- `/whois 角色名` 查询角色信息（需图谱可用）
- `/relations 角色名 --with 另一个角色` 查询关系
- `/events 角色名` 查询事件
- `/setpref 轻松幽默、少形容词、多心理描写` 设置偏好（需 Mem0 启用）
- `/auto on|off` 开关自动确认（破坏性操作仍需确认）

详情见：`docs/对话式Agent使用指南.md`。

## 8. 知识图谱（可选）

默认开启图谱（可通过 `NOVELGEN_GRAPH_ENABLED=false` 关闭）。

全量重建（从 JSON 导入角色/关系/章节/事件）：

```bash
ng graph rebuild demo_001
```

查询示例：

```bash
ng graph whois demo_001 林风
ng graph relations demo_001 林风 --with 师父
ng graph events demo_001 林风
ng graph stats demo_001
```

详情见：`docs/知识图谱使用指南.md`。

