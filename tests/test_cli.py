"""Tests for the CLI entry points."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from marketing_mcp.cli import cli


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "marketing-mcp" in result.output


def test_doctor_exits_nonzero_when_no_credentials(tmp_path: Path) -> None:
    runner = CliRunner()
    creds = tmp_path / "creds"
    creds.mkdir()
    result = runner.invoke(cli, ["doctor", "--credentials-dir", str(creds)])
    assert result.exit_code != 0
    assert "FAIL" in result.output or "No" in result.output


def test_doctor_passes_with_all_credentials(tmp_path: Path) -> None:
    runner = CliRunner()
    creds = tmp_path / "creds"
    creds.mkdir()
    sa = {
        "type": "service_account",
        "project_id": "p",
        "client_email": "x@p.iam.gserviceaccount.com",
        "private_key": "k",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    (creds / "google-analytics-credentials.json").write_text(json.dumps(sa))
    (creds / "google-tag-manager-credentials.json").write_text(json.dumps(sa))
    (creds / "google-ads-credentials.json").write_text(json.dumps({
        "developer_token": "x", "client_id": "x", "client_secret": "x", "refresh_token": "x"
    }))
    (creds / "ahrefs-api-key.txt").write_text("key")

    result = runner.invoke(cli, ["doctor", "--credentials-dir", str(creds)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_init_prints_instructions() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "google-analytics"])
    assert result.exit_code == 0
    assert "service account" in result.output.lower()
