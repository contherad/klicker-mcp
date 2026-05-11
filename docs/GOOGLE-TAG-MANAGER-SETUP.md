# Google Tag Manager OAuth2 Setup Guide

This guide walks you through setting up OAuth2 credentials for Google Tag Manager so Claude can read your GTM data.

---

## Step 1: Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Name it `klicker-mcp` → click **Create**
4. Copy your **Project ID** (shown on the dashboard)

---

## Step 2: Enable the Tag Manager API

1. Go to **APIs & Services → Library**
2. Search for **"Google Tag Manager API"**
3. Click it → click **Enable**

---

## Step 3: Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **"+ Create Credentials"** → choose **"OAuth client ID"**
3. For **Application type**, choose **"Desktop app"**
4. Name it `klicker-mcp-gtm`
5. Click **Create**
6. You'll see a popup with your **Client ID** and **Client Secret** — copy them now
7. Click **Download JSON** (optional) or just copy the values from the screen

---

## Step 4: Get a Refresh Token

Google OAuth2 requires you to go through the authorization flow once to get a refresh token. Run this script:

```
python scripts/setup_gtm.py
```

It will ask for your Client ID and Client Secret, then open a browser for you to authorize, and save the refresh token.

**If you're on Windows and the script doesn't open a browser**, do this instead:

1. Create a file `scripts/do_gtm_auth.py` with these contents:

```python
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/tagmanager.readonly']

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "YOUR_CLIENT_ID_HERE",
            "client_secret": "YOUR_CLIENT_SECRET_HERE",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    },
    SCOPES
)
creds = flow.run_local_server(port=0)
print(f"Refresh token: {creds.token}")
```

2. Replace `YOUR_CLIENT_ID_HERE` and `YOUR_CLIENT_SECRET_HERE` with your actual values
3. Run: `python scripts/do_gtm_auth.py`
4. A browser will open — log in and approve access
5. Copy the **refresh token** from the command line output

3. Create a file `credentials/google-tag-manager-credentials.json` with:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "refresh_token": "your-refresh-token",
  "account_id": "your-gtm-account-id"
}
```

---

## Step 5: Find Your GTM Account and Container IDs

1. Go to [tagmanager.google.com](https://tagmanager.google.com/)
2. Click **Admin** (the gear icon)
3. Your **Account ID** is shown at the top
4. Under the account, click your **Container** to see the **Container ID** (it's a number like `GTM-XXXXXXX`)

---

## Step 6: Save Everything

Create `credentials/google-tag-manager-credentials.json`:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "refresh_token": "your-refresh-token",
  "account_id": "123456789",
  "container_id": "GTM-XXXXXXX"
}
```

---

## That's It!

Once you've saved the JSON file, restart the MCP server and Claude will be able to answer questions like:

- "What tracking scripts are active on my site?"
- "What triggers fire when someone submits a form?"
- "What variables are defined in my GTM workspace?"
- "Show me my GTM container version details"

---

## Troubleshooting

**"Error 401: Invalid credentials"**
- Your refresh token may have expired — re-run the auth script
- Make sure the client_id and client_secret match exactly

**Can't find Account ID?**
- In GTM, click Admin → Account Settings. It's shown under "Account ID".

**Need help with OAuth flow?**
- The `scripts/setup_gtm.py` script handles the OAuth flow automatically
- Run it and follow the instructions