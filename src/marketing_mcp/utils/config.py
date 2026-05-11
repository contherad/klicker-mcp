"""Configuration loader.

Reads credentials from a directory (``credentials/`` by default) and validates
the shape of each file. Supports hot-reload: ``get_cached_config()`` re-loads
when any credential file's mtime changes.

Credential file conventions
---------------------------
- ``google-analytics-credentials.json`` — Google service account JSON
- ``google-ads-credentials.json`` — JSON with developer_token, client_id,
  client_secret, refresh_token, (optional) login_customer_id
- ``google-tag-manager-credentials.json`` — Google service account JSON
- ``ahrefs-api-key.txt`` — single-line Ahrefs API key
"""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from marketing_mcp.utils.logging import get_logger

logger = get_logger("config")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_CREDENTIALS_DIR = PROJECT_ROOT / "credentials"


def _resolve_credentials_dir() -> Path:
    env = os.environ.get("MARKETING_MCP_CREDENTIALS_DIR")
    return Path(env).expanduser().resolve() if env else DEFAULT_CREDENTIALS_DIR


# ---------- Pydantic config models ----------


class GoogleAnalyticsConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    credentials_path: Path | None = None
    project_id: str | None = None
    client_email: str | None = None


class GoogleAdsConfig(BaseModel):
    developer_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    account_id: str | None = None
    login_customer_id: str | None = None


class GoogleTagManagerConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    credentials_path: Path | None = None
    account_id: str | None = None
    container_id: str | None = None
    client_email: str | None = None


class AhrefsConfig(BaseModel):
    api_key: str | None = None


class Config(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    google_analytics: GoogleAnalyticsConfig = GoogleAnalyticsConfig()
    google_ads: GoogleAdsConfig = GoogleAdsConfig()
    google_tag_manager: GoogleTagManagerConfig = GoogleTagManagerConfig()
    ahrefs: AhrefsConfig = AhrefsConfig()
    credentials_dir: Path = DEFAULT_CREDENTIALS_DIR


# ---------- Validation report ----------


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    details: list[str] = field(default_factory=list)


@dataclass
class HealthReport:
    credentials_dir: Path
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def any_ok(self) -> bool:
        return any(c.ok for c in self.checks)


# ---------- File helpers ----------


def _find_first(credentials_dir: Path, *patterns: str) -> Path | None:
    for pattern in patterns:
        matches = sorted(credentials_dir.glob(pattern))
        for match in matches:
            # Skip .example files even if they match the *.json glob
            if match.name.endswith(".example") or match.name.endswith(".example.json"):
                continue
            return match
    return None


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


_SERVICE_ACCOUNT_REQUIRED = {"type", "client_email", "private_key", "token_uri"}


def _is_service_account(data: dict) -> bool:
    return data.get("type") == "service_account" and _SERVICE_ACCOUNT_REQUIRED.issubset(data)


# ---------- Loaders per integration ----------


def _load_analytics(credentials_dir: Path) -> tuple[GoogleAnalyticsConfig, CheckResult]:
    cfg = GoogleAnalyticsConfig()
    path = _find_first(
        credentials_dir,
        "google-analytics-credentials.json",
        "google-analytics-*.json",
        "ga-*.json",
        "analytics-*.json",
    )
    if not path:
        return cfg, CheckResult(
            "Google Analytics",
            False,
            "No credentials file found",
            [
                f"Expected at: {credentials_dir / 'google-analytics-credentials.json'}",
                "See docs/GOOGLE-ANALYTICS-SETUP.md",
            ],
        )

    try:
        data = _read_json(path)
    except json.JSONDecodeError as e:
        return cfg, CheckResult("Google Analytics", False, f"Invalid JSON in {path.name}: {e}")

    if not _is_service_account(data):
        return cfg, CheckResult(
            "Google Analytics",
            False,
            f"{path.name} is not a service account JSON",
            [
                "Expected fields: type=service_account, client_email, private_key, token_uri",
                "Re-download from Google Cloud Console: Service Account → Keys → Add Key → JSON",
            ],
        )

    cfg.credentials_path = path
    cfg.project_id = data.get("project_id") or os.environ.get("GOOGLE_PROJECT_ID")
    cfg.client_email = data.get("client_email")
    return cfg, CheckResult(
        "Google Analytics",
        True,
        f"OK ({path.name}) — service account: {cfg.client_email}",
    )


def _load_ads(credentials_dir: Path) -> tuple[GoogleAdsConfig, CheckResult]:
    cfg = GoogleAdsConfig()
    path = _find_first(
        credentials_dir,
        "google-ads-credentials.json",
        "google-ads*.json",
        "ads*.json",
    )
    if not path:
        return cfg, CheckResult(
            "Google Ads",
            False,
            "No credentials file found",
            [
                f"Expected at: {credentials_dir / 'google-ads-credentials.json'}",
                "Run: marketing-mcp init google-ads",
            ],
        )

    try:
        data = _read_json(path)
    except json.JSONDecodeError as e:
        return cfg, CheckResult("Google Ads", False, f"Invalid JSON in {path.name}: {e}")

    required = ["developer_token", "client_id", "client_secret", "refresh_token"]
    missing = [k for k in required if not data.get(k)]
    if missing:
        return cfg, CheckResult(
            "Google Ads",
            False,
            f"{path.name} missing required fields: {', '.join(missing)}",
            [
                "Expected fields: developer_token, client_id, client_secret, refresh_token",
                "Optional: login_customer_id (for MCC accounts), account_id",
                "Run: marketing-mcp init google-ads",
            ],
        )

    cfg.developer_token = data["developer_token"]
    cfg.client_id = data["client_id"]
    cfg.client_secret = data["client_secret"]
    cfg.refresh_token = data["refresh_token"]
    cfg.account_id = data.get("account_id")
    cfg.login_customer_id = data.get("login_customer_id")
    return cfg, CheckResult("Google Ads", True, f"OK ({path.name})")


def _load_gtm(credentials_dir: Path) -> tuple[GoogleTagManagerConfig, CheckResult]:
    cfg = GoogleTagManagerConfig()
    path = _find_first(
        credentials_dir,
        "google-tag-manager-credentials.json",
        "google-tag-manager-*.json",
        "gtm*.json",
    )
    if not path:
        return cfg, CheckResult(
            "Google Tag Manager",
            False,
            "No credentials file found",
            [
                f"Expected at: {credentials_dir / 'google-tag-manager-credentials.json'}",
                "Re-use your GA service account JSON or create a new one.",
                "See docs/GOOGLE-TAG-MANAGER-SETUP.md",
            ],
        )

    try:
        data = _read_json(path)
    except json.JSONDecodeError as e:
        return cfg, CheckResult("Google Tag Manager", False, f"Invalid JSON in {path.name}: {e}")

    if not _is_service_account(data):
        return cfg, CheckResult(
            "Google Tag Manager",
            False,
            f"{path.name} is not a service account JSON",
            [
                "Expected fields: type=service_account, client_email, private_key, token_uri",
                f"File size: {path.stat().st_size} bytes (real service-account JSON is ~2 KB)",
            ],
        )

    cfg.credentials_path = path
    cfg.account_id = data.get("account_id")
    cfg.container_id = data.get("container_id")
    cfg.client_email = data.get("client_email")
    return cfg, CheckResult(
        "Google Tag Manager",
        True,
        f"OK ({path.name}) — service account: {cfg.client_email}",
    )


def _load_ahrefs(credentials_dir: Path) -> tuple[AhrefsConfig, CheckResult]:
    cfg = AhrefsConfig()
    txt = credentials_dir / "ahrefs-api-key.txt"
    if txt.exists():
        try:
            key = txt.read_text(encoding="utf-8").strip()
        except OSError as e:
            return cfg, CheckResult("Ahrefs", False, f"Could not read {txt.name}: {e}")
        if not key:
            return cfg, CheckResult("Ahrefs", False, f"{txt.name} is empty")
        cfg.api_key = key
        return cfg, CheckResult("Ahrefs", True, f"OK ({txt.name})")

    js = _find_first(credentials_dir, "ahrefs*.json")
    if js:
        try:
            data = _read_json(js)
        except json.JSONDecodeError as e:
            return cfg, CheckResult("Ahrefs", False, f"Invalid JSON in {js.name}: {e}")
        key = data.get("api_key")
        if not key:
            return cfg, CheckResult("Ahrefs", False, f"{js.name} missing 'api_key' field")
        cfg.api_key = key
        return cfg, CheckResult("Ahrefs", True, f"OK ({js.name})")

    return cfg, CheckResult(
        "Ahrefs",
        False,
        "No API key found",
        [f"Expected at: {credentials_dir / 'ahrefs-api-key.txt'}"],
    )


# ---------- Public API ----------


def load_config(credentials_dir: Path | None = None) -> Config:
    """Load configuration, ignoring per-integration validation failures.

    Use ``run_health_check()`` to get a structured report of what loaded vs
    failed.
    """
    creds_dir = credentials_dir or _resolve_credentials_dir()
    if not creds_dir.exists():
        logger.warning("Credentials dir does not exist: %s", creds_dir)
        return Config(credentials_dir=creds_dir)

    ga_cfg, _ = _load_analytics(creds_dir)
    ads_cfg, _ = _load_ads(creds_dir)
    gtm_cfg, _ = _load_gtm(creds_dir)
    ahrefs_cfg, _ = _load_ahrefs(creds_dir)

    return Config(
        google_analytics=ga_cfg,
        google_ads=ads_cfg,
        google_tag_manager=gtm_cfg,
        ahrefs=ahrefs_cfg,
        credentials_dir=creds_dir,
    )


def run_health_check(credentials_dir: Path | None = None) -> HealthReport:
    """Validate all credential files and return a structured report."""
    creds_dir = credentials_dir or _resolve_credentials_dir()
    report = HealthReport(credentials_dir=creds_dir)

    if not creds_dir.exists():
        report.checks.append(
            CheckResult(
                "Credentials directory",
                False,
                f"Directory does not exist: {creds_dir}",
                ["Create it: mkdir credentials"],
            )
        )
        return report

    for loader in (_load_analytics, _load_ads, _load_gtm, _load_ahrefs):
        _, check = loader(creds_dir)
        report.checks.append(check)

    return report


# ---------- Hot-reload singleton ----------


_cached_config: Config | None = None
_cached_mtimes: dict[Path, float] = {}


def _credentials_signature(creds_dir: Path) -> dict[Path, float]:
    if not creds_dir.exists():
        return {}
    sig: dict[Path, float] = {}
    for p in creds_dir.iterdir():
        if p.is_file() and not p.name.startswith("."):
            with contextlib.suppress(OSError):
                sig[p] = p.stat().st_mtime
    return sig


def get_cached_config(credentials_dir: Path | None = None) -> Config:
    """Return the cached config, re-loading if any credential file changed."""
    global _cached_config, _cached_mtimes
    creds_dir = credentials_dir or _resolve_credentials_dir()
    current_sig = _credentials_signature(creds_dir)

    if _cached_config is None or current_sig != _cached_mtimes:
        if _cached_config is not None:
            logger.info("Credential files changed — reloading config")
        _cached_config = load_config(creds_dir)
        _cached_mtimes = current_sig

    return _cached_config


def invalidate_cache() -> None:
    """Force the next ``get_cached_config()`` call to re-read from disk."""
    global _cached_config, _cached_mtimes
    _cached_config = None
    _cached_mtimes = {}


# Back-compat exports
CREDENTIALS_DIR = DEFAULT_CREDENTIALS_DIR
