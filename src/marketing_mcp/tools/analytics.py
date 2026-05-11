"""Google Analytics 4 tools.

Reports go through ``google-analytics-data`` (gRPC). Admin queries (account
list, property details, custom dimensions) use the Admin REST API directly
since the Python client for it is heavyweight for what we need.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunRealtimeReportRequest,
    RunReportRequest,
)

from marketing_mcp.utils.cache import ANALYTICS_METADATA_CACHE, make_key
from marketing_mcp.utils.config import Config
from marketing_mcp.utils.logging import get_logger
from marketing_mcp.utils.retry import with_retry

logger = get_logger("tools.analytics")

ADMIN_BASE = "https://analyticsadmin.googleapis.com/v1beta"


# ---------- tool definitions ----------


def _format_option() -> dict[str, Any]:
    return {
        "format": {
            "type": "string",
            "enum": ["text", "json"],
            "description": "Output format. Defaults to text.",
        }
    }


def get_analytics_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "ga_get_account_summaries",
            "description": "List all Google Analytics accounts and properties the user has access to.",
            "inputSchema": {"type": "object", "properties": {**_format_option()}},
        },
        {
            "name": "ga_get_property_details",
            "description": "Get details about a specific GA4 property.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "GA4 property ID (numeric)"},
                    **_format_option(),
                },
                "required": ["property_id"],
            },
        },
        {
            "name": "ga_run_report",
            "description": "Run a Google Analytics report: sessions, users, bounce rate, conversions for a date range.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "GA4 property ID (numeric)"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (default: 30 days ago)"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD (default: yesterday)"},
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "e.g. city, deviceCategory, country, pagePath, source, medium, campaign, sessionDefaultChannelGroup",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "e.g. sessions, totalUsers, bounceRate, conversions, totalRevenue, screenPageViews",
                    },
                    "limit": {"type": "integer", "description": "Row limit (default 100)"},
                    **_format_option(),
                },
                "required": ["property_id"],
            },
        },
        {
            "name": "ga_run_realtime_report",
            "description": "Current active users, top pages, and top sources in real-time.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "GA4 property ID (numeric)"},
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Realtime-compatible dimensions (e.g. country, deviceCategory, unifiedPagePathScreen)",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Realtime-compatible metrics (e.g. activeUsers, screenPageViews)",
                    },
                    **_format_option(),
                },
                "required": ["property_id"],
            },
        },
        {
            "name": "ga_get_custom_dimensions",
            "description": "List all custom dimensions and metrics configured for a GA4 property.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "GA4 property ID (numeric)"},
                    **_format_option(),
                },
                "required": ["property_id"],
            },
        },
    ]


# ---------- client builders ----------


def _build_data_client(config: Config) -> BetaAnalyticsDataClient | None:
    creds_path = config.google_analytics.credentials_path
    if not creds_path or not creds_path.exists():
        return None
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
    return BetaAnalyticsDataClient()


def _load_service_account(path: Any) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_admin_token(config: Config) -> str | None:
    path = config.google_analytics.credentials_path
    if not path:
        return None
    import google.auth.transport.requests
    from google.oauth2 import service_account

    sa = service_account.Credentials.from_service_account_info(
        _load_service_account(path),
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    sa.refresh(google.auth.transport.requests.Request())
    return sa.token


@with_retry(attempts=3)
def _admin_get(path: str, token: str) -> dict[str, Any]:
    resp = requests.get(
        f"{ADMIN_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _cached_admin_get(path: str, token: str) -> dict[str, Any]:
    key = make_key("admin_get", path)
    cached = ANALYTICS_METADATA_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        result = _admin_get(path, token)
    except requests.HTTPError as e:
        resp = e.response
        status = resp.status_code if resp is not None else "?"
        body = resp.text[:500] if resp is not None else str(e)
        return {"_error": f"HTTP {status}: {body}"}
    except requests.RequestException as e:
        return {"_error": str(e)}
    ANALYTICS_METADATA_CACHE.set(key, result)
    return result


# ---------- handler ----------


async def handle_analytics_tool(
    tool_name: str, arguments: dict[str, Any], config: Config
) -> dict[str, Any]:
    client = _build_data_client(config)
    if not client:
        return _text(
            "Google Analytics credentials not found.\n"
            "Save your service account JSON to: credentials/google-analytics-credentials.json\n"
            "See docs/GOOGLE-ANALYTICS-SETUP.md for setup steps."
        )

    output_format = (arguments.get("format") or "text").lower()
    property_id = arguments.get("property_id", "")
    if not property_id and tool_name != "ga_get_account_summaries":
        return _text("property_id is required")
    if property_id and not property_id.isdigit():
        return _text("property_id must be numeric")

    try:
        if tool_name == "ga_get_account_summaries":
            return _summaries(config, output_format)
        if tool_name == "ga_get_property_details":
            return _property_details(config, property_id, output_format)
        if tool_name == "ga_get_custom_dimensions":
            return _custom_dimensions(config, property_id, output_format)
        if tool_name == "ga_run_report":
            return _run_report(client, arguments, output_format)
        if tool_name == "ga_run_realtime_report":
            return _run_realtime(client, arguments, output_format)
    except Exception as e:
        logger.exception("GA tool %s failed", tool_name)
        return _text(f"GA Error: {e}")

    return _text(f"Unknown tool: {tool_name}")


# ---------- individual tools ----------


def _summaries(config: Config, output_format: str) -> dict[str, Any]:
    token = _get_admin_token(config)
    if not token:
        return _text("Could not obtain Admin API token")
    data = _cached_admin_get("/accountSummaries", token)
    if "_error" in data:
        return _text(f"Admin API error: {data['_error']}")
    if output_format == "json":
        return _text(json.dumps(data, indent=2, default=str))

    accounts = data.get("accountSummaries", [])
    lines = ["=== Google Analytics Accounts & Properties ===", ""]
    for acc in accounts:
        lines.append(f"Account: {acc.get('displayName', '?')} ({acc.get('account', '?')})")
        for prop in acc.get("propertySummaries", []):
            # property name looks like "properties/123456789"; extract numeric ID
            full = prop.get("property", "")
            prop_id = full.split("/")[-1] if "/" in full else full
            lines.append(f"  Property: {prop.get('displayName', '?')}")
            lines.append(f"    ID: {prop_id}")
        lines.append("")
    return _text("\n".join(lines))


def _property_details(config: Config, property_id: str, output_format: str) -> dict[str, Any]:
    token = _get_admin_token(config)
    if not token:
        return _text("Could not obtain Admin API token")
    data = _cached_admin_get(f"/properties/{property_id}", token)
    if "_error" in data:
        return _text(f"Admin API error: {data['_error']}")
    if output_format == "json":
        return _text(json.dumps(data, indent=2, default=str))

    lines = ["=== Property Details ==="]
    for k, v in data.items():
        if k != "name":
            lines.append(f"  {k}: {v}")
    return _text("\n".join(lines))


def _custom_dimensions(config: Config, property_id: str, output_format: str) -> dict[str, Any]:
    token = _get_admin_token(config)
    if not token:
        return _text("Could not obtain Admin API token")
    dims_resp = _cached_admin_get(f"/properties/{property_id}/customDimensions", token)
    metrics_resp = _cached_admin_get(f"/properties/{property_id}/customMetrics", token)

    if output_format == "json":
        return _text(
            json.dumps(
                {"customDimensions": dims_resp, "customMetrics": metrics_resp},
                indent=2,
                default=str,
            )
        )

    dims = dims_resp.get("customDimensions", []) if isinstance(dims_resp, dict) else []
    mets = metrics_resp.get("customMetrics", []) if isinstance(metrics_resp, dict) else []
    lines = ["=== Custom Dimensions ==="]
    if not dims:
        lines.append("No custom dimensions.")
    else:
        for d in dims:
            lines.append(
                f"  {d.get('parameterName', '')} - {d.get('displayName', '')} (scope: {d.get('scope', '')})"
            )
    lines.append("")
    lines.append("=== Custom Metrics ===")
    if not mets:
        lines.append("No custom metrics.")
    else:
        for m in mets:
            lines.append(
                f"  {m.get('parameterName', '')} - {m.get('displayName', '')} (unit: {m.get('measurementUnit', '')})"
            )
    return _text("\n".join(lines))


def _run_report(
    client: BetaAnalyticsDataClient, arguments: dict[str, Any], output_format: str
) -> dict[str, Any]:
    property_id = arguments["property_id"]
    start = arguments.get("start_date", "30daysAgo")
    end = arguments.get("end_date", "today")
    dimensions = arguments.get("dimensions") or ["country", "deviceCategory"]
    metrics = arguments.get("metrics") or ["sessions", "totalUsers", "bounceRate"]
    limit = int(arguments.get("limit", 100))

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start, end_date=end)],
        limit=limit,
    )
    response = client.run_report(request)
    rows = list(response.rows)

    if output_format == "json":
        return _text(_report_to_json(rows, dimensions, metrics, label=f"{start} to {end}"))
    formatted = _format_report(rows, dimensions, metrics)
    return _text(f"=== Report: {start} to {end} ===\n\n{formatted}")


def _run_realtime(
    client: BetaAnalyticsDataClient, arguments: dict[str, Any], output_format: str
) -> dict[str, Any]:
    property_id = arguments["property_id"]
    dimensions = arguments.get("dimensions") or ["country"]
    metrics = arguments.get("metrics") or ["activeUsers"]

    request = RunRealtimeReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
    )
    response = client.run_realtime_report(request)
    rows = list(response.rows)

    if output_format == "json":
        return _text(_report_to_json(rows, dimensions, metrics, label="realtime"))
    formatted = _format_report(rows, dimensions, metrics)
    return _text(f"=== Real-Time Report ===\n\n{formatted}")


# ---------- formatters ----------


def _format_report(rows: list[Any], dimensions: list[str], metrics: list[str]) -> str:
    if not rows:
        return "No data returned for this report."
    header = (
        f"{'Row':<4} "
        + " | ".join(f"{d[:15]:<16}" for d in dimensions)
        + " | "
        + " | ".join(f"{m[:15]:<16}" for m in metrics)
    )
    lines = [header, "-" * len(header)]
    for i, row in enumerate(rows, 1):
        dim_vals = [str(d.value)[:15].ljust(16) for d in row.dimension_values]
        met_vals = [str(v.value)[:15].ljust(16) for v in row.metric_values]
        lines.append(f"{i:<4} " + " | ".join(dim_vals) + " | " + " | ".join(met_vals))
    return "\n".join(lines)


def _report_to_json(
    rows: list[Any], dimensions: list[str], metrics: list[str], label: str
) -> str:
    out = {
        "label": label,
        "dimensions": dimensions,
        "metrics": metrics,
        "rows": [
            {
                "dimensions": dict(zip(dimensions, [d.value for d in row.dimension_values], strict=False)),
                "metrics": dict(zip(metrics, [v.value for v in row.metric_values], strict=False)),
            }
            for row in rows
        ],
    }
    return json.dumps(out, indent=2, default=str)


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}
