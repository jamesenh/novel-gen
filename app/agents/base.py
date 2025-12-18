"""Agent 插件的基类。

插件是纯分析组件:
- 从 State 和 context 读取数据
- 产出结构化问题
- 禁止直接写入磁盘或数据库
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.graph.state import State


class AuditPlugin(ABC):
    """审计插件基类。

    插件分析章节内容并产出结构化问题。
    必须是只读的：不能直接写入文件系统或数据库。
    """

    name: str = "base_plugin"
    description: str = "Base audit plugin"

    @abstractmethod
    def analyze(
        self,
        state: State,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """分析状态并返回问题列表。

        Args:
            state: 当前工作流状态（包含 chapter_draft）。
            context: 附加上下文（world、characters、outline 等）。

        Returns:
            问题字典列表，包含 severity、category、summary 等字段。
        """
        pass
