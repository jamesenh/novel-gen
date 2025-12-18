"""空操作插件 - 始终返回空问题列表。

用于在没有实际审计逻辑的情况下测试工作流。
"""

from typing import Any, Dict, List

from app.agents.base import AuditPlugin
from app.graph.state import State


class NoopPlugin(AuditPlugin):
    """始终通过的空操作插件。

    返回空问题列表，允许工作流在没有实际一致性检查的情况下继续。
    """

    name = "noop"
    description = "No-op plugin that always passes"

    def analyze(
        self,
        state: State,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """返回空问题列表。

        Args:
            state: 当前工作流状态（未使用）。
            context: 附加上下文（未使用）。

        Returns:
            空列表。
        """
        return []
