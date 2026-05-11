"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from marketing_mcp.utils.config import invalidate_cache


@pytest.fixture(autouse=True)
def _reset_config_cache() -> None:
    """Wipe the config singleton between tests."""
    invalidate_cache()


@pytest.fixture
def credentials_dir(tmp_path: Path) -> Path:
    d = tmp_path / "credentials"
    d.mkdir()
    return d


@pytest.fixture
def sample_service_account() -> dict:
    """A minimally-valid service account JSON shape."""
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "abc",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
        "client_email": "tester@test-project.iam.gserviceaccount.com",
        "client_id": "1234",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    }


@pytest.fixture
def write_credentials(credentials_dir: Path, sample_service_account: dict):
    """Helper to drop credential files into the fake creds dir."""
    def _write(name: str, content) -> Path:
        path = credentials_dir / name
        if isinstance(content, (dict, list)):
            path.write_text(json.dumps(content), encoding="utf-8")
        else:
            path.write_text(str(content), encoding="utf-8")
        return path
    return _write
