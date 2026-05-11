# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] — 2026-05-11

### Added
- **CLI**: `marketing-mcp` console script with subcommands `serve`, `doctor`, `init`, `version`.
- **Health-check (`doctor`)**: validates every credentials file at startup or on demand and reports PASS/FAIL with actionable next steps per integration.
- **Structured logging** to `logs/marketing-mcp.log` with rotation (5 MB × 3 files). Configurable via `MARKETING_MCP_LOG_LEVEL` and `MARKETING_MCP_LOG_DIR`.
- **Retry with exponential backoff** for transient API errors (network, 5xx, 408, 429) via `tenacity`.
- **TTL response caching** for Ahrefs (1 hr — paid credits), Google Ads (5 min), GA Admin (10 min), and GTM (10 min) via `cachetools`.
- **Config hot-reload** — `get_cached_config()` re-reads credential files when any mtime changes.
- **JSON output mode** on every tool — pass `format: "json"` for structured output suitable for piping.
- **`gtm_list_accounts` tool** — discover accessible GTM accounts when you don't know your account ID.
- **Test suite** — 37 pytest tests covering config loading, caching, retries, registry, CLI, and Ahrefs HTTP layer (mocked).
- **CI workflows** — lint (`ruff`), type-check (`mypy`), test matrix (Python 3.10–3.13 on Linux/macOS/Windows), build & PyPI publish.
- **Dev tooling** — `ruff`, `mypy`, `pytest`, `pytest-cov`, `responses`, `pytest-mock` configured in `pyproject.toml`.
- **Documentation** — `ARCHITECTURE.md`, `CONTRIBUTING.md`, `OPERATIONS.md`. Updated GA & GTM setup docs with the service-account-via-API-Explorer workaround for the GA4/GTM UI bug.

### Changed
- **Renamed entry point** from `marketing_mcp.server:main` to `marketing_mcp.cli:main`. `python -m marketing_mcp.server` still works.
- **Strengthened input validation** on `customer_id`, `campaign_id`, and date params for Google Ads tools.
- **Hardened `.gitignore`** — credentials directory is now allow-listed (deny everything except `.gitkeep`, `README.md`, and `*.example` files).
- **Replaced explicit handler registry** with a prefix-based router (`ga_*`, `ads_*`, `gtm_*`, `ahrefs_*`).
- **GTM workspace lookup** correctly handles the `"default"` sentinel.
- **GTM container listing** correctly formats the `domainName` list field.

### Fixed
- **Critical**: stdio MCP bootstrap (`stdio_server(...).run_as_task()` was a non-existent API call that prevented the server from ever starting).
- **Critical**: `CREDENTIALS_DIR` resolved to `src/credentials/` instead of `<project-root>/credentials/`.
- `_get_access_token` in analytics now passes `scopes` correctly to `from_service_account_info`.
- Google Ads `_run_query` now flattens `search_stream` batches into rows (previously treated batches as rows).
- Google Ads queries no longer reference invalid `campaign.total_amount_micros` / `campaign.budget.amount_micros` — use `campaign_budget.amount_micros` instead.
- Google Ads `_run_query` no longer silently swallows exceptions.
- Realtime GA reports use `RunRealtimeReportRequest` + `client.run_realtime_report` (previously used the standard report API).
- GA Admin REST endpoints use `/v1beta/` (previously `/v1/` — undefined for `properties` / `customDimensions` / `customMetrics`).
- Config loader no longer silently picks `google-ads-credentials.json` as the GA credentials fallback.
- Ahrefs API integration now uses Bearer-token auth on `/site-explorer/...` endpoints (previously query-param auth on non-existent endpoints).
- Ahrefs response formatter now correctly unwraps rows from the v3 envelope (`data`, named keys).
- 4xx responses (other than 408/429) no longer trigger retries — auth failures fail fast.
- HTTP error formatter no longer drops the status code due to `requests.Response.__bool__` returning False for 4xx.
- `MCP server.py` returns all content items (previously truncated to the first).
- Server no longer creates `credentials/.gitkeep` on every startup.

### Removed
- Unused `ClientOptions` import in `tools/analytics.py`.
- Spurious `" occurrences"` (leading-space typo) key lookup in Ahrefs anchor formatter.

## [1.0.0] — 2026-05-11

Initial release.
