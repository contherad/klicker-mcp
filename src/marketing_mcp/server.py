"""Marketing MCP Server — stdio entry point.

This module is invoked as ``python -m marketing_mcp.server`` by Claude Desktop,
or via the ``marketing-mcp`` console script (which calls ``cli.main``).
"""

from __future__ import annotations

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from marketing_mcp.coordinator import get_tools_metadata, run_tool
from marketing_mcp.utils.config import get_cached_config
from marketing_mcp.utils.logging import configure_logging, get_logger

logger = get_logger("server")

MARKETING_SERVER: Server = Server("marketing-mcp")


@MARKETING_SERVER.list_tools()
async def list_tools() -> list[Tool]:
    """Expose all marketing tool definitions to the MCP client."""
    metadata = get_tools_metadata()
    logger.info("Listing %d tools", len(metadata))
    return [
        Tool(name=m["name"], description=m["description"], inputSchema=m["inputSchema"])
        for m in metadata
    ]


@MARKETING_SERVER.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle a tool call from the MCP client."""
    logger.info("Tool call: %s (args=%s)", name, sorted(arguments))
    try:
        result = await run_tool(name, arguments)
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return [TextContent(type="text", text=f"Error in {name}: {e}")]

    content_items = result.get("content") or [{"type": "text", "text": "no output"}]
    if not isinstance(content_items, list):
        content_items = [{"type": "text", "text": str(content_items)}]
    return [TextContent(type="text", text=item.get("text", "")) for item in content_items]


async def run() -> None:
    """Start the MCP server. Public coroutine used by the CLI."""
    configure_logging()
    logger.info("Starting Marketing MCP Server")
    logger.info("Integrations: Google Analytics | Google Ads | Tag Manager | Ahrefs")

    # Eager-load config so any credential errors surface in the log immediately.
    cfg = get_cached_config()
    logger.info("Credentials dir: %s", cfg.credentials_dir)

    async with stdio_server() as (read_stream, write_stream):
        await MARKETING_SERVER.run(
            read_stream,
            write_stream,
            MARKETING_SERVER.create_initialization_options(),
        )


def main() -> None:
    """Sync entry point preserved for ``python -m marketing_mcp.server``."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
