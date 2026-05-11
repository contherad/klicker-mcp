"""Logging setup — console + rotating file handler.

The MCP server runs over stdio. Anything written to stdout corrupts the protocol,
so all logging goes to stderr and (optionally) to a rotating file in `logs/`.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

_CONFIGURED = False


def configure_logging(
    level: str | int = "INFO",
    log_dir: Path | None = None,
    log_to_file: bool = True,
) -> logging.Logger:
    """Configure root logger once. Idempotent.

    The level can be overridden via the ``MARKETING_MCP_LOG_LEVEL`` env var.
    Log directory can be overridden via ``MARKETING_MCP_LOG_DIR``.
    """
    global _CONFIGURED
    root = logging.getLogger()

    if _CONFIGURED:
        return logging.getLogger("marketing_mcp")

    # Resolve level (env wins over arg)
    env_level = os.environ.get("MARKETING_MCP_LOG_LEVEL")
    if env_level:
        level = env_level.upper()
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(level)

    # Clear any prior handlers (e.g. from basicConfig calls)
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Stderr handler (stdio MCP protocol owns stdout — never log there)
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)

    # Rotating file handler
    if log_to_file:
        env_dir = os.environ.get("MARKETING_MCP_LOG_DIR")
        target_dir = Path(env_dir) if env_dir else (log_dir or DEFAULT_LOG_DIR)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                target_dir / "marketing-mcp.log",
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as e:
            # If we can't write to the log dir (e.g. read-only install), keep going
            root.warning("Could not open log file in %s: %s", target_dir, e)

    # Silence noisy third-party loggers
    for noisy in ("googleapiclient.discovery_cache", "google.auth.transport.requests", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
    return logging.getLogger("marketing_mcp")


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger under the ``marketing_mcp`` namespace."""
    if not name.startswith("marketing_mcp"):
        name = f"marketing_mcp.{name}"
    return logging.getLogger(name)
