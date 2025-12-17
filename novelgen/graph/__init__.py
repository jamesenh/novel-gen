"""
Kùzu 图谱层模块
提供嵌入式图数据库支持，用于人物/关系/事件的结构化检索

作者: jamesenh, 2025-12-17
开发者: Jamesenh
开发时间: 2025-12-15
"""

from novelgen.graph.kuzu_store import KuzuStore
from novelgen.graph.updater import GraphUpdater

__all__ = ["KuzuStore", "GraphUpdater"]
