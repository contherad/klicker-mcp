"""Configuration loader — reads credentials from the credentials/ directory."""

import os
import json
from pathlib import Path
from pydantic import BaseModel

CREDENTIALS_DIR = Path(__file__).parent.parent.parent / "credentials"


class GoogleAnalyticsConfig(BaseModel):
    credentials_path: Path | None = None
    project_id: str | None = None


class GoogleAdsConfig(BaseModel):
    developer_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    account_id: str | None = None


class GoogleTagManagerConfig(BaseModel):
    credentials_path: Path | None = None
    account_id: str | None = None
    container_id: str | None = None


class AhrefsConfig(BaseModel):
    api_key: str | None = None


class Config(BaseModel):
    google_analytics: GoogleAnalyticsConfig = GoogleAnalyticsConfig()
    google_ads: GoogleAdsConfig = GoogleAdsConfig()
    google_tag_manager: GoogleTagManagerConfig = GoogleTagManagerConfig()
    ahrefs: AhrefsConfig = AhrefsConfig()


def _find_json(*patterns: str) -> Path | None:
    for pattern in patterns:
        matches = list(CREDENTIALS_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None


def load_config() -> Config:
    config = Config()

    # Google Analytics
    ga_creds = _find_json("google-analytics-*.json", "ga-*.json", "analytics-*.json", "google-ads-credentials.json")
    if ga_creds and ga_creds.exists():
        config.google_analytics.credentials_path = ga_creds
        try:
            with open(ga_creds) as f:
                data = json.load(f)
                config.google_analytics.project_id = data.get("project_id") or os.environ.get("GOOGLE_PROJECT_ID")
        except Exception:
            pass

    # Google Ads
    ads_creds = _find_json("google-ads-credentials.json", "google-ads*.json", "ads*.json")
    if ads_creds and ads_creds.exists():
        try:
            with open(ads_creds) as f:
                data = json.load(f)
                config.google_ads.developer_token = data.get("developer_token")
                config.google_ads.client_id = data.get("client_id")
                config.google_ads.client_secret = data.get("client_secret")
                config.google_ads.refresh_token = data.get("refresh_token")
                config.google_ads.account_id = data.get("account_id")
        except Exception:
            pass

    # Google Tag Manager
    gtm_creds = _find_json("google-tag-manager-*.json", "gtm*.json")
    if gtm_creds and gtm_creds.exists():
        config.google_tag_manager.credentials_path = gtm_creds
        try:
            with open(gtm_creds) as f:
                data = json.load(f)
                config.google_tag_manager.account_id = data.get("account_id")
                config.google_tag_manager.container_id = data.get("container_id")
        except Exception:
            pass

    # Ahrefs
    ahrefs_txt = CREDENTIALS_DIR / "ahrefs-api-key.txt"
    if ahrefs_txt.exists():
        config.ahrefs.api_key = ahrefs_txt.read_text().strip()
    else:
        ahrefs_json = _find_json("ahrefs*.json")
        if ahrefs_json and ahrefs_json.exists():
            try:
                with open(ahrefs_json) as f:
                    data = json.load(f)
                    config.ahrefs.api_key = data.get("api_key")
            except Exception:
                pass

    return config