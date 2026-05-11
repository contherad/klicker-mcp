"""Google Tag Manager tools via google-api-python-client."""

from __future__ import annotations

import json
from typing import Any

from marketing_mcp.utils.cache import GTM_METADATA_CACHE, make_key
from marketing_mcp.utils.config import Config
from marketing_mcp.utils.logging import get_logger

logger = get_logger("tools.tagmanager")

SCOPES = ["https://www.googleapis.com/auth/tagmanager.readonly"]


# ---------- tool definitions ----------


def _format_option() -> dict[str, Any]:
    return {
        "format": {
            "type": "string",
            "enum": ["text", "json"],
            "description": "Output format. Defaults to text.",
        }
    }


def get_tagmanager_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "gtm_list_accounts",
            "description": "List all GTM accounts the service account has access to.",
            "inputSchema": {"type": "object", "properties": {**_format_option()}},
        },
        {
            "name": "gtm_list_containers",
            "description": "List all GTM containers in an account.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "GTM account ID"},
                    **_format_option(),
                },
                "required": ["account_id"],
            },
        },
        {
            "name": "gtm_get_workspace_tags",
            "description": "List all tags in a GTM container workspace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "container_id": {"type": "string"},
                    "workspace_id": {"type": "string", "description": "Workspace ID (default: 'default')"},
                    **_format_option(),
                },
                "required": ["account_id", "container_id"],
            },
        },
        {
            "name": "gtm_list_triggers",
            "description": "List all triggers in a GTM container workspace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "container_id": {"type": "string"},
                    "workspace_id": {"type": "string"},
                    **_format_option(),
                },
                "required": ["account_id", "container_id"],
            },
        },
        {
            "name": "gtm_list_variables",
            "description": "List all variables in a GTM container workspace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "container_id": {"type": "string"},
                    "workspace_id": {"type": "string"},
                    **_format_option(),
                },
                "required": ["account_id", "container_id"],
            },
        },
        {
            "name": "gtm_get_container_version",
            "description": "Get details about a specific container version.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "container_id": {"type": "string"},
                    "version_id": {"type": "string"},
                    **_format_option(),
                },
                "required": ["account_id", "container_id", "version_id"],
            },
        },
    ]


# ---------- handler ----------


async def handle_tagmanager_tool(tool_name: str, arguments: dict[str, Any], config: Config) -> dict[str, Any]:
    creds_path = config.google_tag_manager.credentials_path
    if not creds_path or not creds_path.exists():
        return _text(
            "Google Tag Manager credentials not found.\n"
            "Save your service account JSON to: credentials/google-tag-manager-credentials.json\n"
            "See docs/GOOGLE-TAG-MANAGER-SETUP.md for setup steps."
        )

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        return _text("Install: pip install google-api-python-client>=2.100.0")

    credentials = service_account.Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    gtm = build("tagmanager", "v2", credentials=credentials, cache_discovery=False)

    account_id = arguments.get("account_id") or config.google_tag_manager.account_id or ""
    container_id = arguments.get("container_id") or config.google_tag_manager.container_id or ""
    workspace = arguments.get("workspace_id", "default")
    output_format = (arguments.get("format") or "text").lower()

    try:
        if tool_name == "gtm_list_accounts":
            return _list_accounts(gtm, output_format)
        if tool_name == "gtm_list_containers":
            return _list_containers(gtm, account_id, output_format)
        if tool_name == "gtm_get_workspace_tags":
            return _get_workspace_tags(gtm, account_id, container_id, workspace, output_format)
        if tool_name == "gtm_list_triggers":
            return _list_triggers(gtm, account_id, container_id, workspace, output_format)
        if tool_name == "gtm_list_variables":
            return _list_variables(gtm, account_id, container_id, workspace, output_format)
        if tool_name == "gtm_get_container_version":
            return _get_container_version(
                gtm, account_id, container_id, arguments.get("version_id"), output_format
            )
    except Exception as e:
        logger.exception("GTM tool %s failed", tool_name)
        return _text(f"GTM API error: {e}")

    return _text(f"Unknown tool: {tool_name}")


# ---------- individual tools ----------


def _list_accounts(gtm: Any, output_format: str) -> dict[str, Any]:
    key = make_key("accounts")
    cached = GTM_METADATA_CACHE.get(key)
    if cached is None:
        cached = gtm.accounts().list().execute()
        GTM_METADATA_CACHE.set(key, cached)
    accounts = cached.get("account", [])

    if output_format == "json":
        return _text(json.dumps(accounts, indent=2, default=str))

    lines = ["=== GTM Accounts ==="]
    if not accounts:
        lines.append("No accounts accessible by this service account.")
    else:
        header = f"{'Name':<35} {'Account ID':<15}"
        lines.append(header)
        lines.append("-" * len(header))
        for a in accounts:
            lines.append(f"{a.get('name', ''):<35} {a.get('accountId', ''):<15}")
    return _text("\n".join(lines))


def _list_containers(gtm: Any, account_id: str, output_format: str) -> dict[str, Any]:
    if not account_id:
        return _text("account_id is required")
    key = make_key("containers", account_id)
    cached = GTM_METADATA_CACHE.get(key)
    if cached is None:
        cached = gtm.accounts().containers().list(parent=f"accounts/{account_id}").execute()
        GTM_METADATA_CACHE.set(key, cached)
    containers = cached.get("container", [])

    if output_format == "json":
        return _text(json.dumps(containers, indent=2, default=str))

    lines = ["=== Tag Manager Containers ==="]
    if not containers:
        lines.append("No containers found for this account.")
    else:
        header = f"{'Name':<40} {'Container ID':<15} {'Public ID':<15} {'Domain'}"
        lines.append(header)
        lines.append("-" * len(header))
        for c in containers:
            domains = c.get("domainName") or []
            domains_str = ", ".join(domains) if isinstance(domains, list) else str(domains)
            lines.append(
                f"{c.get('name', ''):<40} "
                f"{c.get('containerId', ''):<15} "
                f"{c.get('publicId', ''):<15} "
                f"{domains_str[:40]}"
            )
    return _text("\n".join(lines))


def _workspace_path(gtm: Any, account_id: str, container_id: str, workspace: str) -> str | None:
    """Resolve workspace identifier to its full path. 'default' = first workspace."""
    workspaces = (
        gtm.accounts()
        .containers()
        .workspaces()
        .list(parent=f"accounts/{account_id}/containers/{container_id}")
        .execute()
        .get("workspace", [])
    )
    if not workspaces:
        return None
    if workspace == "default":
        return workspaces[0].get("path")
    for w in workspaces:
        if workspace in (str(w.get("workspaceId", "")), w.get("name", "")):
            return w.get("path")
    return None


def _get_workspace_tags(
    gtm: Any, account_id: str, container_id: str, workspace: str, output_format: str
) -> dict[str, Any]:
    path = _workspace_path(gtm, account_id, container_id, workspace)
    if not path:
        return _text(f"Workspace '{workspace}' not found.")
    tags = gtm.accounts().containers().workspaces().tags().list(parent=path).execute().get("tag", [])

    if output_format == "json":
        return _text(json.dumps(tags, indent=2, default=str))

    lines = [f"=== Tags in Workspace: {workspace} ==="]
    if not tags:
        lines.append("No tags found (container may not be published).")
    else:
        header = f"{'Name':<40} {'Type':<28} {'Trigger IDs'}"
        lines.append(header)
        lines.append("-" * len(header))
        for t in tags:
            trigger_ids = ",".join(str(tid) for tid in (t.get("firingTriggerId", []) or []))
            name = t.get("name", "")[:38]
            ttype = str(t.get("type", ""))[:26]
            lines.append(f"{name:<40} {ttype:<28} {trigger_ids or 'none'}")
    return _text("\n".join(lines))


def _list_triggers(
    gtm: Any, account_id: str, container_id: str, workspace: str, output_format: str
) -> dict[str, Any]:
    path = _workspace_path(gtm, account_id, container_id, workspace)
    if not path:
        return _text(f"Workspace '{workspace}' not found.")
    triggers = (
        gtm.accounts().containers().workspaces().triggers().list(parent=path).execute().get("trigger", [])
    )

    if output_format == "json":
        return _text(json.dumps(triggers, indent=2, default=str))

    lines = ["=== Triggers ==="]
    if not triggers:
        lines.append("No triggers found.")
    else:
        for t in triggers:
            tid = t.get("triggerId", "")
            name = t.get("name", "")
            ttype = t.get("type", "")
            has_filter = "yes" if t.get("filter") else "no"
            lines.append(f"  [{tid}] {name} | type: {ttype} | has filters: {has_filter}")
    return _text("\n".join(lines))


def _list_variables(
    gtm: Any, account_id: str, container_id: str, workspace: str, output_format: str
) -> dict[str, Any]:
    path = _workspace_path(gtm, account_id, container_id, workspace)
    if not path:
        return _text(f"Workspace '{workspace}' not found.")
    variables = (
        gtm.accounts().containers().workspaces().variables().list(parent=path).execute().get("variable", [])
    )

    if output_format == "json":
        return _text(json.dumps(variables, indent=2, default=str))

    lines = ["=== Variables ==="]
    if not variables:
        lines.append("No variables found.")
    else:
        for v in variables:
            vid = v.get("variableId", "")
            name = v.get("name", "")
            vtype = v.get("type", "")
            lines.append(f"  [{vid}] {name} | type: {vtype}")
    return _text("\n".join(lines))


def _get_container_version(
    gtm: Any,
    account_id: str,
    container_id: str,
    version_id: str | None,
    output_format: str,
) -> dict[str, Any]:
    if not version_id:
        return _text("version_id is required")
    path = f"accounts/{account_id}/containers/{container_id}/versions/{version_id}"
    v = gtm.accounts().containers().versions().get(path=path).execute()

    if output_format == "json":
        return _text(json.dumps(v, indent=2, default=str))

    lines = [f"=== Container Version {version_id} ==="]
    lines.append(f"Name:     {v.get('name', 'N/A')}")
    lines.append(f"Status:   {v.get('status', 'N/A')}")
    lines.append(f"Created:  {v.get('created', 'N/A')}")
    lines.append(f"Modified: {v.get('modified', 'N/A')}")
    lines.append(f"Num tags: {len(v.get('container', {}).get('tag', []))}")
    return _text("\n".join(lines))


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}
