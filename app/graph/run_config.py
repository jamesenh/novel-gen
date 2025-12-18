"""LangGraph RunnableConfig 构造工具。

LangGraph 在启用 checkpointer 时，`invoke/stream` 必须提供至少一个
`configurable` key（通常是 `thread_id`）。本项目约定：
- 一个 project 对应一个 thread（thread_id = project_name）
- checkpoint_ns 目前固定为空字符串（默认）
"""

from __future__ import annotations

from typing import Any, Dict


def build_thread_config(project_name: str) -> Dict[str, Any]:
    """为某个项目构建 LangGraph 的 thread 配置。"""
    return {"configurable": {"thread_id": project_name}}
