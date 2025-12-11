"""
Celery Worker 控制模块

提供 worker 优雅停机功能：
1. 设置停止标志通知运行中的任务
2. 更新 Redis 进度状态
3. 广播 shutdown 信号给所有 worker
4. 可选强制终止运行中的任务

开发者: jamesenh
日期: 2025-12-08
"""
import argparse
import sys
import time
from typing import Optional

import redis

from novelgen.runtime.mem0_manager import request_shutdown
from novelgen.services.generation_service import (
    _redis,
    get_active_task,
    save_progress,
    clear_active_task,
    ACTIVE_KEY,
)
from novelgen.tasks.celery_app import celery_app


def get_all_active_projects() -> list[str]:
    """扫描 Redis 获取所有活跃任务对应的项目名

    Returns:
        项目名称列表
    """
    client = _redis()
    # 扫描所有 active_task:* 键
    pattern = ACTIVE_KEY.format(project="*")
    keys = client.keys(pattern)
    projects = []
    for key in keys:
        # 从 key 中提取项目名
        # key 格式: active_task:{project}
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        project_name = key.replace("active_task:", "")
        projects.append(project_name)
    return projects


def mark_stopping_progress(project_name: str, message: str = "正在停止..."):
    """标记项目进度为正在停止

    Args:
        project_name: 项目名称
        message: 停止消息
    """
    save_progress(
        project_name,
        {
            "status": "stopping",
            "message": message,
            "progress_percent": 0.0,
        },
    )


def mark_stopped_progress(project_name: str, message: str = "已停止"):
    """标记项目进度为已停止

    Args:
        project_name: 项目名称
        message: 停止消息
    """
    save_progress(
        project_name,
        {
            "status": "stopped",
            "message": message,
            "progress_percent": 0.0,
        },
    )
    clear_active_task(project_name)


def graceful_shutdown_workers(force: bool = False, timeout: float = 30.0) -> bool:
    """优雅停止所有 Celery worker

    执行步骤：
    1. 设置全局停止标志 (request_shutdown)
    2. 扫描所有活跃项目，标记进度为 "stopping"
    3. 如果 force=True，revoke 所有运行中的任务
    4. 广播 shutdown 信号给所有 worker
    5. 等待 worker 退出或超时

    Args:
        force: 是否强制终止运行中的任务（默认 False，等待任务自行检测停止标志）
        timeout: 等待 worker 退出的超时时间（秒）

    Returns:
        bool: 是否成功发送停机信号
    """
    print("🛑 开始优雅停机流程...")

    # 1. 设置全局停止标志
    print("   📍 设置停止标志...")
    request_shutdown()

    # 2. 扫描活跃项目并标记进度
    active_projects = get_all_active_projects()
    if active_projects:
        print(f"   📋 发现 {len(active_projects)} 个活跃项目: {', '.join(active_projects)}")
        for project in active_projects:
            mark_stopping_progress(project, "收到停机信号，正在保存状态...")
    else:
        print("   📋 无活跃任务")

    # 3. 如果强制模式，revoke 所有任务
    if force:
        print("   ⚡ 强制模式：终止所有运行中的任务...")
        for project in active_projects:
            active = get_active_task(project)
            if active and active.get("task_id"):
                task_id = active["task_id"]
                print(f"      🔸 终止任务 {task_id} (项目: {project})")
                try:
                    celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
                except Exception as e:
                    print(f"      ⚠️ 终止任务失败: {e}")
                # 标记为已停止
                mark_stopped_progress(project, "任务被强制终止")

    # 4. 广播 shutdown 信号
    print("   📡 广播 shutdown 信号给所有 worker...")
    try:
        celery_app.control.broadcast("shutdown")
        print("   ✅ shutdown 信号已发送")
    except Exception as e:
        print(f"   ❌ 发送 shutdown 信号失败: {e}")
        return False

    # 5. 等待确认（可选）
    if timeout > 0:
        print(f"   ⏳ 等待 worker 退出 (最多 {timeout}s)...")
        start = time.time()
        while time.time() - start < timeout:
            # 检查是否还有活跃的 worker
            try:
                ping_result = celery_app.control.ping(timeout=2.0)
                if not ping_result:
                    print("   ✅ 所有 worker 已退出")
                    break
                active_workers = len(ping_result)
                print(f"      ... 仍有 {active_workers} 个 worker 运行中")
            except Exception:
                # ping 失败可能意味着 worker 已退出
                print("   ✅ worker 已退出（无响应）")
                break
            time.sleep(2.0)
        else:
            print(f"   ⚠️ 超时 ({timeout}s)，部分 worker 可能仍在运行")

    # 最终标记所有项目为已停止
    for project in active_projects:
        active = get_active_task(project)
        if active:
            mark_stopped_progress(project, "worker 已停机")

    print("🛑 停机流程完成")
    return True


def list_workers() -> list[dict]:
    """列出当前活跃的 worker

    Returns:
        worker 信息列表
    """
    try:
        ping_result = celery_app.control.ping(timeout=5.0)
        if not ping_result:
            return []
        workers = []
        for item in ping_result:
            for worker_name, response in item.items():
                workers.append({
                    "name": worker_name,
                    "status": "ok" if response.get("ok") == "pong" else "unknown",
                })
        return workers
    except Exception as e:
        print(f"❌ 获取 worker 列表失败: {e}")
        return []


def list_active_tasks() -> list[dict]:
    """列出当前活跃的任务

    Returns:
        活跃任务列表
    """
    projects = get_all_active_projects()
    tasks = []
    for project in projects:
        active = get_active_task(project)
        if active:
            tasks.append({
                "project": project,
                "task_id": active.get("task_id"),
                "started_at": active.get("started_at"),
            })
    return tasks


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="Celery Worker 控制工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m novelgen.tasks.worker_control shutdown        # 优雅停机
  python -m novelgen.tasks.worker_control shutdown --force  # 强制停机
  python -m novelgen.tasks.worker_control status          # 查看状态
  python -m novelgen.tasks.worker_control list            # 列出 worker
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # shutdown 子命令
    shutdown_parser = subparsers.add_parser("shutdown", help="停止所有 worker")
    shutdown_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制终止运行中的任务（不等待任务自行退出）",
    )
    shutdown_parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=30.0,
        help="等待 worker 退出的超时时间（秒，默认 30）",
    )

    # status 子命令
    subparsers.add_parser("status", help="查看活跃任务状态")

    # list 子命令
    subparsers.add_parser("list", help="列出活跃 worker")

    args = parser.parse_args()

    if args.command == "shutdown":
        success = graceful_shutdown_workers(force=args.force, timeout=args.timeout)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        print("📊 活跃任务状态:")
        tasks = list_active_tasks()
        if not tasks:
            print("   无活跃任务")
        else:
            for task in tasks:
                print(f"   🔸 项目: {task['project']}")
                print(f"      任务 ID: {task['task_id']}")
                print(f"      启动时间: {task['started_at']}")

    elif args.command == "list":
        print("👷 活跃 Worker:")
        workers = list_workers()
        if not workers:
            print("   无活跃 worker")
        else:
            for w in workers:
                status_icon = "✅" if w["status"] == "ok" else "❓"
                print(f"   {status_icon} {w['name']}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

