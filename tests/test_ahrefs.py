"""Tests for the Ahrefs tool — HTTP layer mocked with ``responses``."""

from __future__ import annotations

import json

import pytest
import responses

from marketing_mcp.tools.ahrefs import (
    AHREFS_BASE,
    _unwrap_rows,
    get_ahrefs_tools,
    handle_ahrefs_tool,
)
from marketing_mcp.utils.cache import AHREFS_CACHE
from marketing_mcp.utils.config import AhrefsConfig, Config


@pytest.fixture(autouse=True)
def _clear_ahrefs_cache():
    AHREFS_CACHE.clear()
    yield
    AHREFS_CACHE.clear()


@pytest.fixture
def cfg_with_key() -> Config:
    return Config(ahrefs=AhrefsConfig(api_key="test-key"))


def test_get_ahrefs_tools_exposes_six_tools():
    tools = get_ahrefs_tools()
    names = {t["name"] for t in tools}
    assert names == {
        "ahrefs_get_domain_rating",
        "ahrefs_get_backlinks",
        "ahrefs_get_organic_keywords",
        "ahrefs_get_linking_domains",
        "ahrefs_compare_domains",
        "ahrefs_get_anchor_text",
    }


def test_handler_without_api_key_returns_friendly_message():
    import asyncio

    cfg = Config()  # no api key
    result = asyncio.run(handle_ahrefs_tool("ahrefs_get_domain_rating", {"domain": "x.com"}, cfg))
    assert "Ahrefs API key not found" in result["content"][0]["text"]


@responses.activate
def test_domain_rating_text_output(cfg_with_key: Config):
    import asyncio

    responses.add(
        responses.GET,
        f"{AHREFS_BASE}/site-explorer/domain-rating",
        json={"domain_rating": {"target": "example.com", "domain_rating": 42.5}},
        status=200,
    )
    result = asyncio.run(
        handle_ahrefs_tool("ahrefs_get_domain_rating", {"domain": "example.com"}, cfg_with_key)
    )
    text = result["content"][0]["text"]
    assert "example.com" in text
    assert "42.5" in text


@responses.activate
def test_domain_rating_json_output(cfg_with_key: Config):
    import asyncio

    responses.add(
        responses.GET,
        f"{AHREFS_BASE}/site-explorer/domain-rating",
        json={"domain_rating": {"target": "example.com", "domain_rating": 42.5}},
        status=200,
    )
    result = asyncio.run(
        handle_ahrefs_tool(
            "ahrefs_get_domain_rating",
            {"domain": "example.com", "format": "json"},
            cfg_with_key,
        )
    )
    text = result["content"][0]["text"]
    parsed = json.loads(text)
    assert parsed["domain_rating"]["domain_rating"] == 42.5


@responses.activate
def test_response_caching_avoids_second_call(cfg_with_key: Config):
    import asyncio

    responses.add(
        responses.GET,
        f"{AHREFS_BASE}/site-explorer/domain-rating",
        json={"domain_rating": {"target": "example.com", "domain_rating": 50}},
        status=200,
    )
    asyncio.run(handle_ahrefs_tool("ahrefs_get_domain_rating", {"domain": "example.com"}, cfg_with_key))
    asyncio.run(handle_ahrefs_tool("ahrefs_get_domain_rating", {"domain": "example.com"}, cfg_with_key))
    assert len(responses.calls) == 1  # second call hits cache


@responses.activate
def test_http_error_surfaces_as_text(cfg_with_key: Config):
    import asyncio

    responses.add(
        responses.GET,
        f"{AHREFS_BASE}/site-explorer/domain-rating",
        json={"error": "unauthorized"},
        status=401,
    )
    result = asyncio.run(
        handle_ahrefs_tool("ahrefs_get_domain_rating", {"domain": "example.com"}, cfg_with_key)
    )
    assert "Ahrefs API error" in result["content"][0]["text"]
    assert "401" in result["content"][0]["text"]


def test_unwrap_rows_finds_data_under_hint():
    result = {"keywords": [{"keyword": "a"}, {"keyword": "b"}]}
    assert len(_unwrap_rows(result, "keywords")) == 2


def test_unwrap_rows_falls_back_to_data():
    result = {"data": [{"keyword": "a"}]}
    assert len(_unwrap_rows(result, "keywords")) == 1


def test_unwrap_rows_handles_nested():
    result = {"data": {"keywords": [{"keyword": "a"}]}}
    assert len(_unwrap_rows(result, "keywords")) == 1


def test_unwrap_rows_empty_default():
    assert _unwrap_rows({}, "keywords") == []
