# 开发环境搭建指南

## 前置依赖
- Python 3.10+（推荐用 `uv` 管理）
- Node.js 18+（用于前端）
- Redis（可用 docker-compose）

## 后端
```bash
# 安装依赖
uv sync
# 启动 API
UV_CACHE_DIR=.uv-cache uv run uvicorn novelgen.api.main:app --reload
```

环境变量（`.env`）：
- `OPENAI_API_KEY` 必填
- `REDIS_URL` 默认 `redis://localhost:6379/0`
- `NOVELGEN_PROJECTS_DIR` 默认 `projects`
- `MEM0_ENABLED` 可选

快速检查：
```bash
curl http://127.0.0.1:8000/health
```

## Celery Worker（异步任务）

### 启动 Worker
```bash
# 推荐方式：使用 solo pool 确保信号处理正常
uv run celery -A novelgen.tasks.celery_app worker -l info -Q generation --pool=solo

# 或者指定并发数（默认为 1）
uv run celery -A novelgen.tasks.celery_app worker -l info -Q generation --pool=solo -c 1
```

### 停止 Worker

**推荐方式：使用优雅停机工具**
```bash
# 优雅停机（等待任务自行检测停止标志后退出）
uv run python -m novelgen.tasks.worker_control shutdown

# 强制停机（立即终止运行中的任务）
uv run python -m novelgen.tasks.worker_control shutdown --force

# 指定等待超时（默认 30 秒）
uv run python -m novelgen.tasks.worker_control shutdown --timeout 60
```

**查看 Worker 状态**
```bash
# 列出活跃 Worker
uv run python -m novelgen.tasks.worker_control list

# 查看活跃任务
uv run python -m novelgen.tasks.worker_control status
```

### 停机行为说明

优雅停机流程：
1. **设置停止标志**：通知运行中的工作流停止
2. **标记进度**：将活跃项目状态设为 "stopping"
3. **广播 shutdown**：向所有 Worker 发送关闭信号
4. **等待退出**：等待 Worker 完成清理后退出
5. **最终状态**：将项目状态标记为 "stopped"

强制停机（`--force`）：
- 立即调用 `revoke(terminate=True)` 终止任务
- 任务会收到 SIGTERM 信号
- 状态会被标记为"任务被强制终止"

**注意**：
- 即使任务被中断，LangGraph 检查点已持久化，可通过"恢复"功能继续
- 使用 `--pool=solo` 确保信号能正确传递到任务进程
- Ctrl+C 在 solo pool 下也会触发优雅停机

## 前端
```bash
cd frontend
npm install
npm run dev  # http://127.0.0.1:5173
```

## Redis（docker-compose）
```bash
docker-compose up -d redis
```

## 常见问题
- uv 缓存权限：设置 `UV_CACHE_DIR=.uv-cache`
- WS 断线：前端已自动重连并回退 HTTP 轮询
- 缺少 @vitejs/plugin-react：已在 package.json 中声明，确保重新 `npm install`
- **Worker 无法停止**：使用 `python -m novelgen.tasks.worker_control shutdown --force` 强制停机
- **任务状态不一致**：检查 Redis 连接，重启 Worker 后状态会自动同步

