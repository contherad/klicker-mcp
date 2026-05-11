# Klicker MCP Server

Unified MCP server connecting Claude Desktop to **Google Analytics 4**, **Google Ads**, **Google Tag Manager**, and **Ahrefs** — ask Claude anything about your marketing data.

> Instead of opening four dashboards:
> "What's my organic traffic for the last 90 days?"
> "Which Google Ads campaigns have the best ROAS this month?"
> "What tracking scripts are deployed on my site?"
> "What keywords does klickerinc.com rank for?"

---

## What's in the box

| Integration | Tools |
|---|---|
| **Google Analytics 4** | Account/property listing, custom reports, realtime reports, custom dimensions |
| **Google Ads** | Campaigns, campaign performance, keyword performance, ad groups, account summary |
| **Google Tag Manager** | Accounts, containers, tags, triggers, variables, container versions |
| **Ahrefs** | Domain rating, backlinks, organic keywords, linking domains, anchor text, domain comparison |

Every tool supports both human-readable text output and structured JSON (`format: "json"`).

---

## Quick start (Windows)

### 1. Install

```cmd
cd %USERPROFILE%\Documents\git
git clone https://github.com/contherad/klicker-mcp
cd klicker-mcp
pip install -e .
```

If you don't have Git, [download a ZIP](https://github.com/contherad/klicker-mcp) instead.

> Requires Python 3.10+.

### 2. Set up credentials

Each integration needs its own credentials file in `credentials/`. The CLI walks you through each one:

```cmd
marketing-mcp init google-analytics
marketing-mcp init google-ads
marketing-mcp init google-tag-manager
marketing-mcp init ahrefs
```

Full setup guides are in [`docs/`](docs/):

- [`GOOGLE-ANALYTICS-SETUP.md`](docs/GOOGLE-ANALYTICS-SETUP.md)
- [`GOOGLE-ADS-SETUP.md`](docs/GOOGLE-ADS-SETUP.md)
- [`GOOGLE-TAG-MANAGER-SETUP.md`](docs/GOOGLE-TAG-MANAGER-SETUP.md)
- [`AHREFS-SETUP.md`](docs/AHREFS-SETUP.md)

### 3. Verify the credentials are good

```cmd
marketing-mcp doctor
```

Output is per-integration PASS/FAIL. Exits 0 only when everything is configured.

### 4. Wire up Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` and add (adjust the paths to match your install):

```json
{
  "mcpServers": {
    "marketing-mcp": {
      "command": "C:\\Python313\\python.exe",
      "args": ["-m", "marketing_mcp.cli"],
      "cwd": "C:\\Users\\YourName\\Documents\\git\\klicker-mcp",
      "env": {
        "PYTHONPATH": "C:\\Users\\YourName\\Documents\\git\\klicker-mcp\\src"
      }
    }
  }
}
```

> If you installed via `pip install -e .` you can use `"command": "marketing-mcp"` with `"args": []` instead.

### 5. Restart Claude Desktop

Fully quit (system tray → Quit, not just close the window) and reopen. Ask:

> "What's my Google Analytics traffic for the last 30 days?"

---

## CLI reference

```
marketing-mcp serve                      # start MCP server over stdio (default)
marketing-mcp doctor                     # validate credentials
marketing-mcp init [integration]         # interactive setup
marketing-mcp version                    # print version
marketing-mcp --log-level DEBUG serve    # increase verbosity
```

Environment variables:

| Var | Purpose |
|---|---|
| `MARKETING_MCP_LOG_LEVEL` | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |
| `MARKETING_MCP_LOG_DIR` | Override log directory |
| `MARKETING_MCP_CREDENTIALS_DIR` | Override credentials directory |

---

## Production features

This server is built for real use, not just demos.

- **Hot-reload credentials** — drop a new key file in `credentials/`, no restart needed
- **TTL caching** — Ahrefs (1 hr), Google Ads (5 min), GA metadata (10 min). Per-integration tunable.
- **Retry with exponential backoff** on transient failures (5xx, 408, 429, network blips); 4xx errors fail fast
- **Rotating file logs** — `logs/marketing-mcp.log`, 5 MB × 3 files
- **Input validation** — customer IDs, dates, etc. validated before hitting the API
- **`marketing-mcp doctor`** — actionable startup health check

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/OPERATIONS.md`](docs/OPERATIONS.md) for the deep dive.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Tools don't appear in Claude | Fully quit Claude Desktop and reopen. Check `%APPDATA%\Claude\logs\mcp-server-marketing-mcp.log` |
| "Credentials not found" but file is there | Run `marketing-mcp doctor` — it pinpoints the issue |
| GTM "Not found or permission denied" | Service account not granted on the GTM account. See workaround in [`GOOGLE-TAG-MANAGER-SETUP.md`](docs/GOOGLE-TAG-MANAGER-SETUP.md) |
| GA UI rejects service account email | Use the API Explorer workaround in [`GOOGLE-ANALYTICS-SETUP.md`](docs/GOOGLE-ANALYTICS-SETUP.md) |
| Ahrefs 401 | API key is invalid; regenerate at https://app.ahrefs.com/api/dashboard |

Full operations runbook: [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). TL;DR:

```bash
git clone https://github.com/contherad/klicker-mcp
cd klicker-mcp
pip install -e ".[dev]"
pytest
ruff check src tests
```

---

## License

MIT.
