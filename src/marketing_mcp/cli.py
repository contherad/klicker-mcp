"""CLI entry point: ``marketing-mcp <subcommand>``.

Subcommands:
  serve   Start the MCP server over stdio (default — used by Claude Desktop).
  doctor  Validate credentials and report PASS/FAIL per integration.
  init    Interactive wizard to set up credentials.
  version Print version.
"""

from __future__ import annotations

import asyncio
import sys

import click

from marketing_mcp import __version__
from marketing_mcp.utils.config import HealthReport, run_health_check
from marketing_mcp.utils.logging import configure_logging

OK = "[OK]"
FAIL = "[FAIL]"


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--log-level",
    default=None,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Override log level (env: MARKETING_MCP_LOG_LEVEL).",
)
@click.version_option(__version__, prog_name="marketing-mcp")
@click.pass_context
def cli(ctx: click.Context, log_level: str | None) -> None:
    """Klicker MCP — Google Analytics, Ads, Tag Manager, and Ahrefs for Claude."""
    configure_logging(level=log_level or "INFO")
    if ctx.invoked_subcommand is None:
        # `marketing-mcp` with no args -> serve (preserves Claude Desktop config)
        ctx.invoke(serve)


@cli.command()
def serve() -> None:
    """Start the MCP server (stdio). This is what Claude Desktop calls."""
    from marketing_mcp.server import run

    asyncio.run(run())


@cli.command()
@click.option(
    "--credentials-dir",
    type=click.Path(),
    default=None,
    help="Override credentials directory (env: MARKETING_MCP_CREDENTIALS_DIR).",
)
def doctor(credentials_dir: str | None) -> None:
    """Validate credentials and exit 0 if all integrations are configured."""
    from pathlib import Path

    creds_dir = Path(credentials_dir).expanduser().resolve() if credentials_dir else None
    report = run_health_check(creds_dir)
    _print_report(report)
    sys.exit(0 if report.all_ok else 1)


@cli.command(name="init")
@click.argument(
    "integration",
    required=False,
    type=click.Choice(
        ["google-analytics", "google-ads", "google-tag-manager", "ahrefs", "all"],
        case_sensitive=False,
    ),
)
def init_cmd(integration: str | None) -> None:
    """Interactive setup wizard for credentials."""
    if not integration or integration == "all":
        click.echo("Setup all integrations one by one.\n")
        for name in ("google-analytics", "google-ads", "google-tag-manager", "ahrefs"):
            click.echo(click.style(f"\n--- {name} ---", fg="cyan"))
            _init_one(name)
    else:
        _init_one(integration.lower())


@cli.command()
def version() -> None:
    """Print version."""
    click.echo(f"marketing-mcp {__version__}")


# ---------- helpers ----------


def _print_report(report: HealthReport) -> None:
    click.echo(f"Credentials dir: {report.credentials_dir}\n")
    for check in report.checks:
        tag = click.style(OK, fg="green") if check.ok else click.style(FAIL, fg="red")
        click.echo(f"{tag} {check.name}: {check.message}")
        for line in check.details:
            click.echo(f"      {line}")
    click.echo()
    if report.all_ok:
        click.echo(click.style("All integrations configured.", fg="green"))
    elif report.any_ok:
        click.echo(click.style("Some integrations are not configured (see above).", fg="yellow"))
    else:
        click.echo(click.style("No integrations are configured.", fg="red"))


def _init_one(integration: str) -> None:
    """Print setup instructions for a single integration.

    We intentionally don't automate downloading credentials from Google — the user
    must do that part themselves through the OAuth/service account flow. This
    command's job is to walk them through it.
    """
    if integration == "google-analytics":
        click.echo(
            "Google Analytics service account setup:\n"
            "  1. Go to https://console.cloud.google.com/ → Create a project\n"
            "  2. Enable: Google Analytics Admin API + Google Analytics Data API\n"
            "  3. Credentials → Create credentials → Service Account\n"
            "  4. Open the service account → Keys → Add key → JSON\n"
            "  5. Save the downloaded JSON as: credentials/google-analytics-credentials.json\n"
            "  6. In GA4 → Admin → Property Access Management, grant the service\n"
            "     account email 'Viewer' role on your property.\n"
            "     (If the UI rejects service account emails, see docs/GOOGLE-ANALYTICS-SETUP.md)\n"
            "\nFull guide: docs/GOOGLE-ANALYTICS-SETUP.md"
        )
    elif integration == "google-ads":
        click.echo(
            "Google Ads OAuth setup:\n"
            "  1. Get a developer token from ads.google.com → Tools → API Center\n"
            "  2. In Google Cloud, enable Google Ads API\n"
            "  3. Create OAuth2 Desktop credentials (Client ID + Secret)\n"
            "  4. Run: python scripts/setup_google_ads.py\n"
            "     (Walks you through the refresh-token flow.)\n"
            "  5. The script writes credentials/google-ads-credentials.json.\n"
            "\nFull guide: docs/GOOGLE-ADS-SETUP.md"
        )
    elif integration == "google-tag-manager":
        click.echo(
            "Google Tag Manager service account setup:\n"
            "  1. (Re-use your GA service account if you have one.)\n"
            "  2. In Google Cloud, enable Tag Manager API\n"
            "  3. Save the service account JSON as:\n"
            "     credentials/google-tag-manager-credentials.json\n"
            "  4. In GTM → Admin → User Management, grant the service account 'Read'.\n"
            "     If the UI rejects service account emails, use the API Explorer\n"
            "     (see docs/GOOGLE-TAG-MANAGER-SETUP.md).\n"
            "\nFull guide: docs/GOOGLE-TAG-MANAGER-SETUP.md"
        )
    elif integration == "ahrefs":
        click.echo(
            "Ahrefs API setup:\n"
            "  1. ahrefs.com → Dashboard → API → generate an API key\n"
            "  2. Save the key (single line, no quotes) to:\n"
            "     credentials/ahrefs-api-key.txt\n"
            "\nFull guide: docs/AHREFS-SETUP.md"
        )
    else:
        click.echo(f"Unknown integration: {integration}", err=True)


def main() -> None:
    """Sync entry point referenced by ``[project.scripts]`` in pyproject.toml."""
    cli(prog_name="marketing-mcp")


if __name__ == "__main__":
    main()
