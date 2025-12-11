"""
生成相关 Celery 任务

提供:
1. generate_novel - 完整生成流程
2. resume_novel - 从检查点恢复生成

特性:
- 支持优雅停机（响应停止标志）
- 中断时自动保存进度
- 确保 orchestrator 资源清理

开发者: jamesenh
日期: 2025-12-08
更新: 2025-12-08 - 增强中断处理，确保状态持久化
"""
import os
import sys
from typing import Optional

from celery import states
from celery.exceptions import SoftTimeLimitExceeded, WorkerLostError
from celery.utils.log import get_task_logger

from novelgen.runtime.mem0_manager import is_shutdown_requested, request_shutdown, reset_shutdown
from novelgen.runtime.orchestrator import NovelOrchestrator
from novelgen.runtime.workflow import get_default_recursion_limit
from novelgen.services.generation_service import (
    append_log,
    clear_active_task,
    save_progress,
)
from novelgen.tasks.celery_app import celery_app

logger = get_task_logger(__name__)

TASK_GENERATE = "novelgen.tasks.generation_tasks.generate_novel"
TASK_RESUME = "novelgen.tasks.generation_tasks.resume_novel"


def _publish_progress(project_name: str, node_name: str, step_index: int):
    """根据节点执行顺序推算粗略进度"""
    percent = min(95.0, step_index * 5.0)
    save_progress(
        project_name,
        {
            "status": "running",
            "current_step": node_name,
            "progress_percent": percent,
            "message": f"节点 {node_name} 已完成",
        },
    )
    append_log(project_name, "INFO", f"节点 {node_name} 完成")


def _safe_cleanup(orchestrator: Optional[NovelOrchestrator], project_name: str):
    """安全清理 orchestrator 资源

    确保即使在异常情况下也能正确清理资源。

    Args:
        orchestrator: NovelOrchestrator 实例
        project_name: 项目名称（用于日志）
    """
    if orchestrator:
        try:
            orchestrator.cleanup()
            logger.info(f"✅ 项目 {project_name} 资源已清理")
        except Exception as cleanup_err:
            logger.warning(f"⚠️ cleanup 失败: {cleanup_err}", exc_info=True)


def _handle_interruption(
    project_name: str,
    orchestrator: Optional[NovelOrchestrator],
    reason: str,
    exc_type: str,
):
    """处理任务中断

    统一处理各种中断情况，确保:
    1. 保存进度状态为 "stopped"
    2. 记录中断日志
    3. 清理 orchestrator 资源
    4. 清理活跃任务记录

    Args:
        project_name: 项目名称
        orchestrator: NovelOrchestrator 实例
        reason: 中断原因描述
        exc_type: 异常类型名称
    """
    logger.warning(f"⚠️ 任务中断 ({exc_type}): {reason}")

    # 保存停止状态
    try:
        save_progress(
            project_name,
            {
                "status": "stopped",
                "message": reason,
                "progress_percent": 0.0,
            },
        )
        append_log(project_name, "WARNING", f"任务被中断: {reason}")
    except Exception as save_err:
        logger.error(f"❌ 保存中断状态失败: {save_err}")

    # 清理资源
    _safe_cleanup(orchestrator, project_name)

    # 清理活跃任务记录
    try:
        clear_active_task(project_name)
    except Exception as clear_err:
        logger.error(f"❌ 清理活跃任务记录失败: {clear_err}")


@celery_app.task(name=TASK_GENERATE, bind=True)
def generate_novel(self, project_name: str, stop_at: Optional[str] = None, verbose: bool = False, show_prompt: bool = False):
    """
    触发完整生成流程

    支持优雅停机:
    - 定期检查停止标志
    - 响应 KeyboardInterrupt/SystemExit
    - 中断时保存进度并清理资源
    """
    reset_shutdown()
    append_log(project_name, "INFO", f"开始生成项目 {project_name}")
    save_progress(project_name, {"status": "running", "progress_percent": 1.0, "message": "任务已启动"})
    orchestrator: Optional[NovelOrchestrator] = None
    step_index = 0

    try:
        orchestrator = NovelOrchestrator(project_name, verbose=verbose, show_prompt=show_prompt)
        initial_state = orchestrator._get_or_create_workflow_state()
        recursion_limit = initial_state.recursion_limit if initial_state else get_default_recursion_limit()
        config = {"configurable": {"thread_id": project_name}, "recursion_limit": recursion_limit}

        for state in orchestrator.workflow.stream(initial_state, config):
            # 检查停止标志
            if is_shutdown_requested():
                logger.info(f"📍 项目 {project_name} 收到停止请求，正在保存状态...")
                save_progress(project_name, {"status": "stopped", "message": "收到停止请求，状态已保存"})
                append_log(project_name, "INFO", "收到停止请求，任务已暂停")
                self.update_state(state=states.REVOKED, meta="stopped")
                return {"status": "stopped"}

            for node_name, _ in state.items():
                step_index += 1
                _publish_progress(project_name, node_name, step_index)
                if stop_at and node_name == stop_at:
                    save_progress(project_name, {"status": "completed", "message": f"已在 {stop_at} 停止", "progress_percent": 100})
                    append_log(project_name, "INFO", f"stop_at={stop_at} 达成，任务暂停")
                    return {"status": "stopped"}

        save_progress(project_name, {"status": "completed", "progress_percent": 100, "message": "生成完成"})
        append_log(project_name, "INFO", "生成完成")
        return {"status": "completed"}

    except KeyboardInterrupt:
        # 用户按 Ctrl+C 或收到 SIGINT
        _handle_interruption(
            project_name, orchestrator,
            "用户中断 (Ctrl+C)", "KeyboardInterrupt"
        )
        request_shutdown()
        self.update_state(state=states.REVOKED, meta="interrupted")
        return {"status": "stopped", "reason": "user_interrupt"}

    except SystemExit as e:
        # 系统退出信号
        _handle_interruption(
            project_name, orchestrator,
            f"系统退出 (code={e.code})", "SystemExit"
        )
        request_shutdown()
        self.update_state(state=states.REVOKED, meta="system_exit")
        return {"status": "stopped", "reason": "system_exit"}

    except SoftTimeLimitExceeded:
        # Celery 软超时
        _handle_interruption(
            project_name, orchestrator,
            "任务执行超时", "SoftTimeLimitExceeded"
        )
        self.update_state(state=states.REVOKED, meta="timeout")
        return {"status": "stopped", "reason": "timeout"}

    except WorkerLostError:
        # Worker 丢失（进程被杀）
        _handle_interruption(
            project_name, orchestrator,
            "Worker 进程丢失", "WorkerLostError"
        )
        return {"status": "stopped", "reason": "worker_lost"}

    except Exception as exc:
        logger.exception("生成任务失败")
        save_progress(project_name, {"status": "failed", "message": str(exc)})
        append_log(project_name, "ERROR", f"生成失败: {exc}")
        raise

    finally:
        clear_active_task(project_name)
        _safe_cleanup(orchestrator, project_name)


@celery_app.task(name=TASK_RESUME, bind=True)
def resume_novel(self, project_name: str):
    """
    从检查点恢复生成

    支持优雅停机:
    - 响应 KeyboardInterrupt/SystemExit
    - 中断时保存进度并清理资源
    """
    reset_shutdown()
    append_log(project_name, "INFO", f"恢复项目 {project_name}")
    save_progress(project_name, {"status": "running", "progress_percent": 1.0, "message": "恢复任务启动"})
    orchestrator: Optional[NovelOrchestrator] = None

    try:
        orchestrator = NovelOrchestrator(project_name, verbose=False, show_prompt=False)
        orchestrator.resume_workflow()
        save_progress(project_name, {"status": "completed", "progress_percent": 100, "message": "恢复完成"})
        append_log(project_name, "INFO", "恢复完成")
        return {"status": "completed"}

    except KeyboardInterrupt:
        # 用户按 Ctrl+C 或收到 SIGINT
        _handle_interruption(
            project_name, orchestrator,
            "用户中断 (Ctrl+C)", "KeyboardInterrupt"
        )
        request_shutdown()
        self.update_state(state=states.REVOKED, meta="interrupted")
        return {"status": "stopped", "reason": "user_interrupt"}

    except SystemExit as e:
        # 系统退出信号
        _handle_interruption(
            project_name, orchestrator,
            f"系统退出 (code={e.code})", "SystemExit"
        )
        request_shutdown()
        self.update_state(state=states.REVOKED, meta="system_exit")
        return {"status": "stopped", "reason": "system_exit"}

    except SoftTimeLimitExceeded:
        # Celery 软超时
        _handle_interruption(
            project_name, orchestrator,
            "任务执行超时", "SoftTimeLimitExceeded"
        )
        self.update_state(state=states.REVOKED, meta="timeout")
        return {"status": "stopped", "reason": "timeout"}

    except WorkerLostError:
        # Worker 丢失（进程被杀）
        _handle_interruption(
            project_name, orchestrator,
            "Worker 进程丢失", "WorkerLostError"
        )
        return {"status": "stopped", "reason": "worker_lost"}

    except Exception as exc:
        logger.exception("恢复任务失败")
        save_progress(project_name, {"status": "failed", "message": str(exc)})
        append_log(project_name, "ERROR", f"恢复失败: {exc}")
        raise

    finally:
        clear_active_task(project_name)
        _safe_cleanup(orchestrator, project_name)


