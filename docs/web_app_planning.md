# NovelGen Web 应用功能规划

## 一、当前功能概览

### 1.1 核心生成流程（6步）

| 步骤 | 功能 | 输入 | 输出 |
|------|------|------|------|
| 1. 世界观生成 | 根据描述生成完整世界设定 | world_description | world.json |
| 2. 主题冲突 | 生成核心主题与冲突 | theme_description + world | theme_conflict.json |
| 3. 角色创建 | 生成主角、反派、配角 | world + theme_conflict | characters.json |
| 4. 大纲生成 | 生成故事结构与章节摘要 | 上述所有 | outline.json |
| 5. 章节计划 | 每章拆分为多个场景 | outline | chapter_XXX_plan.json |
| 6. 场景生成 | 生成实际小说文本 | 章节计划 + 上下文 | chapter_XXX.json |

### 1.2 辅助功能

| 功能 | 描述 |
|------|------|
| 一致性检查 | 检测生成内容的逻辑/角色一致性 |
| 章节修订 | 根据一致性报告自动/手动修订 |
| 动态章节扩展 | 评估剧情进度，动态扩展大纲 |
| 断点续跑 | LangGraph 检查点支持中断恢复 |
| 导出 | 导出为 txt 格式 |
| 回滚 | 回滚到指定步骤/章节 |

### 1.3 CLI 命令

```bash
ng init <project>    # 创建项目
ng run <project>     # 运行生成
ng resume <project>  # 恢复生成
ng status <project>  # 查看状态
ng state <project>   # 详细状态
ng export <project>  # 导出
ng rollback <project> --step/--chapter  # 回滚
ng chat <project>    # 对话式 Agent

# 世界观/主题冲突候选（可选但推荐）
ng world-variants <project> --prompt "修仙世界" --expand
ng world-select <project> variant_1
ng world-show <project>
ng theme-variants <project> --direction "复仇"
ng theme-select <project> variant_1
ng theme-show <project>

# 图谱（可选）
ng graph rebuild <project>
ng graph whois <project> <name>
ng graph relations <project> <name> --with <name>
ng graph events <project> [name] --chapter <N>
ng graph stats <project>
```

---

## 二、Web 应用功能拆分

### 2.1 项目管理模块

**适合 Web 的功能：**
- ✅ 项目列表展示（所有已创建项目）
- ✅ 创建新项目（交互式表单）
- ✅ 删除项目
- ✅ 项目详情页面

**Web 展示优势：**
- 可视化项目卡片
- 搜索和筛选
- 批量操作

### 2.2 生成流程控制模块

**适合 Web 的功能：**
- ✅ 一键生成整本小说
- ✅ 分步生成（可选停止点）
- ✅ 实时进度展示
- ✅ 生成日志查看
- ✅ 中断/恢复生成
- ✅ 回滚操作（选择回滚点）

**技术考虑：**
- WebSocket 实时推送进度
- 后台任务队列处理生成
- 生成状态持久化

### 2.3 内容展示模块

**适合 Web 的功能：**

**世界观展示：**
- ✅ 结构化展示世界设定各字段
- ✅ 编辑和重新生成

**角色展示：**
- ✅ 角色卡片列表
- ✅ 角色关系图谱（可视化）
- ✅ 角色详情页

**大纲展示：**
- ✅ 故事结构概览
- ✅ 章节列表（可折叠）
- ✅ 章节依赖可视化

**章节阅读：**
- ✅ 章节选择器
- ✅ 场景导航
- ✅ 阅读进度追踪
- ✅ 全书阅读模式

### 2.4 编辑与修订模块

**适合 Web 的功能：**
- ✅ 世界观/角色/大纲在线编辑
- ✅ 一致性问题列表展示
- ✅ 修订候选对比（diff view）
- ✅ 接受/拒绝修订
- ✅ 手动编辑章节内容

### 2.5 导出模块

**适合 Web 的功能：**
- ✅ 导出为 TXT（单章/全书）
- ✅ 导出为 EPUB（需新增）
- ✅ 导出为 PDF（需新增）
- ✅ 下载生成文件

### 2.6 统计与分析模块

**适合 Web 的功能：**
- ✅ 项目生成统计
- ✅ 字数统计（每章/总计）
- ✅ 生成时间统计
- ✅ 一致性问题分布图表

---

## 三、技术架构建议

### 3.1 后端架构

**选项 A: FastAPI（推荐）**
```
novelgen/
├── api/                    # API 层
│   ├── routes/             # 路由
│   │   ├── projects.py
│   │   ├── generation.py
│   │   ├── content.py
│   │   └── export.py
│   ├── schemas/            # Pydantic 请求/响应模型
│   └── deps.py             # 依赖注入
├── services/               # 业务逻辑（复用现有 chains/runtime）
├── tasks/                  # 后台任务
│   └── generation_tasks.py
└── websockets/             # WebSocket 处理
    └── progress.py
```

**核心组件：**
- FastAPI 提供 REST API
- Celery + Redis 处理生成任务
- WebSocket 推送实时进度
- SQLite/PostgreSQL 存储项目元数据

### 3.2 前端架构

**选项 A: React + TypeScript（推荐）**
```
frontend/
├── pages/                  # 页面
│   ├── projects/           # 项目管理
│   ├── generation/         # 生成控制
│   ├── reader/             # 阅读器
│   └── settings/           # 设置
├── components/             # 组件
│   ├── WorldCard.tsx
│   ├── CharacterCard.tsx
│   ├── OutlineTree.tsx
│   └── ChapterReader.tsx
├── hooks/                  # 自定义 Hooks
├── services/               # API 调用
└── store/                  # 状态管理
```

**选项 B: Vue 3 + TypeScript**
类似结构，使用 Composition API

### 3.3 数据流

```
用户操作 → API 请求 → 后端处理
                        ↓
                   任务队列
                        ↓
            LangGraph 工作流执行
                        ↓
                 WebSocket 推送
                        ↓
                   前端更新
```

---

## 四、功能优先级建议

### Phase 1：核心功能（MVP）
1. 项目列表/创建/删除
2. 完整生成流程（一键生成）
3. 生成进度展示
4. 基础内容阅读
5. TXT 导出

### Phase 2：增强体验
1. 分步生成控制
2. 实时日志查看
3. 世界观/角色/大纲展示
4. 断点续跑

### Phase 3：高级功能
1. 内容编辑
2. 一致性问题管理
3. 修订对比
4. 回滚功能
5. 更多导出格式

### Phase 4：扩展功能
1. 角色关系图谱
2. 统计分析仪表板
3. 多用户支持
4. 项目模板

---

## 五、需要讨论的问题

1. **技术栈选择**
   - 后端：FastAPI vs Django vs Flask？
   - 前端：React vs Vue vs 其他？
   - 任务队列：Celery vs RQ vs 其他？

2. **部署方式**
   - 本地部署 vs 云端部署？
   - Docker 容器化？
   - 多用户支持需求？

3. **功能范围**
   - MVP 应该包含哪些功能？
   - 有哪些功能是 CLI 独有不需要迁移的？

4. **用户体验**
   - 生成过程是同步等待还是异步通知？
   - 需要用户认证吗？

5. **与现有 CLI 的关系**
   - Web 是完全替代 CLI 还是并存？
   - API 层如何复用现有代码？
