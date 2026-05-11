# Credentials directory

This directory holds API keys, OAuth tokens, and service-account JSON files.

**Files in here are gitignored.** Anything that *isn't* an `.example` file or this README is excluded from version control.

## Expected files

| File | Format | Setup guide |
|---|---|---|
| `google-analytics-credentials.json` | Google service account JSON (~2 KB) | [`docs/GOOGLE-ANALYTICS-SETUP.md`](../docs/GOOGLE-ANALYTICS-SETUP.md) |
| `google-ads-credentials.json` | Custom JSON (developer_token, client_id, client_secret, refresh_token) | [`docs/GOOGLE-ADS-SETUP.md`](../docs/GOOGLE-ADS-SETUP.md) |
| `google-tag-manager-credentials.json` | Google service account JSON (~2 KB) — can reuse the GA one | [`docs/GOOGLE-TAG-MANAGER-SETUP.md`](../docs/GOOGLE-TAG-MANAGER-SETUP.md) |
| `ahrefs-api-key.txt` | Single-line plaintext API key | [`docs/AHREFS-SETUP.md`](../docs/AHREFS-SETUP.md) |

## Verify

```
marketing-mcp doctor
```

This validates each credential's *shape* (without sending API requests) and prints PASS/FAIL with the next step to take.

## Override directory

If you'd rather keep credentials elsewhere:

```
MARKETING_MCP_CREDENTIALS_DIR=/path/to/secrets marketing-mcp serve
```
