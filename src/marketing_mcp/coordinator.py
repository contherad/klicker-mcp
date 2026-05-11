"""Coordinator — routes MCP tool calls to the correct integration handler."""

from __future__ import annotations

from typing import Any

from marketing_mcp.utils.config import Config, get_cached_config
from marketing_mcp.utils.logging import get_logger

logger = get_logger("coordinator")


def get_config() -> Config:
    """Return the hot-reloading singleton config."""
    return get_cached_config()


def get_tools_metadata() -> list[dict[str, Any]]:
    from marketing_mcp.tools import get_all_tools

    return get_all_tools()


async def run_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from marketing_mcp.tools import get_all_handlers

    config = get_config()
    handlers = get_all_handlers()
    handler = handlers.get(tool_name)
    if not handler:
        logger.warning("Unknown tool requested: %s", tool_name)
        return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}

    logger.info("Dispatching %s", tool_name)
    return await handler(tool_name, arguments, config)
