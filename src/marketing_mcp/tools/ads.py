"""Google Ads tools using google-ads-python client library."""

import os

def get_ads_tools():
    return [
        {
            "name": "ads_get_campaigns",
            "description": "List all active Google Ads campaigns with name, status, budget, and current cost.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Google Ads customer ID (no dashes, e.g. 1234567890)"},
                    "limit": {"type": "integer", "description": "Max campaigns to return (default 50)"},
                },
                "required": ["customer_id"],
            },
        },
        {
            "name": "ads_get_campaign_performance",
            "description": "Get cost, clicks, impressions, CTR, CPC, and conversions for a campaign over a date range.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Google Ads customer ID (no dashes)"},
                    "campaign_id": {"type": "string", "description": "Campaign ID (numeric)"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                },
                "required": ["customer_id", "campaign_id", "start_date", "end_date"],
            },
        },
        {
            "name": "ads_get_keywords_performance",
            "description": "Get performance stats per keyword: clicks, cost, conversions, CTR, average CPC.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Google Ads customer ID (no dashes)"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                    "limit": {"type": "integer", "description": "Max keywords (default 100)"},
                },
                "required": ["customer_id", "start_date", "end_date"],
            },
        },
        {
            "name": "ads_get_ad_groups",
            "description": "List ad groups for a campaign with name, status, and current cost.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Google Ads customer ID (no dashes)"},
                    "campaign_id": {"type": "string", "description": "Campaign ID (numeric, optional to filter)"},
                },
                "required": ["customer_id"],
            },
        },
        {
            "name": "ads_get_account_summary",
            "description": "Get high-level spend, clicks, impressions, and conversions across the entire Google Ads account.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Google Ads customer ID (no dashes)"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                },
                "required": ["customer_id", "start_date", "end_date"],
            },
        },
    ]


async def handle_ads_tool(tool_name, arguments, config):
    creds = config.google_ads
    if not creds.developer_token:
        msg = ("Google Ads credentials not configured.\n"
               "Save your credentials JSON to: credentials/google-ads-credentials.json\n"
               "See docs/GOOGLE-ADS-SETUP.md for step-by-step instructions.")
        return {"content": [{"type": "text", "text": msg}]}

    try:
        from google.ads.googleads import Client as GoogleAdsClient
    except ImportError:
        return {"content": [{"type": "text", "text": "Install google-ads: pip install google-ads>=24.0.0"}]}

    try:
        client = GoogleAdsClient.load_from_dict({
            "developer_token": creds.developer_token,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "refresh_token": creds.refresh_token,
            "use_proto_plus": True,
        })
    except Exception as e:
        err = "Failed to initialize Google Ads client: " + str(e)
        return {"content": [{"type": "text", "text": err}]}

    customer_id = arguments.get("customer_id", "").replace("-", "")

    try:
        if tool_name == "ads_get_campaigns":
            return await _get_campaigns(client, customer_id, arguments.get("limit", 50))
        elif tool_name == "ads_get_campaign_performance":
            return await _get_campaign_performance(client, customer_id, arguments)
        elif tool_name == "ads_get_keywords_performance":
            return await _get_keywords_performance(client, customer_id, arguments)
        elif tool_name == "ads_get_ad_groups":
            return await _get_ad_groups(client, customer_id, arguments.get("campaign_id"))
        elif tool_name == "ads_get_account_summary":
            return await _get_account_summary(client, customer_id, arguments)
    except Exception as e:
        err = "Ads API error: " + str(e)
        return {"content": [{"type": "text", "text": err}]}

    err = "Unknown tool: " + tool_name
    return {"content": [{"type": "text", "text": err}]}


async def _get_campaigns(client, customer_id, limit=50):
    query = f"""
        SELECT campaign.id, campaign.name, campaign.status, campaign.total_amount_micros,
               metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.ctr, metrics.average_cpc
        FROM campaign
        ORDER BY metrics.cost_micros DESC
        LIMIT {limit}
    """
    results = _run_query(client, customer_id, query)
    lines = ["=== Google Ads Campaigns ==="]
    if not results:
        lines.append("No campaigns found or no access to this account.")
    else:
        lines.append(f"{'Campaign Name':<40} {'Status':<10} {'Spent':<12} {'Clicks':<8} {'Impr':<10} {'CTR':<8} {'Avg CPC':<10}")
        lines.append("-" * 110)
        for row in results:
            name = str(row.campaign.name)[:38]
            status = str(row.campaign.status).split(".")[-1]
            cost = _micros_dollars(row.metrics.cost_micros)
            clicks = row.metrics.clicks
            impr = row.metrics.impressions
            ctr = f"{row.metrics.ctr:.2%}"
            cpc = f"${_micros_dollars(row.metrics.average_cpc)}"
            lines.append(f"{name:<40} {status:<10} ${cost:<11} {clicks:<8} {impr:<10} {ctr:<8} {cpc:<10}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


async def _get_campaign_performance(client, customer_id, args):
    campaign_id = args.get("campaign_id", "")
    start = args.get("start_date", "")
    end = args.get("end_date", "")
    query = f"""
        SELECT campaign.name, campaign.status, campaign.budget.amount_micros,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.ctr, metrics.average_cpc, metrics.conversions
        FROM campaign
        WHERE campaign.id = {campaign_id}
          AND segments.date BETWEEN '{start}' AND '{end}'
    """
    results = _run_query(client, customer_id, query)
    lines = [f"=== Campaign {campaign_id} Performance: {start} to {end} ==="]
    if not results:
        lines.append("No data for this campaign and date range.")
    else:
        row = results[0]
        lines.append(f"Campaign: {row.campaign.name}")
        lines.append(f"Status: {str(row.campaign.status).split('.')[-1]}")
        lines.append(f"Budget: ${_micros_dollars(row.campaign.budget.amount_micros) if hasattr(row.campaign, 'budget') and row.campaign.budget else 'N/A'}")
        lines.append(f"Spend: ${_micros_dollars(row.metrics.cost_micros)}")
        lines.append(f"Clicks: {row.metrics.clicks}")
        lines.append(f"Impressions: {row.metrics.impressions}")
        lines.append(f"CTR: {row.metrics.ctr:.2%}")
        lines.append(f"Avg CPC: ${_micros_dollars(row.metrics.average_cpc)}")
        lines.append(f"Conversions: {row.metrics.conversions}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


async def _get_keywords_performance(client, customer_id, args):
    start = args.get("start_date", "")
    end = args.get("end_date", "")
    limit = args.get("limit", 100)
    query = f"""
        SELECT keyword_view.keyword.text, keyword_view.keyword.match_type,
               metrics.clicks, metrics.cost_micros, metrics.impressions,
               metrics.ctr, metrics.conversions
        FROM keyword_view
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        ORDER BY metrics.cost_micros DESC
        LIMIT {limit}
    """
    results = _run_query(client, customer_id, query)
    lines = ["=== Keyword Performance ==="]
    if not results:
        lines.append("No keyword data found.")
    else:
        lines.append(f"{'Keyword':<30} {'Match':<8} {'Clicks':<8} {'Cost':<10} {'Impr':<8} {'CTR':<8} {'Conv':<6}")
        lines.append("-" * 90)
        for row in results:
            kw = str(row.keyword_view.keyword.text)[:28]
            mt = str(row.keyword_view.keyword.match_type).split(".")[-1]
            lines.append(
                f"{kw:<30} {mt:<8} {row.metrics.clicks:<8} "
                f"${_micros_dollars(row.metrics.cost_micros):<9} {row.metrics.impressions:<8} "
                f"{row.metrics.ctr:.2%}    {row.metrics.conversions:<6}"
            )
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


async def _get_ad_groups(client, customer_id, campaign_id=None):
    query = f"""
        SELECT ad_group.id, ad_group.name, ad_group.status,
               metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.ctr
        FROM ad_group
        {"WHERE ad_group.campaign = 'campaigns/" + campaign_id + "'" if campaign_id else ""}
        ORDER BY metrics.cost_micros DESC
        LIMIT 200
    """
    results = _run_query(client, customer_id, query)
    lines = ["=== Ad Groups ==="]
    if not results:
        lines.append("No ad groups found.")
    else:
        for row in results:
            ag_id = row.ad_group.id
            name = row.ad_group.name
            status = str(row.ad_group.status).split(".")[-1]
            cost = _micros_dollars(row.metrics.cost_micros)
            lines.append(f"[{ag_id}] {name} | Status: {status} | Spend: ${cost}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


async def _get_account_summary(client, customer_id, args):
    start = args.get("start_date", "")
    end = args.get("end_date", "")
    query = f"""
        SELECT campaign.name,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.ctr, metrics.conversions, metrics.average_cpc
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
        ORDER BY metrics.cost_micros DESC
    """
    results = _run_query(client, customer_id, query)
    total_cost = total_clicks = total_impr = total_conv = 0
    lines = [f"=== Google Ads Account Summary: {start} to {end} ===", ""]

    if not results:
        lines.append("No data for this period.")
    else:
        for row in results:
            c = row.metrics.cost_micros
            total_cost += c if c else 0
            total_clicks += row.metrics.clicks if row.metrics.clicks else 0
            total_impr += row.metrics.impressions if row.metrics.impressions else 0
            total_conv += row.metrics.conversions if row.metrics.conversions else 0
            lines.append(f"  {row.campaign.name}: ${_micros_dollars(c or 0)}")

        lines.append("")
        lines.append(f"TOTAL SPEND:     ${_micros_dollars(total_cost)}")
        lines.append(f"TOTAL CLICKS:    {total_clicks:,}")
        lines.append(f"TOTAL IMPRESSIONS: {total_impr:,}")
        lines.append(f"TOTAL CONVERSIONS: {total_conv}")
        if total_clicks > 0:
            lines.append(f"AVG CTR:         {(total_clicks/total_impr*100):.2f}%" if total_impr > 0 else "AVG CTR: N/A")
        if total_cost > 0 and total_conv > 0:
            lines.append(f"COST PER CONV:   ${_micros_dollars(total_cost)/total_conv:.2f}")

    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def _run_query(client, customer_id, query):
    try:
        ga_service = client.get_service("GoogleAdsService")
        stream = ga_service.search_stream(customer_id=customer_id, query=query)
        return list(stream)
    except Exception:
        return []


def _micros_dollars(micros):
    if micros is None:
        return "0.00"
    return f"{micros / 1_000_000:.2f}"