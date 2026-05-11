"""Tests for the tool registry aggregator."""

from __future__ import annotations

from marketing_mcp.tools import get_all_handlers, get_all_tools
from marketing_mcp.tools.ads import handle_ads_tool
from marketing_mcp.tools.ahrefs import handle_ahrefs_tool
from marketing_mcp.tools.analytics import handle_analytics_tool
from marketing_mcp.tools.tagmanager import handle_tagmanager_tool


def test_get_all_tools_returns_unique_names():
    tools = get_all_tools()
    names = [t["name"] for t in tools]
    assert len(names) == len(set(names))


def test_all_tools_have_required_keys():
    for tool in get_all_tools():
        assert "name" in tool and isinstance(tool["name"], str)
        assert "description" in tool
        assert "inputSchema" in tool


def test_prefix_routing():
    handlers = get_all_handlers()
    assert handlers.get("ga_get_account_summaries") is handle_analytics_tool
    assert handlers.get("ads_get_campaigns") is handle_ads_tool
    assert handlers.get("gtm_list_containers") is handle_tagmanager_tool
    assert handlers.get("ahrefs_get_domain_rating") is handle_ahrefs_tool


def test_unknown_tool_returns_none():
    handlers = get_all_handlers()
    assert handlers.get("unknown_tool") is None
    assert handlers.get("ga_not_a_real_tool") is None
