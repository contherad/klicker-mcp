"""Google Ads tools using google-ads-python."""

from __future__ import annotations

import json
import re
from typing import Any

from marketing_mcp.utils.cache import ADS_QUERY_CACHE, make_key
from marketing_mcp.utils.config import Config
from marketing_mcp.utils.logging import get_logger

logger = get_logger("tools.ads")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------- tool definitions ----------


def _format_option() -> dict[str, Any]:
    return {
        "format": {
            "type": "string",
            "enum": ["text", "json"],
            "description": "Output format. Defaults to text.",
        }
    }


def get_ads_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "ads_get_campaigns",
            "description": "List Google Ads campaigns with status, budget, and spend.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Google Ads customer ID (no dashes)"},
                    "limit": {"type": "integer", "description": "Max campaigns (default 50)"},
                    **_format_option(),
                },
                "required": ["customer_id"],
            },
        },
        {
            "name": "ads_get_campaign_performance",
            "description": "Performance for a campaign over a date range: cost, clicks, CTR, CPC, conversions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "campaign_id": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    **_format_option(),
                },
                "required": ["customer_id", "campaign_id", "start_date", "end_date"],
            },
        },
        {
            "name": "ads_get_keywords_performance",
            "description": "Performance per keyword: clicks, cost, conversions, CTR, avg CPC.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "limit": {"type": "integer", "description": "Max keywords (default 100)"},
                    **_format_option(),
                },
                "required": ["customer_id", "start_date", "end_date"],
            },
        },
        {
            "name": "ads_get_ad_groups",
            "description": "List ad groups for a campaign (or all ad groups in the account).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "campaign_id": {"type": "string", "description": "Optional — filter to one campaign"},
                    **_format_option(),
                },
                "required": ["customer_id"],
            },
        },
        {
            "name": "ads_get_account_summary",
            "description": "Account-level spend, clicks, impressions, conversions for a date range.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    **_format_option(),
                },
                "required": ["customer_id", "start_date", "end_date"],
            },
        },
    ]


# ---------- handler ----------


async def handle_ads_tool(tool_name: str, arguments: dict[str, Any], config: Config) -> dict[str, Any]:
    creds = config.google_ads
    if not creds.developer_token:
        return _text(
            "Google Ads credentials not configured.\n"
            "Save your credentials to: credentials/google-ads-credentials.json\n"
            "Run: marketing-mcp init google-ads"
        )

    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        return _text("Install google-ads: pip install 'google-ads>=24.0.0'")

    # Build client (login_customer_id supported for MCC)
    try:
        client_dict = {
            "developer_token": creds.developer_token,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "refresh_token": creds.refresh_token,
            "use_proto_plus": True,
        }
        if creds.login_customer_id:
            client_dict["login_customer_id"] = str(creds.login_customer_id).replace("-", "")
        client = GoogleAdsClient.load_from_dict(client_dict)
    except Exception as e:
        logger.exception("Google Ads client init failed")
        return _text(f"Failed to initialize Google Ads client: {e}")

    # Input validation
    customer_id = str(arguments.get("customer_id", "")).replace("-", "")
    if not customer_id.isdigit():
        return _text("customer_id must be numeric (digits only)")

    campaign_id = arguments.get("campaign_id")
    if campaign_id is not None and not str(campaign_id).isdigit():
        return _text("campaign_id must be numeric")

    for key in ("start_date", "end_date"):
        val = arguments.get(key)
        if val and not DATE_RE.match(str(val)):
            return _text(f"{key} must be YYYY-MM-DD")

    output_format = (arguments.get("format") or "text").lower()

    try:
        if tool_name == "ads_get_campaigns":
            return _get_campaigns(client, customer_id, int(arguments.get("limit", 50)), output_format)
        if tool_name == "ads_get_campaign_performance":
            return _get_campaign_performance(client, customer_id, arguments, output_format)
        if tool_name == "ads_get_keywords_performance":
            return _get_keywords_performance(client, customer_id, arguments, output_format)
        if tool_name == "ads_get_ad_groups":
            return _get_ad_groups(client, customer_id, arguments.get("campaign_id"), output_format)
        if tool_name == "ads_get_account_summary":
            return _get_account_summary(client, customer_id, arguments, output_format)
    except Exception as e:
        logger.exception("Ads tool %s failed", tool_name)
        return _text(f"Ads API error: {e}")

    return _text(f"Unknown tool: {tool_name}")


# ---------- individual tools ----------


def _get_campaigns(client: Any, customer_id: str, limit: int, output_format: str) -> dict[str, Any]:
    query = f"""
        SELECT campaign.id, campaign.name, campaign.status, campaign_budget.amount_micros,
               metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.ctr, metrics.average_cpc
        FROM campaign
        ORDER BY metrics.cost_micros DESC
        LIMIT {limit}
    """
    rows = _cached_query(client, customer_id, query)
    if output_format == "json":
        out = [
            {
                "campaign_id": row.campaign.id,
                "name": row.campaign.name,
                "status": _enum_name(row.campaign.status),
                "budget": _micros_dollars(getattr(row.campaign_budget, "amount_micros", None)),
                "spend": _micros_dollars(row.metrics.cost_micros),
                "clicks": row.metrics.clicks,
                "impressions": row.metrics.impressions,
                "ctr": row.metrics.ctr,
                "avg_cpc": _micros_dollars(row.metrics.average_cpc),
            }
            for row in rows
        ]
        return _text(json.dumps(out, indent=2, default=str))

    lines = ["=== Google Ads Campaigns ==="]
    if not rows:
        lines.append("No campaigns found.")
    else:
        header = f"{'Campaign Name':<40} {'Status':<10} {'Spend':<12} {'Clicks':<8} {'Impr':<10} {'CTR':<8} {'Avg CPC':<10}"
        lines.append(header)
        lines.append("-" * len(header))
        for row in rows:
            name = str(row.campaign.name)[:38]
            status = _enum_name(row.campaign.status)
            cost = _micros_dollars(row.metrics.cost_micros)
            clicks = row.metrics.clicks
            impr = row.metrics.impressions
            ctr = f"{row.metrics.ctr:.2%}"
            cpc = f"${_micros_dollars(row.metrics.average_cpc)}"
            lines.append(f"{name:<40} {status:<10} ${cost:<11} {clicks:<8} {impr:<10} {ctr:<8} {cpc:<10}")
    return _text("\n".join(lines))


def _get_campaign_performance(
    client: Any, customer_id: str, args: dict[str, Any], output_format: str
) -> dict[str, Any]:
    campaign_id = args["campaign_id"]
    start = args["start_date"]
    end = args["end_date"]
    query = f"""
        SELECT campaign.name, campaign.status, campaign_budget.amount_micros,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.ctr, metrics.average_cpc, metrics.conversions
        FROM campaign
        WHERE campaign.id = {campaign_id}
          AND segments.date BETWEEN '{start}' AND '{end}'
    """
    rows = _cached_query(client, customer_id, query)
    if not rows:
        return _text(f"No data for campaign {campaign_id} between {start} and {end}.")

    row = rows[0]
    budget = getattr(row.campaign_budget, "amount_micros", None) if hasattr(row, "campaign_budget") else None
    if output_format == "json":
        return _text(
            json.dumps(
                {
                    "campaign": str(row.campaign.name),
                    "status": _enum_name(row.campaign.status),
                    "budget": _micros_dollars(budget),
                    "spend": _micros_dollars(row.metrics.cost_micros),
                    "clicks": row.metrics.clicks,
                    "impressions": row.metrics.impressions,
                    "ctr": row.metrics.ctr,
                    "avg_cpc": _micros_dollars(row.metrics.average_cpc),
                    "conversions": row.metrics.conversions,
                },
                indent=2,
                default=str,
            )
        )

    lines = [
        f"=== Campaign {campaign_id} Performance: {start} to {end} ===",
        f"Campaign: {row.campaign.name}",
        f"Status: {_enum_name(row.campaign.status)}",
        f"Budget: ${_micros_dollars(budget) if budget else 'N/A'}",
        f"Spend: ${_micros_dollars(row.metrics.cost_micros)}",
        f"Clicks: {row.metrics.clicks}",
        f"Impressions: {row.metrics.impressions}",
        f"CTR: {row.metrics.ctr:.2%}",
        f"Avg CPC: ${_micros_dollars(row.metrics.average_cpc)}",
        f"Conversions: {row.metrics.conversions}",
    ]
    return _text("\n".join(lines))


def _get_keywords_performance(
    client: Any, customer_id: str, args: dict[str, Any], output_format: str
) -> dict[str, Any]:
    start = args["start_date"]
    end = args["end_date"]
    limit = int(args.get("limit", 100))
    query = f"""
        SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
               metrics.clicks, metrics.cost_micros, metrics.impressions,
               metrics.ctr, metrics.conversions
        FROM keyword_view
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        ORDER BY metrics.cost_micros DESC
        LIMIT {limit}
    """
    rows = _cached_query(client, customer_id, query)
    if output_format == "json":
        out = [
            {
                "keyword": str(row.ad_group_criterion.keyword.text),
                "match_type": _enum_name(row.ad_group_criterion.keyword.match_type),
                "clicks": row.metrics.clicks,
                "cost": _micros_dollars(row.metrics.cost_micros),
                "impressions": row.metrics.impressions,
                "ctr": row.metrics.ctr,
                "conversions": row.metrics.conversions,
            }
            for row in rows
        ]
        return _text(json.dumps(out, indent=2, default=str))

    lines = ["=== Keyword Performance ==="]
    if not rows:
        lines.append("No keyword data found.")
    else:
        header = f"{'Keyword':<30} {'Match':<8} {'Clicks':<8} {'Cost':<10} {'Impr':<8} {'CTR':<8} {'Conv':<6}"
        lines.append(header)
        lines.append("-" * len(header))
        for row in rows:
            kw = str(row.ad_group_criterion.keyword.text)[:28]
            mt = _enum_name(row.ad_group_criterion.keyword.match_type)
            lines.append(
                f"{kw:<30} {mt:<8} {row.metrics.clicks:<8} "
                f"${_micros_dollars(row.metrics.cost_micros):<9} {row.metrics.impressions:<8} "
                f"{row.metrics.ctr:.2%}    {row.metrics.conversions:<6}"
            )
    return _text("\n".join(lines))


def _get_ad_groups(
    client: Any, customer_id: str, campaign_id: str | None, output_format: str
) -> dict[str, Any]:
    where = f"WHERE campaign.id = {campaign_id}" if campaign_id else ""
    query = f"""
        SELECT ad_group.id, ad_group.name, ad_group.status,
               metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.ctr
        FROM ad_group
        {where}
        ORDER BY metrics.cost_micros DESC
        LIMIT 200
    """
    rows = _cached_query(client, customer_id, query)
    if output_format == "json":
        out = [
            {
                "ad_group_id": row.ad_group.id,
                "name": row.ad_group.name,
                "status": _enum_name(row.ad_group.status),
                "spend": _micros_dollars(row.metrics.cost_micros),
                "clicks": row.metrics.clicks,
                "impressions": row.metrics.impressions,
                "ctr": row.metrics.ctr,
            }
            for row in rows
        ]
        return _text(json.dumps(out, indent=2, default=str))

    lines = ["=== Ad Groups ==="]
    if not rows:
        lines.append("No ad groups found.")
    else:
        for row in rows:
            lines.append(
                f"[{row.ad_group.id}] {row.ad_group.name} | "
                f"Status: {_enum_name(row.ad_group.status)} | "
                f"Spend: ${_micros_dollars(row.metrics.cost_micros)}"
            )
    return _text("\n".join(lines))


def _get_account_summary(
    client: Any, customer_id: str, args: dict[str, Any], output_format: str
) -> dict[str, Any]:
    start = args["start_date"]
    end = args["end_date"]
    query = f"""
        SELECT campaign.name,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.ctr, metrics.conversions, metrics.average_cpc
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        ORDER BY metrics.cost_micros DESC
    """
    rows = _cached_query(client, customer_id, query)
    total_cost = total_clicks = total_impr = 0
    total_conv = 0.0
    per_campaign = []
    for row in rows:
        c = row.metrics.cost_micros or 0
        total_cost += c
        total_clicks += row.metrics.clicks or 0
        total_impr += row.metrics.impressions or 0
        total_conv += row.metrics.conversions or 0
        per_campaign.append({"name": row.campaign.name, "spend": _micros_dollars(c)})

    if output_format == "json":
        return _text(
            json.dumps(
                {
                    "period": {"start": start, "end": end},
                    "totals": {
                        "spend": _micros_dollars(total_cost),
                        "clicks": total_clicks,
                        "impressions": total_impr,
                        "conversions": total_conv,
                        "ctr": (total_clicks / total_impr) if total_impr > 0 else None,
                        "cost_per_conv": (
                            float(_micros_dollars(total_cost)) / total_conv if total_conv > 0 else None
                        ),
                    },
                    "campaigns": per_campaign,
                },
                indent=2,
                default=str,
            )
        )

    lines = [f"=== Google Ads Account Summary: {start} to {end} ===", ""]
    if not rows:
        lines.append("No data for this period.")
    else:
        for c in per_campaign:
            lines.append(f"  {c['name']}: ${c['spend']}")
        lines.append("")
        lines.append(f"TOTAL SPEND:       ${_micros_dollars(total_cost)}")
        lines.append(f"TOTAL CLICKS:      {total_clicks:,}")
        lines.append(f"TOTAL IMPRESSIONS: {total_impr:,}")
        lines.append(f"TOTAL CONVERSIONS: {total_conv}")
        if total_impr > 0:
            lines.append(f"AVG CTR:           {(total_clicks / total_impr * 100):.2f}%")
        if total_conv > 0:
            lines.append(f"COST PER CONV:     ${float(_micros_dollars(total_cost)) / total_conv:.2f}")
    return _text("\n".join(lines))


# ---------- internals ----------


def _cached_query(client: Any, customer_id: str, query: str) -> list[Any]:
    """Run a GAQL query, with TTL caching of the row list."""
    key = make_key("ads_query", customer_id, query)
    cached = ADS_QUERY_CACHE.get(key)
    if cached is not None:
        return cached  # type: ignore[no-any-return]
    rows = _run_query(client, customer_id, query)
    ADS_QUERY_CACHE.set(key, rows)
    return rows


def _run_query(client: Any, customer_id: str, query: str) -> list[Any]:
    """Execute a GAQL query — search_stream yields batches; flatten to rows."""
    ga_service = client.get_service("GoogleAdsService")
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    rows: list[Any] = []
    for batch in stream:
        for row in batch.results:
            rows.append(row)
    return rows


def _enum_name(value: Any) -> str:
    return str(value).split(".")[-1] if value is not None else ""


def _micros_dollars(micros: int | None) -> str:
    if micros is None:
        return "0.00"
    return f"{micros / 1_000_000:.2f}"


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}
