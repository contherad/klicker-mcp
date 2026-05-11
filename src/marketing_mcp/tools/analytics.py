"""Google Analytics 4 tools using google-analytics-data pip package."""

import os
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from google.api_core.client_options import ClientOptions


def get_analytics_tools():
    return [
        {
            "name": "ga_get_account_summaries",
            "description": "List all Google Analytics accounts and properties the user has access to.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "ga_get_property_details",
            "description": "Get details about a specific GA4 property.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "property_id": {
                        "type": "string",
                        "description": "GA4 property ID (numeric, e.g. 123456789)",
                    },
                },
                "required": ["property_id"],
            },
        },
        {
            "name": "ga_run_report",
            "description": "Run a Google Analytics report: sessions, users, bounce rate, conversions for a date range. Great for building custom dashboards.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "GA4 property ID (numeric)"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (default: 30 days ago)"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD (default: yesterday)"},
                    "dimensions": {"type": "array", "items": {"type": "string"}, "description": "Break down by: city, deviceCategory, country, pagePath, source, medium, campaign"},
                    "metrics": {"type": "array", "items": {"type": "string"}, "description": "Metrics: sessions, users, bounceRate, conversions, totalRevenue, screenPageViews"},
                },
                "required": ["property_id"],
            },
        },
        {
            "name": "ga_run_realtime_report",
            "description": "Get current active users, top pages, and top sources/referrers in real-time.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "GA4 property ID (numeric)"},
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
                },
                "required": ["property_id"],
            },
        },
    ]


def _get_analytics_client(config):
    creds_path = config.google_analytics.credentials_path
    project_id = config.google_analytics.project_id or os.environ.get("GOOGLE_PROJECT_ID", "")
    if not creds_path or not creds_path.exists():
        return None, project_id
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
    options = ClientOptions()
    return BetaAnalyticsDataClient(), project_id


def _format_report(rows, dimensions, metrics):
    if not rows:
        return "No data returned for this report."
    header = f"{'Row':<4} " + " | ".join(f"{d[:15]:<16}" for d in dimensions) + " | " + " | ".join(f"{m[:15]:<16}" for m in metrics)
    lines = [header, "-" * len(header)]
    for i, row in enumerate(rows, 1):
        dim_vals = [str(d.value)[:15].ljust(16) for d in row.dimension_values]
        met_vals = [str(v.value)[:15].ljust(16) for v in row.metric_values]
        lines.append(f"{i:<4} " + " | ".join(dim_vals) + " | " + " | ".join(met_vals))
    return "\n".join(lines)


async def handle_analytics_tool(tool_name, arguments, config):
    client, project_id = _get_analytics_client(config)
    if not client:
        return {"content": [{"type": "text", (
            "Google Analytics credentials not found.\n"
            "Save your service account JSON to: credentials/google-analytics-credentials.json\n"
            "Then restart the server.\n\n"
            "See docs/GOOGLE-ANALYTICS-SETUP.md for step-by-step instructions."
        )}]}

    property_id = arguments.get("property_id", "")
    if not property_id:
        return {"content": [{"type": "text", "property_id is required"}]}

    try:
        if tool_name == "ga_get_account_summaries":
            # Use Admin API via REST for account listing
            import requests
            creds_path = config.google_analytics.credentials_path
            creds = _load_service_account(creds_path)
            token = _get_access_token(creds)
            headers = {"Authorization": f"Bearer {token}"}
            # List accounts
            resp = requests.get(
                "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
                headers=headers
            ).json()
            accounts = resp.get("accountSummaries", [])
            lines = ["=== Google Analytics Accounts & Properties ===", ""]
            for acc in accounts:
                lines.append(f"Account: {acc.get('account', '')} ({acc.get('accountId', '')})")
                for prop in acc.get("propertySummaries", []):
                    lines.append(f"  Property: {prop.get('property')}")
                    lines.append(f"    Display Name: {prop.get('displayName')}")
                    lines.append(f"    Property ID: {prop.get('propertyId', '')}")
                    lines.append("")
            return {"content": [{"type": "text", "\n".join(lines)}]}

        elif tool_name in ("ga_run_report", "ga_run_realtime_report"):
            is_realtime = tool_name == "ga_run_realtime_report"
            start = arguments.get("start_date", "30daysAgo")
            end = arguments.get("end_date", "today")
            dimensions = arguments.get("dimensions", ["country", "deviceCategory"])
            metrics = arguments.get("metrics", ["sessions", "users", "bounceRate"])

            dim_objs = [Dimension(name=d) for d in dimensions]
            met_objs = [Metric(name=m) for m in metrics]

            if is_realtime:
                request = RunReportRequest(
                    property=f"properties/{property_id}",
                    dimensions=dim_objs,
                    metrics=met_objs,
                    date_ranges=[DateRange(start_date="today", end_date="today")],
                )
            else:
                request = RunReportRequest(
                    property=f"properties/{property_id}",
                    dimensions=dim_objs,
                    metrics=met_objs,
                    date_ranges=[DateRange(start_date=start, end_date=end)],
                )

            response = client.run_report(request)
            rows = list(response.rows)
            formatted = _format_report(rows, dimensions, metrics)
            label = "Real-Time Report" if is_realtime else f"Report: {start} to {end}"
            return {"content": [{"type": "text", f"=== {label} ===\n\n{formatted}"}]}

        elif tool_name == "ga_get_property_details":
            import requests
            creds = _load_service_account(config.google_analytics.credentials_path)
            token = _get_access_token(creds)
            resp = requests.get(
                f"https://analyticsadmin.googleapis.com/v1/properties/{property_id}",
                headers={"Authorization": f"Bearer {token}"}
            ).json()
            lines = ["=== Property Details ==="]
            for k, v in resp.items():
                if k != "name":
                    lines.append(f"  {k}: {v}")
            return {"content": [{"type": "text", "\n".join(lines)}]}

        elif tool_name == "ga_get_custom_dimensions":
            import requests
            creds = _load_service_account(config.google_analytics.credentials_path)
            token = _get_access_token(creds)
            resp = requests.get(
                f"https://analyticsadmin.googleapis.com/v1/properties/{property_id}/customDimensions",
                headers={"Authorization": f"Bearer {token}"}
            ).json()
            dims = resp.get("customDimensions", [])
            lines = ["=== Custom Dimensions ===", ""]
            if not dims:
                lines.append("No custom dimensions found.")
            else:
                for d in dims:
                    lines.append(f"  {d.get('parameterName', '')} - {d.get('displayName', '')} (scope: {d.get('scope', '')})")
            resp2 = requests.get(
                f"https://analyticsadmin.googleapis.com/v1/properties/{property_id}/customMetrics",
                headers={"Authorization": f"Bearer {token}"}
            ).json()
            mets = resp2.get("customMetrics", [])
            lines.append("")
            lines.append("=== Custom Metrics ===")
            if not mets:
                lines.append("No custom metrics found.")
            else:
                for m in mets:
                    lines.append(f"  {m.get('parameterName', '')} - {m.get('displayName', '')} (type: {m.get('measurementUnit', '')})")
            return {"content": [{"type": "text", "\n".join(lines)}]}

    except Exception as e:
        return {"content": [{"type": "text", f"GA Error: {e}"}]}

    return {"content": [{"type": "text", f"Unknown tool: {tool_name}"}]}


def _load_service_account(path):
    import json
    with open(path) as f:
        return json.load(f)


def _get_access_token(creds):
    import google.auth.transport.requests
    from google.oauth2 import service_account
    scoped = creds.copy()
    scoped["scopes"] = ["https://www.googleapis.com/auth/analytics.readonly"]
    sa = service_account.Credentials.from_service_account_info(scoped)
    req = google.auth.transport.requests.Request()
    sa.refresh(req)
    return sa.token