from .analytics import get_analytics_tools, handle_analytics_tool
from .ads import get_ads_tools, handle_ads_tool
from .tagmanager import get_tagmanager_tools, handle_tagmanager_tool
from .ahrefs import get_ahrefs_tools, handle_ahrefs_tool

def get_all_tools():
    return (
        get_analytics_tools()
        + get_ads_tools()
        + get_tagmanager_tools()
        + get_ahrefs_tools()
    )

def get_all_handlers():
    return {
        # analytics
        "ga_get_account_summaries": handle_analytics_tool,
        "ga_get_property_details": handle_analytics_tool,
        "ga_run_report": handle_analytics_tool,
        "ga_run_realtime_report": handle_analytics_tool,
        "ga_get_custom_dimensions": handle_analytics_tool,
        # ads
        "ads_get_campaigns": handle_ads_tool,
        "ads_get_campaign_performance": handle_ads_tool,
        "ads_get_keywords_performance": handle_ads_tool,
        "ads_get_ad_groups": handle_ads_tool,
        "ads_get_account_summary": handle_ads_tool,
        # tagmanager
        "gtm_list_containers": handle_tagmanager_tool,
        "gtm_get_workspace_tags": handle_tagmanager_tool,
        "gtm_list_triggers": handle_tagmanager_tool,
        "gtm_list_variables": handle_tagmanager_tool,
        "gtm_get_container_version": handle_tagmanager_tool,
        # ahrefs
        "ahrefs_get_domain_rating": handle_ahrefs_tool,
        "ahrefs_get_backlinks": handle_ahrefs_tool,
        "ahrefs_get_organic_keywords": handle_ahrefs_tool,
        "ahrefs_get_linking_domains": handle_ahrefs_tool,
        "ahrefs_compare_domains": handle_ahrefs_tool,
        "ahrefs_get_anchor_text": handle_ahrefs_tool,
    }