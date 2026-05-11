# Contributing

Thanks for considering a contribution. This guide covers local setup, the test/lint workflow, and our conventions.

## Local setup

```bash
git clone https://github.com/contherad/klicker-mcp
cd klicker-mcp
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The `[dev]` extra pulls in `pytest`, `ruff`, `mypy`, and friends.

## Daily commands

```bash
pytest                              # run tests
pytest -m "not live"                # skip live-API tests (default in CI)
pytest --cov=marketing_mcp          # with coverage
ruff check src tests                # lint
ruff format src tests               # auto-format
mypy src/marketing_mcp              # type-check (advisory)
marketing-mcp doctor                # validate your credentials
marketing-mcp serve                 # run the MCP server over stdio
```

## Conventions

- **Type hints** everywhere on new code. `from __future__ import annotations` at the top of new modules.
- **Async handlers** for new tools so concurrent calls don't block. They can call sync libraries inside — we don't run a real event loop fan-out yet.
- **Logging**: use `from marketing_mcp.utils.logging import get_logger`. Never `print()`.
- **HTTP calls**: wrap with `@with_retry(...)`. Surface 4xx errors verbatim; let the decorator handle 5xx/408/429/network.
- **Cache** expensive read-only calls with the per-integration `ScopedCache` instance (`ANALYTICS_METADATA_CACHE`, `AHREFS_CACHE`, ...).
- **Input validation**: validate arguments inside the handler. Tool input schemas are advisory; the MCP client doesn't enforce types.
- **Output format**: every tool should support `format: "text"` (default) and `format: "json"`.
- **Tests** for new behavior. Mock HTTP with `responses` for `requests`, or `pytest-mock` for the Google client libraries.

## Adding a tool

See `docs/ARCHITECTURE.md` → "Adding a new tool".

## Pull requests

1. Branch off `main`. Keep PRs focused (one feature / one fix).
2. Run the daily commands above before pushing.
3. Update `CHANGELOG.md` under `## [Unreleased]` (create the section if it doesn't exist).
4. Open the PR. CI runs lint + tests on push.

## Releases

Releases are tag-driven. Once a release is ready:

1. Update version in `pyproject.toml` and `src/marketing_mcp/__init__.py`.
2. Promote the `[Unreleased]` section in `CHANGELOG.md` to a dated version section.
3. Commit, tag (`git tag v1.x.y`), push (`git push --tags`).
4. The `Release` workflow builds and publishes to PyPI via trusted publishing.

## Reporting bugs

Open an issue with:

- The tool you called and the arguments
- The error message (from Claude or from `logs/marketing-mcp.log`)
- Output of `marketing-mcp doctor`
- Python version (`python --version`) and OS

Do **not** paste API keys or service account JSONs in issues. Run `marketing-mcp doctor` — it only shows file paths and service account *emails*, no secrets.
