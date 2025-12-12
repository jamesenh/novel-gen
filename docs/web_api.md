# Web API 速览

## 基础
- Base URL: `http://127.0.0.1:8000`
- 错误格式：`{"detail": "...", "error_code": "HTTP_ERROR"}`（未捕获为 `SERVER_ERROR`）

## 项目管理
- `GET /api/projects` 列表
- `POST /api/projects` 创建 `{project_name, world_description, theme_description?, initial_chapters?}`
- `GET /api/projects/{name}` 详情
- `DELETE /api/projects/{name}` 删除
- `GET /api/projects/{name}/state` 状态与章节元数据

## 生成控制
- `POST /api/projects/{name}/generate` 开始 `{stop_at?}`
- `POST /api/projects/{name}/generate/resume` 恢复
- `POST /api/projects/{name}/generate/stop` 停止
- `GET /api/projects/{name}/generate/status` 状态
- `GET /api/projects/{name}/generate/progress` 进度快照
- `GET /api/projects/{name}/generate/logs` 日志
- `WS /ws/projects/{name}/progress` 实时进度/日志推送

## 内容读取
- `GET /api/projects/{name}/world`
- `GET /api/projects/{name}/theme_conflict`
- `GET /api/projects/{name}/characters`
- `GET /api/projects/{name}/outline`
- `GET /api/projects/{name}/chapters`
- `GET /api/projects/{name}/chapters/{num}`

## 内容编辑
- `PUT /api/projects/{name}/world` 任意键值
- `PUT /api/projects/{name}/theme_conflict` 任意键值
- `PUT /api/projects/{name}/characters` 任意键值（含 protagonist/antagonist/supporting_characters）
- `PUT /api/projects/{name}/outline` 任意键值
- `PUT /api/projects/{name}/chapters/{num}` `{chapter_title?, scenes:[{scene_number, content, word_count?}]}` 自动重算字数
- `DELETE /api/projects/{name}/chapters/{num}` 删除整章
- `DELETE /api/projects/{name}/chapters/{num}?scene=X` 删除单场景

## 内容生成（LLM 多候选）
- `POST /api/projects/{name}/content/generate`
  - 请求：`{target: "world"|"theme"|"characters"|"outline", user_prompt?, num_variants?, num_characters?, expand?}`
  - 返回：`{target, variants: [{variant_id, style_tag, brief_description, payload}], generated_at}`
  - world/theme 使用 `num_variants`（默认 3），characters 使用 `num_characters`（默认由环境变量 `CHARACTERS_DEFAULT_COUNT` 控制，未设置时为 5，范围 3-12），outline 当前返回单候选
  - theme 需先有 world.json，characters 需 world+theme，outline 需 world+theme+characters

## 回滚
- `POST /api/projects/{name}/rollback`
  - `step`：world_creation/theme_conflict_creation/character_creation/outline_creation/chapter_planning/chapter_generation
  - `chapter` / `scene`：按章节/场景回滚
  - 返回 `deleted_files`、`cleared_memories`、`files`

## 导出
- 全书：`GET /api/projects/{name}/export/txt|md|json`
- 单章：`GET /api/projects/{name}/export/txt|md|json/{chapter_num}`

