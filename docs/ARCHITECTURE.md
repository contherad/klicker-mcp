# Architecture

A short tour of how the code is organised, what each layer does, and where to add things.

```
src/marketing_mcp/
├── __init__.py              # version
├── cli.py                   # marketing-mcp CLI entry point (serve, doctor, init)
├── server.py                # MCP stdio server (called by Claude Desktop)
├── coordinator.py           # Singleton-ish glue: get_config / run_tool dispatch
├── tools/
│   ├── __init__.py          # aggregates tools across all integrations
│   ├── analytics.py         # Google Analytics 4 tool defs + handlers + formatters
│   ├── ads.py               # Google Ads
│   ├── tagmanager.py        # Google Tag Manager
│   └── ahrefs.py            # Ahrefs
└── utils/
    ├── config.py            # credential discovery, validation, hot-reload
    ├── logging.py           # stderr + rotating file handlers
    ├── retry.py             # tenacity-based with_retry() decorator
    └── cache.py             # ScopedCache (TTL-based) for API responses
```

## Layers

### Transport (`server.py`)

Implements the MCP protocol over stdio. Two responsibilities only:

1. Advertise the tool catalog (`list_tools`) — reads from `coordinator.get_tools_metadata()`.
2. Dispatch tool calls (`call_tool`) — passes through `coordinator.run_tool()`.

Logging is configured here on startup. The server itself contains no business logic.

### Dispatch (`coordinator.py`)

Thin glue between the MCP server and the tool implementations. Holds the hot-reloading config singleton and provides the dispatcher used by `call_tool`.

### Tools (`tools/<integration>.py`)

Each integration file is self-contained and exports two public functions:

- `get_<integration>_tools() -> list[dict]` — tool definitions (name, description, JSON Schema).
- `handle_<integration>_tool(tool_name, arguments, config) -> dict` — async handler. Returns the MCP content envelope `{"content": [{"type": "text", "text": ...}]}`.

Internally each file is laid out as:

1. Tool definitions (schemas)
2. Top-level `handle_*` dispatcher
3. Per-tool helper functions
4. Format helpers (text and JSON)

The registry (`tools/__init__.py`) routes tool names to handlers by prefix: `ga_*`, `ads_*`, `gtm_*`, `ahrefs_*`.

### Utilities (`utils/`)

| Module | Responsibility |
|---|---|
| `config.py` | Resolve credentials, validate shape, hot-reload on file change. |
| `logging.py` | Console + rotating-file logger. Never logs to stdout (would corrupt MCP stdio). |
| `retry.py` | `@with_retry(...)` decorator for HTTP calls. Skips 4xx (other than 408/429). |
| `cache.py` | `ScopedCache` — TTL-based, thread-safe wrapper around `cachetools.TTLCache`. Pre-configured caches per integration. |

## Adding a new tool

1. Pick the right integration file (or create one in `tools/`).
2. Append a definition to `get_<integration>_tools()`:
   ```python
   {
     "name": "myint_do_thing",
     "description": "...",
     "inputSchema": {"type": "object", "properties": {...}, "required": [...]},
   }
   ```
3. Add a branch in `handle_<integration>_tool()` for the new tool name.
4. Implement the helper. Use `@with_retry()` on the HTTP layer and `_cached_*` wrappers for expensive calls.
5. Add a `format: "json"` branch in addition to the text formatter.
6. Update the registry only if you added a new integration prefix.
7. Add tests under `tests/test_<integration>.py` — mock HTTP with the `responses` library.

## Adding a new integration

1. Create `src/marketing_mcp/tools/<integration>.py` following the layout above.
2. Add a per-integration cache to `utils/cache.py` if useful.
3. Add credential loading + validation to `utils/config.py`:
   - Add a Pydantic model class.
   - Add a `_load_<integration>(credentials_dir) -> (Config, CheckResult)` function.
   - Register it in `load_config()` and `run_health_check()`.
4. Add an `_init_one()` branch in `cli.py` describing the setup steps.
5. Update `tools/__init__.py` to include the new tools and prefix.
6. Write tests and docs (`docs/<INTEGRATION>-SETUP.md`).

## MCP content protocol notes

- Tool handlers return `{"content": [{"type": "text", "text": "..."}]}`. The list can hold multiple content items; the server preserves them all.
- **Never write to stdout** outside the MCP framing — it will corrupt the protocol stream. All logging is forced to stderr in `utils/logging.py`.
- Errors in handlers should be caught and returned as text content, not raised — uncaught exceptions get logged but return a generic error string to the client.

## Caching guidance

| Cache | TTL | Why |
|---|---|---|
| `ANALYTICS_METADATA_CACHE` | 10 min | Account / property / custom-dimension lists change rarely. |
| `GTM_METADATA_CACHE` | 10 min | Container/workspace listing is stable. |
| `ADS_QUERY_CACHE` | 5 min | Reporting data updates often; short TTL keeps it responsive. |
| `AHREFS_CACHE` | 1 hr | Ahrefs charges per credit — cache aggressively. |

Tune TTLs in `utils/cache.py`. Cache keys are stable hashes of `(endpoint, params)`.

## Retry guidance

Wrap the lowest-level HTTP call (not the entire handler). The decorator does not retry 4xx errors except for 408 (timeout) and 429 (rate limit) — those are transient. Everything 4xx else means "the request is wrong"; retrying just burns time and quota.
