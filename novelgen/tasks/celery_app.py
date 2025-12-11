"""
Celery 应用配置

提供:
1. Celery 应用实例
2. Worker 信号处理（优雅停机）
3. OS 信号处理（SIGTERM/SIGINT）

开发者: jamesenh
日期: 2025-12-08
更新: 2025-12-08 - 添加信号处理支持优雅停机
"""
import os
import signal
import logging

from celery import Celery
from celery.signals import worker_shutting_down, worker_shutdown

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "novelgen",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["novelgen.tasks.generation_tasks"],
)

# 基础配置：单队列、JSON 序列化、限制并发
# 使用 solo pool 确保信号可以正确传递到任务
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="generation",
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
    # 使用 solo pool 以便信号能够传递到主进程
    # 这对于优雅停机至关重要
    worker_pool="solo",
    # 在收到 SIGTERM 后等待任务完成的时间（秒）
    worker_cancel_long_running_tasks_on_connection_loss=True,
)


# ==================== Celery Worker 信号处理 ====================

@worker_shutting_down.connect
def handle_worker_shutting_down(sig, how, exitcode, **kwargs):
    """Worker 正在关闭时的处理

    当 worker 收到 shutdown 信号时触发，设置停止标志通知运行中的任务。
    """
    logger.warning("⚠️ Worker 正在关闭 (signal=%s, how=%s, exitcode=%s)", sig, how, exitcode)
    print(f"\n⚠️ Worker 正在关闭...")

    try:
        # 导入并设置停止标志
        from novelgen.runtime.mem0_manager import request_shutdown
        request_shutdown()
        logger.info("✅ 已设置停止标志")

        # 标记所有活跃项目为正在停止
        from novelgen.tasks.worker_control import (
            get_all_active_projects,
            mark_stopping_progress,
        )
        active_projects = get_all_active_projects()
        for project in active_projects:
            mark_stopping_progress(project, "Worker 正在关闭，保存状态中...")
            logger.info(f"📍 项目 {project} 已标记为正在停止")

    except Exception as e:
        logger.error(f"❌ 处理 worker_shutting_down 信号时出错: {e}")


@worker_shutdown.connect
def handle_worker_shutdown(sender, **kwargs):
    """Worker 已关闭时的处理

    当 worker 完全关闭时触发，清理所有活跃任务状态。
    """
    logger.info("🛑 Worker 已关闭")
    print("🛑 Worker 已关闭")

    try:
        from novelgen.tasks.worker_control import (
            get_all_active_projects,
            mark_stopped_progress,
        )
        active_projects = get_all_active_projects()
        for project in active_projects:
            mark_stopped_progress(project, "Worker 已停机")
            logger.info(f"📍 项目 {project} 已标记为已停止")

    except Exception as e:
        logger.error(f"❌ 处理 worker_shutdown 信号时出错: {e}")


# ==================== OS 信号处理 ====================

_original_sigterm_handler = None
_original_sigint_handler = None


def _graceful_signal_handler(signum, frame):
    """统一的信号处理器

    处理 SIGTERM 和 SIGINT 信号，设置停止标志并通知任务。
    """
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.warning(f"⚠️ 收到 {signal_name} 信号，开始优雅停机...")
    print(f"\n⚠️ 收到 {signal_name} 信号，开始优雅停机...")

    try:
        # 设置停止标志
        from novelgen.runtime.mem0_manager import request_shutdown
        request_shutdown()

        # 标记活跃项目
        from novelgen.tasks.worker_control import (
            get_all_active_projects,
            mark_stopping_progress,
        )
        for project in get_all_active_projects():
            mark_stopping_progress(project, f"收到 {signal_name} 信号，正在保存...")

    except Exception as e:
        logger.error(f"❌ 处理 {signal_name} 信号时出错: {e}")

    # 调用原始处理器（让 Celery 继续其正常关闭流程），若无可调用处理器则主动抛出中断
    # 避免第一次 Ctrl+C 仅设置标志但不退出的情况
    if signum == signal.SIGTERM:
        if callable(_original_sigterm_handler):
            _original_sigterm_handler(signum, frame)
        else:
            raise SystemExit(0)
    elif signum == signal.SIGINT:
        if callable(_original_sigint_handler):
            _original_sigint_handler(signum, frame)
        else:
            raise KeyboardInterrupt()


def setup_signal_handlers():
    """设置 OS 信号处理器

    在 worker 启动时调用，确保 SIGTERM 和 SIGINT 能够触发优雅停机。
    """
    global _original_sigterm_handler, _original_sigint_handler

    try:
        _original_sigterm_handler = signal.signal(signal.SIGTERM, _graceful_signal_handler)
        _original_sigint_handler = signal.signal(signal.SIGINT, _graceful_signal_handler)
        logger.info("✅ OS 信号处理器已设置")
    except Exception as e:
        logger.warning(f"⚠️ 设置信号处理器失败: {e}")


# 在模块加载时设置信号处理器
# 注意：这会在 worker 进程中生效
setup_signal_handlers()


