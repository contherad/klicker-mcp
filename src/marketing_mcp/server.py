"""Marketing MCP Server — connects Google Analytics, Google Ads, GTM, and Ahrefs to Claude Desktop."""

import asyncio
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from marketing_mcp.coordinator import get_tools_metadata, run_tool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MARKETING_SERVER = Server("marketing-mcp")


@MARKETING_SERVER.list_tools()
async def list_tools():
    """Expose all marketing tool definitions to Claude Desktop."""
    metadata = get_tools_metadata()
    logger.info(f"Loading {len(metadata)} tools...")
    return [
        Tool(
            name=m["name"],
            description=m["description"],
            inputSchema=m["inputSchema"],
        )
        for m in metadata
    ]


@MARKETING_SERVER.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle a tool call from Claude Desktop."""
    logger.info(f"--> Tool call: {name} | args: {list(arguments.keys())}")
    try:
        result = await run_tool(name, arguments)
    except Exception as e:
        logger.exception(f"Tool {name} failed")
        result = {"content": [{"type": "text", f"Error: {e}"}]}

    text = result.get("content", [{"type": "text", "no output"}])
    if isinstance(text, list):
        text = text[0].get("text", str(result))
    else:
        text = str(text)

    return [TextContent(type="text", text=text)]


async def main():
    """Start the MCP server. Called by the CLI entry point."""
    logger.info("Starting Marketing MCP Server...")
    logger.info("Integrations: Google Analytics | Google Ads | Google Tag Manager | Ahrefs")

    # Ensure credentials directory exists
    creds = Path(__file__).parent.parent.parent / "credentials"
    creds.mkdir(exist_ok=True)
    (creds / ".gitkeep").touch()

    await (stdio_server(MARKETING_SERVER).run_as_task())


if __name__ == "__main__":
    asyncio.run(main())