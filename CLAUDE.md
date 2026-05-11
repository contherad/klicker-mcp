# Klicker MCP Server

Unified MCP server connecting Claude Desktop to Google Analytics, Google Ads, Google Tag Manager, and Ahrefs.

## Project Structure

```
klicker-mcp/
├── src/marketing_mcp/
│   ├── server.py          # MCP server entry point (stdio)
│   ├── coordinator.py     # Routes tool calls to handlers
│   ├── tools/
│   │   ├── analytics.py   # GA4 tools (google-analytics-data)
│   │   ├── ads.py         # Google Ads tools (google-ads)
│   │   ├── tagmanager.py  # GTM tools (google-api-python-client)
│   │   └── ahrefs.py      # Ahrefs tools (requests + Ahrefs API v5)
│   └── utils/
│       └── config.py      # Loads credentials from credentials/ directory
├── credentials/           # API keys and OAuth tokens (gitignored)
│   ├── google-analytics-credentials.json
│   ├── google-ads-credentials.json
│   ├── google-tag-manager-credentials.json
│   └── ahrefs-api-key.txt
├── scripts/               # Interactive credential setup scripts
│   ├── setup_google_ads.py
│   ├── setup_gtm.py
│   └── setup_ahrefs.py
├── docs/                  # Step-by-step setup guides
│   ├── GOOGLE-ANALYTICS-SETUP.md
│   ├── GOOGLE-ADS-SETUP.md
│   ├── GOOGLE-TAG-MANAGER-SETUP.md
│   └── AHREFS-SETUP.md
└── README.md              # End-user onboarding
```

## Running

```bash
cd klicker-mcp
pip install -r requirements.txt
python -m marketing_mcp.server
```

## Credentials

Credentials are loaded from the `credentials/` directory. See `docs/*.md` for setup instructions.

## Adding New Tools

1. Add tool definition to the appropriate `tools/*.py` (follow the `get_*_tools()` pattern)
2. Add handler to `tools/__init__.py` in the `get_all_handlers()` dict
3. Update `docs/` with setup instructions for any new credentials

## Design Notes

- Single unified project (not modular per-integration) — per Kade's request
- All tools return `{"content": [{"type": "text", "..."}]}` (MCP TextContent format)
- Config is a singleton loaded once at startup
- GA4 uses `google-analytics-data` library with service account credentials
- Google Ads uses `google-ads` library with OAuth2 refresh token flow
- GTM uses `google-api-python-client` with OAuth2 refresh token
- Ahrefs uses raw `requests` against Ahrefs API v5