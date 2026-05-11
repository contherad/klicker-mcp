"""Ahrefs tools using the Ahrefs API v3."""

import requests


def get_ahrefs_tools():
    return [
        {
            "name": "ahrefs_get_domain_rating",
            "description": "Get Domain Rating (DR), backlinks count, and referring domains for any domain.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain (e.g. klickerinc.com)"},
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_get_backlinks",
            "description": "Get top backlinks for a domain: source URL, anchor text, dofollow/nofollow, DR of source.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_get_organic_keywords",
            "description": "Get top organic keywords a domain ranks for with search volume, KD, position, and landing page URL.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max keywords (default 50)"},
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_get_linking_domains",
            "description": "Get domains that link to the target with DR and number of links per domain.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max domains (default 50)"},
                },
                "required": ["domain"],
            },
        },
        {
            "name": "ahrefs_compare_domains",
            "description": "Compare two domains side-by-side: DR, backlinks, referring domains, top keywords.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain_a": {"type": "string", "description": "First domain"},
                    "domain_b": {"type": "string", "description": "Second domain"},
                },
                "required": ["domain_a", "domain_b"],
            },
        },
        {
            "name": "ahrefs_get_anchor_text",
            "description": "Get the most common anchor texts used in backlinks pointing to the domain.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Target domain"},
                    "limit": {"type": "integer", "description": "Max results (default 50)"},
                },
                "required": ["domain"],
            },
        },
    ]


AHREFS_BASE = "https://api.ahrefs.com/v3"


def _req(endpoint, params, api_key):
    params["access_token"] = api_key
    try:
        resp = requests.get(f"{AHREFS_BASE}/{endpoint}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": str(e)}


async def handle_ahrefs_tool(tool_name, arguments, config):
    api_key = config.ahrefs.api_key
    if not api_key:
        return {"content": [{"type": "text", (
            "Ahrefs API key not found.\n"
            "Save your API key to: credentials/ahrefs-api-key.txt\n"
            "See docs/AHREFS-SETUP.md for step-by-step instructions."
        )}]}

    domain = arguments.get("domain", "")
    limit = arguments.get("limit", 50)

    if tool_name == "ahrefs_get_domain_rating":
        result = _req("domain-resolver", {"domain": domain}, api_key)
        return _format(result, tool_name)

    elif tool_name == "ahrefs_get_backlinks":
        result = _req("backlinks/all", {"domain": domain, "limit": limit}, api_key)
        return _format(result, tool_name)

    elif tool_name == "ahrefs_get_organic_keywords":
        result = _req("keywords/ranking", {"domain": domain, "limit": limit}, api_key)
        return _format(result, tool_name)

    elif tool_name == "ahrefs_get_linking_domains":
        result = _req("domains/referencing", {"domain": domain, "limit": limit}, api_key)
        return _format(result, tool_name)

    elif tool_name == "ahrefs_compare_domains":
        domain_a = arguments.get("domain_a", "")
        domain_b = arguments.get("domain_b", "")
        r_a = _req("domain-resolver", {"domain": domain_a}, api_key)
        r_b = _req("domain-resolver", {"domain": domain_b}, api_key)
        result = {"domain_a": r_a, "domain_b": r_b}
        return _format(result, tool_name)

    elif tool_name == "ahrefs_get_anchor_text":
        result = _req("backlinks/anchors", {"domain": domain, "limit": limit}, api_key)
        return _format(result, tool_name)

    return {"content": [{"type": "text", f"Unknown tool: {tool_name}"}]}


def _format(result, tool_name):
    if "error" in result:
        return {"content": [{"type": "text", f"Ahrefs API error: {result['error']}"}]}

    lines = []

    if tool_name == "ahrefs_get_domain_rating":
        lines = ["=== Domain Rating ==="]
        lines.append(f"Domain: {result.get('domain', 'N/A')}")
        lines.append(f"DR: {result.get('domain_rating', 'N/A')}")
        bl = result.get("backlinks", result.get("backlinks_count", "N/A"))
        rd = result.get("referring_domains", result.get("refdomains", "N/A"))
        lines.append(f"Backlinks: {bl:,}" if isinstance(bl, int) else f"Backlinks: {bl}")
        lines.append(f"Referring Domains: {rd:,}" if isinstance(rd, int) else f"Referring Domains: {rd}")

    elif tool_name == "ahrefs_get_backlinks":
        rows = result.get("backlinks", result.get("results", []))
        lines = ["=== Backlinks ==="]
        if not rows:
            lines.append("No backlinks found.")
        else:
            lines.append(f"{'Source URL':<55} {'Target URL':<35} {'DR':<4} {'DF'}")
            lines.append("-" * 105)
            for b in rows[:50]:
                src = _get_nested(b, "source", "url", "")
                tgt = _get_nested(b, "target", "url", "")
                dr = b.get("domain_rating", b.get("DR", "?"))
                df = "yes" if b.get("do_follow", b.get("dofollow", False)) else "no"
                lines.append(f"{str(src)[:53]:<55} {str(tgt)[:33]:<35} {str(dr):<4} {df}")

    elif tool_name == "ahrefs_get_organic_keywords":
        rows = result.get("keywords", result.get("results", []))
        lines = ["=== Organic Keywords ==="]
        if not rows:
            lines.append("No keywords found.")
        else:
            lines.append(f"{'Keyword':<40} {'Vol':<8} {'KD':<5} {'Pos':<5} {'URL':<28}")
            lines.append("-" * 95)
            for kw in rows[:50]:
                lines.append(
                    f"{str(kw.get('keyword', ''))[:38]:<40}"
                    f"{str(kw.get('search_volume', kw.get('vol', ''))):<8}"
                    f"{str(kw.get('keyword_difficulty', kw.get('kd', ''))):<5}"
                    f"{str(kw.get('position', kw.get('pos', ''))):<5}"
                    f"{str(kw.get('url', ''))[:26]:<28}"
                )

    elif tool_name == "ahrefs_get_linking_domains":
        rows = result.get("domains", result.get("results", []))
        lines = ["=== Linking Domains ==="]
        if not rows:
            lines.append("No linking domains found.")
        else:
            lines.append(f"{'Domain':<40} {'DR':<6} {'Links'}")
            lines.append("-" * 58)
            for d in rows[:50]:
                lines.append(
                    f"{str(d.get('domain', ''))[:38]:<40}"
                    f"{str(d.get('domain_rating', d.get('DR', '?'))):<6}"
                    f"{d.get('backlinks', d.get('links', '?'))}"
                )

    elif tool_name == "ahrefs_compare_domains":
        lines = ["=== Domain Comparison ==="]
        a = result.get("domain_a", {})
        b = result.get("domain_b", {})
        for label, data in [("Domain A", a), ("Domain B", b)]:
            lines.append(f"\n--- {label} ---")
            lines.append(f"  DR:                {data.get('domain_rating', 'N/A')}")
            lines.append(f"  Backlinks:         {data.get('backlinks', 'N/A')}")
            lines.append(f"  Referring Domains: {data.get('referring_domains', 'N/A')}")
            lines.append(f"  Est. Traffic:       {data.get('estimated_traffic', 'N/A')}")

    elif tool_name == "ahrefs_get_anchor_text":
        rows = result.get("anchors", result.get("results", []))
        lines = ["=== Anchor Text Distribution ==="]
        if not rows:
            lines.append("No anchor data found.")
        else:
            lines.append(f"{'Anchor Text':<40} {'Count'}")
            lines.append("-" * 50)
            for a in rows[:50]:
                lines.append(f"{str(a.get('anchor', ''))[:38]:<40} {a.get('count', a.get(' occurrences', '?'))}")

    if not lines:
        lines = [f"Response: {str(result)[:500]}"]

    return {"content": [{"type": "text", "\n".join(lines)}]}


def _get_nested(obj, *keys, default=""):
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k, default)
        else:
            return default
    return obj if obj else default