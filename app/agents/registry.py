"""审计插件注册表。

管理审计插件的注册和检索。
插件可以按名称注册，也可以作为列表检索。
"""

from typing import Dict, List, Optional, Type

from app.agents.base import AuditPlugin
from app.agents.continuity import ContinuityPlugin
from app.agents.noop import NoopPlugin

# Global plugin registry
_PLUGINS: Dict[str, AuditPlugin] = {}

# Default plugins to register
_DEFAULT_PLUGINS: List[Type[AuditPlugin]] = [
    NoopPlugin,
    ContinuityPlugin,
]


def register_plugin(plugin: AuditPlugin) -> None:
    """注册审计插件。

    Args:
        plugin: 要注册的插件实例。
    """
    _PLUGINS[plugin.name] = plugin


def get_plugin(name: str) -> Optional[AuditPlugin]:
    """按名称获取插件。

    Args:
        name: 插件名称。

    Returns:
        插件实例，如果未找到则返回 None。
    """
    return _PLUGINS.get(name)


def get_audit_plugins() -> List[AuditPlugin]:
    """获取所有已注册的审计插件。

    Returns:
        所有已注册插件实例的列表。
    """
    return list(_PLUGINS.values())


def get_active_plugins(names: Optional[List[str]] = None) -> List[AuditPlugin]:
    """按名称获取插件，如果 names 为 None 则返回全部。

    Args:
        names: 可选的插件名称列表。如果为 None，返回所有插件。

    Returns:
        匹配的插件实例列表。
    """
    if names is None:
        return get_audit_plugins()
    return [p for n, p in _PLUGINS.items() if n in names]


def _init_default_plugins() -> None:
    """初始化默认插件。"""
    for plugin_cls in _DEFAULT_PLUGINS:
        register_plugin(plugin_cls())


# Initialize defaults on import
_init_default_plugins()
