# Operations Runbook

Practical guide to running, monitoring, and debugging the Klicker MCP server in production (i.e. on Kade's laptop).

## Where things live

| File | Purpose |
|---|---|
| `credentials/` | All API keys, OAuth tokens, service account JSONs. Never commit. |
| `logs/marketing-mcp.log` | Rotating server log (5 MB × 3 files). |
| `%APPDATA%\Claude\claude_desktop_config.json` | Claude Desktop's MCP server registry (Windows). |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Same, on macOS. |
| `%APPDATA%\Claude\logs\mcp-server-marketing-mcp.log` | Claude Desktop's own log of what the MCP server emitted. |

## Common tasks

### Verify the install

```
marketing-mcp doctor
```

Output is per-integration PASS/FAIL with the credential file path. Exits non-zero if anything is missing.

### Test a tool without going through Claude

```
marketing-mcp serve
```

This will start the server in foreground over stdio. Useful for confirming it boots; press Ctrl+C to stop. Tools themselves are only callable from an MCP client (Claude Desktop, or an MCP test harness).

### Restart after credential changes

Service account JSONs and the Ahrefs key are hot-reloaded on file-mtime change — usually no restart needed. For environment variable changes (`MARKETING_MCP_*`), restart Claude Desktop fully:

1. Right-click Claude tray icon → Quit
2. Reopen Claude Desktop

### Override log level

```
MARKETING_MCP_LOG_LEVEL=DEBUG marketing-mcp serve
```

Or set it in the Claude Desktop config's `env` block:

```json
{
  "mcpServers": {
    "marketing-mcp": {
      "command": "...",
      "args": ["..."],
      "env": {
        "MARKETING_MCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Override credentials directory

```
MARKETING_MCP_CREDENTIALS_DIR=/opt/secrets/klicker marketing-mcp serve
```

Useful for clients with security policies that require credentials outside the project directory.

## Troubleshooting

### Tools don't appear in Claude

1. Fully quit Claude Desktop and reopen (system tray → Quit). Just closing the window keeps it running.
2. Check `%APPDATA%\Claude\logs\mcp-server-marketing-mcp.log` for startup errors.
3. Run `marketing-mcp serve` in a terminal — if it crashes here, the same error is breaking Claude's child process.
4. Verify the `command` and `env.PYTHONPATH` in `claude_desktop_config.json` are absolute paths and use double-backslashes on Windows.

### "Credentials not found" but the file exists

1. Run `marketing-mcp doctor` — the report will tell you exactly where it's looking and what's wrong with the file.
2. Check that the file is the *right kind* of JSON. Service account JSON is ~2 KB; OAuth client-secret JSON is ~400 bytes. Easy mix-up.

### Ahrefs returns 401

The API key is invalid or expired. Regenerate at https://app.ahrefs.com/api/dashboard.

### Google Ads returns "unauthenticated"

The refresh token expired. Re-run:

```
python scripts/setup_google_ads.py
```

### GTM returns "Not found or permission denied"

The service account isn't granted on the GTM account/container yet, OR the Tag Manager API isn't enabled on the GCP project. See `docs/GOOGLE-TAG-MANAGER-SETUP.md` — the GTM UI rejects service account emails so you'll likely need the API Explorer workaround documented there.

### High Ahrefs credit burn

Check the cache TTL in `src/marketing_mcp/utils/cache.py` — `AHREFS_CACHE.ttl` defaults to 1 hour. If users are running the same query repeatedly, increase it.

## Backup & rotation

- Logs rotate automatically (5 MB × 3 files in `logs/`). No manual cleanup needed.
- Credentials should be backed up to a password manager. **Never** push them to git — `.gitignore` blocks the whole `credentials/` directory.
- Service account keys should be rotated annually. Create a new key in GCP, drop it into `credentials/`, delete the old key from GCP after verifying.

## Monitoring

For a single-user deployment, monitoring is "Kade tells you it broke." For multi-user:

- Tail `logs/marketing-mcp.log` for `ERROR`-level events.
- Build a Cron / Windows Task Scheduler job that runs `marketing-mcp doctor` daily and emails on non-zero exit.
- Hook `logs/marketing-mcp.log` into your existing logging stack (Datadog, Splunk, etc.) via Filebeat or similar.

## Upgrading

```
cd klicker-mcp
git pull
pip install -e ".[dev]"
marketing-mcp doctor      # verify credentials still work
```

Then restart Claude Desktop fully.

## Uninstall

1. Remove the `marketing-mcp` entry from `claude_desktop_config.json`.
2. Optionally `pip uninstall marketing-mcp`.
3. Delete the project directory.
4. Revoke the service account key(s) in Google Cloud Console.
5. Revoke the Ahrefs API key in the Ahrefs dashboard.
