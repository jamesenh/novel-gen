"""
生成控制服务

封装 Celery 任务调度、进度持久化与日志管理，供 API 层调用。

开发者: jamesenh
日期: 2025-12-08
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import redis
from celery.result import AsyncResult

from novelgen.runtime.mem0_manager import request_shutdown, reset_shutdown
from novelgen.tasks.celery_app import celery_app

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PROGRESS_KEY = "generation_progress:{project}"
LOG_KEY = "generation_logs:{project}"
ACTIVE_KEY = "active_task:{project}"
PROGRESS_CHANNEL = "generation_progress_channel:{project}"
LOG_CHANNEL = "generation_logs_channel:{project}"
LOG_LIMIT = 200

TASK_GENERATE = "novelgen.tasks.generation_tasks.generate_novel"
TASK_RESUME = "novelgen.tasks.generation_tasks.resume_novel"


def _redis() -> redis.Redis:
    """获取同步 Redis 客户端"""
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _progress_key(project_name: str) -> str:
    return PROGRESS_KEY.format(project=project_name)


def _log_key(project_name: str) -> str:
    return LOG_KEY.format(project=project_name)


def _active_key(project_name: str) -> str:
    return ACTIVE_KEY.format(project=project_name)


def _progress_channel(project_name: str) -> str:
    return PROGRESS_CHANNEL.format(project=project_name)


def _log_channel(project_name: str) -> str:
    return LOG_CHANNEL.format(project=project_name)


def set_active_task(project_name: str, task_id: str):
    """记录活跃任务"""
    client = _redis()
    payload = {"task_id": task_id, "started_at": _now_iso()}
    client.set(_active_key(project_name), json.dumps(payload))


def clear_active_task(project_name: str):
    """清理活跃任务记录"""
    client = _redis()
    client.delete(_active_key(project_name))


def clear_runtime_state(project_name: str) -> int:
    """
    清理 Redis 中的运行时状态（active/progress/logs）

    Returns:
        被删除的键数量
    """
    client = _redis()
    keys = [_active_key(project_name), _progress_key(project_name), _log_key(project_name)]
    removed = client.delete(*keys)
    return int(removed)


def reset_runtime_state(project_name: str, message: str = "已回滚") -> int:
    """
    回滚后重置运行态：删除旧状态并写入空进度

    Returns:
        删除的键数量
    """
    removed = clear_runtime_state(project_name)
    save_progress(
        project_name,
        {
            "status": "idle",
            "progress_percent": 0.0,
            "message": message,
            "current_step": None,
            "current_chapter": None,
            "current_scene": None,
        },
    )
    return removed


def get_active_task(project_name: str) -> Optional[Dict[str, Any]]:
    """读取活跃任务信息"""
    client = _redis()
    raw = client.get(_active_key(project_name))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def save_progress(project_name: str, data: Dict[str, Any]):
    """保存进度快照并推送到频道"""
    client = _redis()
    snapshot = {
        "status": data.get("status", "running"),
        "current_step": data.get("current_step"),
        "current_chapter": data.get("current_chapter"),
        "current_scene": data.get("current_scene"),
        "progress_percent": float(data.get("progress_percent", 0.0)),
        "message": data.get("message"),
        "updated_at": _now_iso(),
    }
    serialized = json.dumps(snapshot)
    client.set(_progress_key(project_name), serialized)
    client.publish(_progress_channel(project_name), serialized)


def read_progress(project_name: str) -> Dict[str, Any]:
    """读取进度快照"""
    client = _redis()
    raw = client.get(_progress_key(project_name))
    if not raw:
        return {
            "status": "idle",
            "progress_percent": 0.0,
            "message": "未找到任务",
            "current_step": None,
            "current_chapter": None,
            "current_scene": None,
        }
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "status": "idle",
            "progress_percent": 0.0,
            "message": "进度数据损坏",
        }


def append_log(project_name: str, level: str, message: str, context: Optional[Dict[str, Any]] = None):
    """记录日志并推送"""
    client = _redis()
    entry = {
        "timestamp": _now_iso(),
        "level": level,
        "message": message,
        "context": context or {},
    }
    serialized = json.dumps(entry, ensure_ascii=False)
    key = _log_key(project_name)
    client.lpush(key, serialized)
    client.ltrim(key, 0, LOG_LIMIT - 1)
    client.publish(_log_channel(project_name), serialized)


def read_logs(project_name: str, limit: int = 50):
    """读取最新日志"""
    client = _redis()
    entries = client.lrange(_log_key(project_name), 0, max(limit - 1, 0))
    items = []
    for raw in entries:
        try:
            items.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return items


def start_generation(project_name: str, stop_at: Optional[str], verbose: bool, show_prompt: bool) -> str:
    """
    启动生成任务

    Raises:
        ValueError: 当已有活跃任务时
    """
    if get_active_task(project_name):
        raise ValueError("当前已有生成任务在运行")

    reset_shutdown()
    task = celery_app.send_task(
        TASK_GENERATE,
        args=[project_name],
        kwargs={"stop_at": stop_at, "verbose": verbose, "show_prompt": show_prompt},
        queue="generation",
    )
    set_active_task(project_name, task.id)
    save_progress(project_name, {"status": "running", "message": "任务已提交", "progress_percent": 1.0})
    return task.id


def resume_generation(project_name: str) -> str:
    """恢复生成任务"""
    if get_active_task(project_name):
        raise ValueError("当前已有生成任务在运行")

    reset_shutdown()
    task = celery_app.send_task(TASK_RESUME, args=[project_name], queue="generation")
    set_active_task(project_name, task.id)
    save_progress(project_name, {"status": "running", "message": "恢复任务已提交", "progress_percent": 1.0})
    return task.id


def stop_generation(project_name: str) -> Optional[str]:
    """停止当前任务"""
    active = get_active_task(project_name)
    if not active:
        return None
    task_id = active.get("task_id")
    request_shutdown()
    if task_id:
        celery_app.control.revoke(task_id, terminate=True)
    save_progress(project_name, {"status": "stopped", "message": "任务已停止", "progress_percent": 0.0})
    clear_active_task(project_name)
    return task_id


def get_status(project_name: str) -> Dict[str, Any]:
    """获取任务状态"""
    active = get_active_task(project_name)
    if not active:
        progress = read_progress(project_name)
        return {"status": progress.get("status", "idle"), "task_id": None, "detail": progress.get("message")}

    task_id = active.get("task_id")
    result = AsyncResult(task_id, app=celery_app)
    state = result.state.lower() if result.state else "running"
    detail = None
    if state == "failure":
        detail = str(result.info)
    return {"status": state, "task_id": task_id, "detail": detail}


