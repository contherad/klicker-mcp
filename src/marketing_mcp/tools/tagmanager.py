"""Google Tag Manager tools using google-api-python-client."""

import os


def get_tagmanager_tools():
    return [
        {
            "name": "gtm_list_containers",
            "description": "List all Google Tag Manager containers in the account.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "GTM account ID"},
                },
            },
        },
        {
            "name": "gtm_get_workspace_tags",
            "description": "List all tags in a GTM container workspace. Shows what tracking scripts are deployed.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "GTM account ID"},
                    "container_id": {"type": "string", "description": "GTM container ID"},
                    "workspace_id": {"type": "string", "description": "Workspace ID (default: 'default')"},
                },
                "required": ["account_id", "container_id"],
            },
        },
        {
            "name": "gtm_list_triggers",
            "description": "List all triggers in a GTM container workspace (what events fire which tags).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "GTM account ID"},
                    "container_id": {"type": "string", "description": "GTM container ID"},
                    "workspace_id": {"type": "string", "description": "Workspace ID (default: 'default')"},
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
                    "account_id": {"type": "string", "description": "GTM account ID"},
                    "container_id": {"type": "string", "description": "GTM container ID"},
                    "workspace_id": {"type": "string", "description": "Workspace ID (default: 'default')"},
                },
                "required": ["account_id", "container_id"],
            },
        },
        {
            "name": "gtm_get_container_version",
            "description": "Get details about a specific container version (who published it, when).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "GTM account ID"},
                    "container_id": {"type": "string", "description": "GTM container ID"},
                    "version_id": {"type": "string", "description": "Container version ID"},
                },
                "required": ["account_id", "container_id", "version_id"],
            },
        },
    ]


async def handle_tagmanager_tool(tool_name, arguments, config):
    creds_path = config.google_tag_manager.credentials_path
    if not creds_path or not creds_path.exists():
        msg = ("Google Tag Manager credentials not found.\n"
               "Save your service account JSON to: credentials/google-tag-manager-credentials.json\n"
               "See docs/GOOGLE-TAG-MANAGER-SETUP.md for step-by-step instructions.")
        return {"content": [{"type": "text", "text": msg}]}

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        return {"content": [{"type": "text", "text": "Install: pip install google-api-python-client>=2.100.0"}]}

    SCOPES = ["https://www.googleapis.com/auth/tagmanager.readonly"]
    credentials = service_account.Credentials.from_service_account_file(
        str(creds_path), scopes=SCOPES
    )
    gtm = build("tagmanager", "v2", credentials=credentials, cache_discovery=False)

    account_id = arguments.get("account_id") or config.google_tag_manager.account_id or ""
    container_id = arguments.get("container_id") or config.google_tag_manager.container_id or ""
    workspace = arguments.get("workspace_id", "default")

    try:
        if tool_name == "gtm_list_containers":
            return _list_containers(gtm, account_id)
        elif tool_name == "gtm_get_workspace_tags":
            return _get_workspace_tags(gtm, account_id, container_id, workspace)
        elif tool_name == "gtm_list_triggers":
            return _list_triggers(gtm, account_id, container_id, workspace)
        elif tool_name == "gtm_list_variables":
            return _list_variables(gtm, account_id, container_id, workspace)
        elif tool_name == "gtm_get_container_version":
            return _get_container_version(gtm, account_id, container_id, arguments.get("version_id"))
    except Exception as e:
        return {"content": [{"type": "text", "text": "GTM API error: " + str(e)}]}

    return {"content": [{"type": "text", "text": "Unknown tool: " + tool_name}]}


def _workspace_path(gtm, account_id, container_id, workspace="default"):
    """Find the workspace path by name or ID."""
    workspaces = gtm.accounts().containers().workspaces().list(
        parent=f"accounts/{account_id}/containers/{container_id}"
    ).execute().get("workspace", [])
    for w in workspaces:
        if workspace in (str(w.get("workspaceId", "")), w.get("name", ""), "default"):
            return w.get("path")
    # Fall back to first workspace
    return workspaces[0]["path"] if workspaces else None


def _list_containers(gtm, account_id):
    if not account_id:
        return {"content": [{"type": "text", "text": "account_id is required"}]}
    resp = gtm.accounts().containers().list(parent=f"accounts/{account_id}").execute()
    containers = resp.get("container", [])
    lines = ["=== Google Tag Manager Containers ==="]
    if not containers:
        lines.append("No containers found for this account.")
    else:
        lines.append(f"{'Name':<40} {'Container ID':<15} {'Domain':<30}")
        lines.append("-" * 90)
        for c in containers:
            lines.append(f"{c.get('name',''):<40} {c.get('containerId',''):<15} {str(c.get('domainName','')[:28]):<30}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def _get_workspace_tags(gtm, account_id, container_id, workspace):
    path = _workspace_path(gtm, account_id, container_id, workspace)
    if not path:
        return {"content": [{"type": "text", "text": "Workspace '" + workspace + "' not found."}]}
    tags = gtm.accounts().containers().workspaces().tags().list(parent=path).execute().get("tag", [])
    lines = ["=== Tags in Workspace: " + workspace + " ==="]
    if not tags:
        lines.append("No tags found (container may not be published).")
    else:
        lines.append(f"{'Name':<40} {'Type':<28} {'Trigger IDs'}")
        lines.append("-" * 95)
        for t in tags:
            trigger_ids = ",".join(str(tid) for tid in (t.get("firingTriggerId", []) or []))
            name = t.get("name", "")[:38]
            ttype = str(t.get("type", ""))[:26]
            lines.append(f"{name:<40} {ttype:<28} {trigger_ids or 'none'}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def _list_triggers(gtm, account_id, container_id, workspace):
    path = _workspace_path(gtm, account_id, container_id, workspace)
    if not path:
        return {"content": [{"type": "text", "text": "Workspace '" + workspace + "' not found."}]}
    triggers = gtm.accounts().containers().workspaces().triggers().list(parent=path).execute().get("trigger", [])
    lines = ["=== Triggers ==="]
    if not triggers:
        lines.append("No triggers found.")
    else:
        for t in triggers:
            tid = t.get("triggerId", "")
            name = t.get("name", "")
            ttype = t.get("type", "")
            filters = "yes" if t.get("filter") else "no"
            lines.append(f"  [{tid}] {name} | type: {ttype} | has filters: {filters}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def _list_variables(gtm, account_id, container_id, workspace):
    path = _workspace_path(gtm, account_id, container_id, workspace)
    if not path:
        return {"content": [{"type": "text", "text": "Workspace '" + workspace + "' not found."}]}
    variables = gtm.accounts().containers().workspaces().variables().list(parent=path).execute().get("variable", [])
    lines = ["=== Variables ==="]
    if not variables:
        lines.append("No variables found.")
    else:
        for v in variables:
            vid = v.get("variableId", "")
            name = v.get("name", "")
            vtype = v.get("type", "")
            lines.append(f"  [{vid}] {name} | type: {vtype}")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def _get_container_version(gtm, account_id, container_id, version_id):
    if not version_id:
        return {"content": [{"type": "text", "text": "version_id is required"}]}
    path = f"accounts/{account_id}/containers/{container_id}/versions/{version_id}"
    try:
        v = gtm.accounts().containers().versions().get(path=path).execute()
        lines = ["=== Container Version " + version_id + " ==="]
        lines.append(f"Name:    {v.get('name', 'N/A')}")
        lines.append(f"Status:  {v.get('status', 'N/A')}")
        lines.append(f"Created: {v.get('created', 'N/A')}")
        lines.append(f"Modified: {v.get('modified', 'N/A')}")
        lines.append(f"Num tags: {len(v.get('container', {}).get('tag', []))}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}
    except Exception as e:
        err = "Version not found or not accessible: " + str(e)
        return {"content": [{"type": "text", "text": err}]}