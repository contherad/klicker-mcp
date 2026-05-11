"""Ahrefs tools — Ahrefs API v3 with Bearer auth.

Endpoints live under ``/v3/site-explorer/``. Responses are cached for 1 hr
(see ``AHREFS_CACHE``) because Ahrefs charges per credit.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any

import requests

from marketing_mcp.utils.cache import AHREFS_CACHE, make_key
from marketing_mcp.utils.config import Config
from marketing_mcp.utils.logging import get_logger
from marketing_mcp.utils.retry import with_retry

logger = get_logger("tools.ahrefs")

AHREFS_BASE = "https://api.ahrefs.com/v3"


# ---------- tool definitions ----------


def _format_option() -> dict[str, Any]:
    return {
        "format": {
            "type": "string",
            "enum": ["text", "json"],
            "description": "Output format. Defaults to text.",
        }
    }


def get_ahrefs_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "ahrefs_get_domain_rating",
            "description": "Get Domain Rating (DR), backlinks count, and referring domains for any domain.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain (e.g. example.com)"},
                    **_format_option(),
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_get_backlinks",
            "description": "Top backlinks for a domain: source URL, anchor, dofollow status, source DR.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                    **_format_option(),
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_get_organic_keywords",
            "description": "Top organic keywords with volume, KD, position, landing page URL.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max keywords (default 50)"},
                    "country": {"type": "string", "description": "Country code (default: us)"},
                    **_format_option(),
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_get_linking_domains",
            "description": "Domains linking to the target with DR and link counts.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max domains (default 50)"},
                    **_format_option(),
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_compare_domains",
            "description": "Compare two domains side-by-side: DR, backlinks, referring domains.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain_a": {"type": "string", "description": "First domain"},
                    "domain_b": {"type": "string", "description": "Second domain"},
                    **_format_option(),
                },
                "required": ["domain_a", "domain_b"],
            },
        },
        {
            "name": "ahrefs_get_anchor_text",
            "description": "Most common anchor texts in backlinks pointing to the domain.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                    **_format_option(),
                },
                "required": ["domain"],
            },
        },
    ]


# ---------- HTTP layer ----------


@with_retry(attempts=3, wait_initial=1.0, wait_max=8.0)
def _http_get(endpoint: str, params: dict[str, Any], api_key: str) -> dict[str, Any]:
    """GET an Ahrefs endpoint with Bearer auth. Retried on transient failures."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    resp = requests.get(
        f"{AHREFS_BASE}/{endpoint}",
        params=params,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _cached_get(endpoint: str, params: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Cache-wrapped GET — keyed on endpoint+params (not api_key)."""
    key = make_key(endpoint, params)
    cached = AHREFS_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        result = _http_get(endpoint, params, api_key)
    except requests.HTTPError as e:
        resp = e.response
        status = resp.status_code if resp is not None else "?"
        body = ""
        if resp is not None:
            with contextlib.suppress(Exception):
                body = resp.text[:500]
        return {"error": f"HTTP {status}: {body or e}"}
    except requests.RequestException as e:
        return {"error": str(e)}
    AHREFS_CACHE.set(key, result)
    return result


# ---------- handler ----------


async def handle_ahrefs_tool(
    tool_name: str, arguments: dict[str, Any], config: Config
) -> dict[str, Any]:
    api_key = config.ahrefs.api_key
    if not api_key:
        return _text(
            "Ahrefs API key not found.\n"
            "Save your API key to: credentials/ahrefs-api-key.txt\n"
            "See docs/AHREFS-SETUP.md for setup steps."
        )

    output_format = (arguments.get("format") or "text").lower()
    if output_format not in ("text", "json"):
        return _text(f"Invalid format: {output_format} (expected 'text' or 'json')")

    domain = arguments.get("domain", "").strip()
    limit = int(arguments.get("limit", 50))

    if tool_name == "ahrefs_get_domain_rating":
        result = _cached_get(
            "site-explorer/domain-rating",
            {"target": domain, "date": "today"},
            api_key,
        )
    elif tool_name == "ahrefs_get_backlinks":
        result = _cached_get(
            "site-explorer/all-backlinks",
            {
                "target": domain,
                "limit": limit,
                "mode": "domain",
                "select": "url_from,url_to,anchor,domain_rating_source,is_dofollow",
            },
            api_key,
        )
    elif tool_name == "ahrefs_get_organic_keywords":
        country = arguments.get("country", "us").lower()
        result = _cached_get(
            "site-explorer/organic-keywords",
            {
                "target": domain,
                "country": country,
                "limit": limit,
                "select": "keyword,volume,difficulty,position,url",
            },
            api_key,
        )
    elif tool_name == "ahrefs_get_linking_domains":
        result = _cached_get(
            "site-explorer/refdomains",
            {
                "target": domain,
                "limit": limit,
                "mode": "domain",
                "select": "domain,domain_rating,backlinks",
            },
            api_key,
        )
    elif tool_name == "ahrefs_compare_domains":
        domain_a = arguments.get("domain_a", "").strip()
        domain_b = arguments.get("domain_b", "").strip()
        result = {
            "domain_a": _cached_get(
                "site-explorer/domain-rating", {"target": domain_a, "date": "today"}, api_key
            ),
            "domain_b": _cached_get(
                "site-explorer/domain-rating", {"target": domain_b, "date": "today"}, api_key
            ),
        }
    elif tool_name == "ahrefs_get_anchor_text":
        result = _cached_get(
            "site-explorer/anchors",
            {
                "target": domain,
                "limit": limit,
                "select": "anchor,refdomains,backlinks",
            },
            api_key,
        )
    else:
        return _text(f"Unknown tool: {tool_name}")

    if "error" in result:
        return _text(f"Ahrefs API error: {result['error']}")

    if output_format == "json":
        return _text(json.dumps(result, indent=2, default=str))

    return _format_text(result, tool_name)


# ---------- formatters ----------


def _format_text(result: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Format an Ahrefs v3 response as a text table."""
    if tool_name == "ahrefs_get_domain_rating":
        return _format_domain_rating(result)
    if tool_name == "ahrefs_get_backlinks":
        return _format_backlinks(_unwrap_rows(result, "backlinks"))
    if tool_name == "ahrefs_get_organic_keywords":
        return _format_keywords(_unwrap_rows(result, "keywords"))
    if tool_name == "ahrefs_get_linking_domains":
        return _format_refdomains(_unwrap_rows(result, "refdomains"))
    if tool_name == "ahrefs_compare_domains":
        return _format_compare(result.get("domain_a", {}), result.get("domain_b", {}))
    if tool_name == "ahrefs_get_anchor_text":
        return _format_anchors(_unwrap_rows(result, "anchors"))
    return _text(f"Unknown tool: {tool_name}")


def _unwrap_rows(result: dict[str, Any], key_hint: str) -> list[dict[str, Any]]:
    """Ahrefs v3 wraps result rows under varying keys (``data``, ``backlinks``,
    ``keywords``, etc.). Try the hint first, then common fallbacks."""
    for k in (key_hint, "data", "results", "items"):
        v = result.get(k)
        if isinstance(v, list):
            return v
    # Some endpoints return {"data": {<key_hint>: [...]}}
    data = result.get("data") or {}
    if isinstance(data, dict):
        v = data.get(key_hint) or data.get("rows")
        if isinstance(v, list):
            return v
    return []


def _format_domain_rating(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("domain_rating") or result.get("data") or result
    dr = payload.get("domain_rating") if isinstance(payload, dict) else None
    if dr is None and isinstance(payload, dict):
        # Sometimes returned under "domain_rating_value" or nested differently
        dr = payload.get("value")
    target = payload.get("target", "?") if isinstance(payload, dict) else "?"
    lines = [
        "=== Domain Rating ===",
        f"Target: {target}",
        f"DR: {dr if dr is not None else 'N/A'}",
    ]
    return _text("\n".join(lines))


def _format_backlinks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lines = ["=== Backlinks ==="]
    if not rows:
        lines.append("No backlinks found.")
    else:
        header = f"{'Source URL':<55} {'Target URL':<35} {'DR':<4} {'DF'}"
        lines.append(header)
        lines.append("-" * len(header))
        for b in rows:
            src = b.get("url_from", b.get("source", {}).get("url", "")) if isinstance(b.get("source"), dict) else b.get("url_from", "")
            tgt = b.get("url_to", b.get("target", {}).get("url", "")) if isinstance(b.get("target"), dict) else b.get("url_to", "")
            dr = b.get("domain_rating_source", b.get("domain_rating", b.get("DR", "?")))
            df = "yes" if b.get("is_dofollow", b.get("do_follow", b.get("dofollow", False))) else "no"
            lines.append(f"{str(src)[:53]:<55} {str(tgt)[:33]:<35} {dr!s:<4} {df}")
    return _text("\n".join(lines))


def _format_keywords(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lines = ["=== Organic Keywords ==="]
    if not rows:
        lines.append("No keywords found.")
    else:
        header = f"{'Keyword':<40} {'Vol':<8} {'KD':<5} {'Pos':<5} {'URL':<28}"
        lines.append(header)
        lines.append("-" * len(header))
        for kw in rows:
            lines.append(
                f"{str(kw.get('keyword', ''))[:38]:<40}"
                f"{kw.get('volume', kw.get('search_volume', kw.get('vol', '')))!s:<8}"
                f"{kw.get('difficulty', kw.get('keyword_difficulty', kw.get('kd', '')))!s:<5}"
                f"{kw.get('position', kw.get('pos', ''))!s:<5}"
                f"{str(kw.get('url', ''))[:26]:<28}"
            )
    return _text("\n".join(lines))


def _format_refdomains(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lines = ["=== Linking Domains ==="]
    if not rows:
        lines.append("No linking domains found.")
    else:
        header = f"{'Domain':<40} {'DR':<6} {'Links'}"
        lines.append(header)
        lines.append("-" * len(header))
        for d in rows:
            lines.append(
                f"{str(d.get('domain', ''))[:38]:<40}"
                f"{d.get('domain_rating', d.get('DR', '?'))!s:<6}"
                f"{d.get('backlinks', d.get('links', '?'))}"
            )
    return _text("\n".join(lines))


def _format_compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    lines = ["=== Domain Comparison ==="]
    for label, data in [("Domain A", a), ("Domain B", b)]:
        payload = data.get("domain_rating") if isinstance(data.get("domain_rating"), dict) else data
        lines.append(f"\n--- {label} ---")
        lines.append(f"  Target: {payload.get('target', 'N/A')}")
        lines.append(f"  DR: {payload.get('domain_rating', payload.get('value', 'N/A'))}")
        if "backlinks" in payload:
            lines.append(f"  Backlinks: {payload['backlinks']}")
        if "referring_domains" in payload:
            lines.append(f"  Referring Domains: {payload['referring_domains']}")
    return _text("\n".join(lines))


def _format_anchors(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lines = ["=== Anchor Text Distribution ==="]
    if not rows:
        lines.append("No anchor data found.")
    else:
        header = f"{'Anchor Text':<40} {'Count'}"
        lines.append(header)
        lines.append("-" * len(header))
        for a in rows:
            count = a.get("backlinks", a.get("count", a.get("occurrences", "?")))
            lines.append(f"{str(a.get('anchor', ''))[:38]:<40} {count}")
    return _text("\n".join(lines))


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}
