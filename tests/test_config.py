"""Unit tests for the config loader and health check."""

from __future__ import annotations

from pathlib import Path

from marketing_mcp.utils.config import (
    get_cached_config,
    load_config,
    run_health_check,
)


def test_empty_credentials_dir_returns_empty_config(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert cfg.google_analytics.credentials_path is None
    assert cfg.google_ads.developer_token is None
    assert cfg.google_tag_manager.credentials_path is None
    assert cfg.ahrefs.api_key is None


def test_loads_valid_ga_service_account(credentials_dir: Path, write_credentials, sample_service_account):
    write_credentials("google-analytics-credentials.json", sample_service_account)
    cfg = load_config(credentials_dir)
    assert cfg.google_analytics.credentials_path is not None
    assert cfg.google_analytics.client_email == sample_service_account["client_email"]
    assert cfg.google_analytics.project_id == "test-project"


def test_rejects_oauth_client_secret_as_ga(credentials_dir: Path, write_credentials):
    # The "wrong file" the user originally had — OAuth client-secret JSON shape
    write_credentials(
        "google-analytics-credentials.json",
        {
            "installed": {
                "client_id": "12345-abc.apps.googleusercontent.com",
                "client_secret": "GOCSPX-...",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
    )
    cfg = load_config(credentials_dir)
    assert cfg.google_analytics.credentials_path is None  # rejected


def test_health_check_passes_when_all_present(credentials_dir, write_credentials, sample_service_account):
    write_credentials("google-analytics-credentials.json", sample_service_account)
    write_credentials("google-tag-manager-credentials.json", sample_service_account)
    write_credentials(
        "google-ads-credentials.json",
        {
            "developer_token": "DEV",
            "client_id": "CID",
            "client_secret": "CSEC",
            "refresh_token": "RTOK",
        },
    )
    write_credentials("ahrefs-api-key.txt", "my-api-key")

    report = run_health_check(credentials_dir)
    assert report.all_ok, [c for c in report.checks if not c.ok]


def test_health_check_reports_missing_ads_fields(credentials_dir, write_credentials):
    write_credentials("google-ads-credentials.json", {"client_id": "only_this"})
    report = run_health_check(credentials_dir)
    ads_check = next(c for c in report.checks if c.name == "Google Ads")
    assert not ads_check.ok
    assert "developer_token" in ads_check.message


def test_health_check_rejects_empty_ahrefs_key(credentials_dir, write_credentials):
    write_credentials("ahrefs-api-key.txt", "")
    report = run_health_check(credentials_dir)
    ah_check = next(c for c in report.checks if c.name == "Ahrefs")
    assert not ah_check.ok


def test_health_check_warns_on_invalid_json(credentials_dir, write_credentials):
    (credentials_dir / "google-analytics-credentials.json").write_text("{not valid json")
    report = run_health_check(credentials_dir)
    ga_check = next(c for c in report.checks if c.name == "Google Analytics")
    assert not ga_check.ok
    assert "JSON" in ga_check.message or "json" in ga_check.message


def test_hot_reload_picks_up_new_files(
    credentials_dir, write_credentials, sample_service_account, monkeypatch
):
    monkeypatch.setenv("MARKETING_MCP_CREDENTIALS_DIR", str(credentials_dir))

    cfg1 = get_cached_config()
    assert cfg1.ahrefs.api_key is None

    write_credentials("ahrefs-api-key.txt", "freshly-added-key")

    cfg2 = get_cached_config()
    assert cfg2.ahrefs.api_key == "freshly-added-key"


def test_example_files_are_ignored(credentials_dir, write_credentials, sample_service_account):
    # An *.example file should never be picked as the real credentials
    write_credentials("google-analytics-credentials.json.example", sample_service_account)
    cfg = load_config(credentials_dir)
    assert cfg.google_analytics.credentials_path is None


def test_ads_fallback_does_not_grab_ads_for_ga(credentials_dir, write_credentials, sample_service_account):
    """Regression: original loader picked up the Ads JSON as GA credentials."""
    write_credentials(
        "google-ads-credentials.json",
        {
            "developer_token": "DEV",
            "client_id": "CID",
            "client_secret": "CSEC",
            "refresh_token": "RTOK",
        },
    )
    cfg = load_config(credentials_dir)
    assert cfg.google_analytics.credentials_path is None
    assert cfg.google_ads.developer_token == "DEV"
