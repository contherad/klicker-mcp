"""Coordinator — routes MCP tool calls to the correct integration handler."""

from marketing_mcp.utils.config import load_config

_config = None

def get_config():
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_tools_metadata():
    from marketing_mcp.tools import get_all_tools
    return get_all_tools()


async def run_tool(tool_name, arguments):
    from marketing_mcp.tools import get_all_handlers
    config = get_config()
    handlers = get_all_handlers()
    handler = handlers.get(tool_name)
    if not handler:
        return {"content": [{"type": "text", f"Unknown tool: {tool_name}"}]}
    return await handler(tool_name, arguments, config)