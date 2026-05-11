#!/usr/bin/env python
"""Get OAuth2 credentials interactively for Google Ads."""

import os
from pathlib import Path

CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("Google Ads OAuth2 Setup")
print("=" * 60)
print()
print("This script will help you get your Google Ads API credentials.")
print()
print("PREREQUISITE: You need a Google Cloud project with the")
print("  Google Ads API enabled and OAuth2 credentials created.")
print("  See: docs/GOOGLE-ADS-SETUP.md")
print()

client_id = input("OAuth Client ID: ").strip()
client_secret = input("OAuth Client Secret: ").strip()
developer_token = input("Developer Token: ").strip()
refresh_token = input("Refresh Token: ").strip()
account_id = input("Google Ads Account ID (e.g. 123-456-7890): ").strip().replace("-", "")

if not all([client_id, client_secret, developer_token, refresh_token]):
    print("Error: All fields are required.")
    exit(1)

credentials = {
    "developer_token": developer_token,
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": refresh_token,
    "account_id": account_id,
}

output_path = CREDENTIALS_DIR / "google-ads-credentials.json"
with open(output_path, "w") as f:
    import json
    json.dump(credentials, f, indent=2)

print()
print(f"Credentials saved to: {output_path}")
print("You're ready to use Google Ads with the MCP server!")