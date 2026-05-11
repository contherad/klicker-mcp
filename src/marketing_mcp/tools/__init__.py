"""Tool registry aggregator.

Each integration module exposes ``get_*_tools()`` (definitions) and
``handle_*_tool()`` (dispatcher). This module aggregates them so the MCP
server can ``list_tools`` and ``call_tool`` in one shot.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .ads import get_ads_tools, handle_ads_tool
from .ahrefs import get_ahrefs_tools, handle_ahrefs_tool
from .analytics import get_analytics_tools, handle_analytics_tool
from .tagmanager import get_tagmanager_tools, handle_tagmanager_tool


def get_all_tools() -> list[dict[str, Any]]:
    return (
        get_analytics_tools()
        + get_ads_tools()
        + get_tagmanager_tools()
        + get_ahrefs_tools()
    )


# Map tool prefix -> handler. Avoids the giant explicit name -> handler table.
_HANDLERS_BY_PREFIX: dict[str, Callable[..., Any]] = {
    "ga_": handle_analytics_tool,
    "ads_": handle_ads_tool,
    "gtm_": handle_tagmanager_tool,
    "ahrefs_": handle_ahrefs_tool,
}


class _PrefixHandlerMap:
    """Dict-like view that resolves tool name -> handler by prefix."""

    def __init__(self) -> None:
        self._cached_names: set[str] | None = None

    def _populate(self) -> set[str]:
        if self._cached_names is None:
            self._cached_names = {t["name"] for t in get_all_tools()}
        return self._cached_names

    def get(self, name: str) -> Callable[..., Any] | None:
        if name not in self._populate():
            return None
        for prefix, handler in _HANDLERS_BY_PREFIX.items():
            if name.startswith(prefix):
                return handler
        return None


def get_all_handlers() -> _PrefixHandlerMap:
    return _PrefixHandlerMap()
