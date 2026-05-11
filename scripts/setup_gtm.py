#!/usr/bin/env python
"""Interactive OAuth2 setup for Google Tag Manager."""

import json
from pathlib import Path

CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("Google Tag Manager OAuth2 Setup")
print("=" * 60)
print()

# Check for existing client config or prompt
client_id = input("OAuth Client ID: ").strip()
client_secret = input("OAuth Client Secret: ").strip()

if not client_id or not client_secret:
    print("Client ID and Client Secret are required.")
    print("Create credentials at: console.cloud.google.com → APIs & Services → Credentials")
    exit(1)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Installing google-auth-oauthlib...")
    import subprocess
    subprocess.run(["pip", "install", "google-auth-oauthlib"], check=True)
    from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/tagmanager.readonly"]

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    },
    SCOPES,
)

print("\nOpening browser for authorization...")
creds = flow.run_local_server(port=0)

account_id = input("\nGoogle Tag Manager Account ID: ").strip()
container_id = input("Container ID (e.g. GTM-XXXXXXX): ").strip()

credentials = {
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": creds.token,
    "account_id": account_id,
    "container_id": container_id,
}

output_path = CREDENTIALS_DIR / "google-tag-manager-credentials.json"
with open(output_path, "w") as f:
    json.dump(credentials, f, indent=2)

print(f"\nCredentials saved to: {output_path}")
print("You're ready to use Google Tag Manager with the MCP server!")