# Google Ads API Setup Guide

This guide walks you through setting up Google Ads API access so Claude can query your ad performance data.

---

## Step 1: Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Name it `klicker-mcp` → click **Create**
4. Copy your **Project ID** (shown on the dashboard)

---

## Step 2: Enable the Google Ads API

1. Go to **APIs & Services → Library**
2. Search for **"Google Ads API"**
3. Click it → click **Enable**

---

## Step 3: Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **"+ Create Credentials"** → choose **"OAuth client ID"**
3. For **Application type**, choose **"Desktop app"**
4. Name it `klicker-mcp-ads`
5. Click **Create**
6. You'll see a popup with your **Client ID** and **Client Secret** — copy them now

---

## Step 4: Get Your Developer Token

1. Go to [ads.google.com](https://ads.google.com/)
2. Click **Tools → Settings → API Center** (or search for "API access")
3. Your **Developer Token** is shown there — it's a string like `abc123DEF456ghi789jkl`
4. If you don't have API access, request it (may take 1-2 business days for approval)

---

## Step 5: Get a Refresh Token

Run the setup script:

```
python scripts/setup_google_ads.py
```

The script will ask for your Client ID, Client Secret, Developer Token, and a refresh token.

**To get the refresh token**, you need to authorize once. The script `scripts/setup_google_ads.py` handles this — it will open a browser for you to log in and approve.

If the script can't open a browser automatically, do this manually:

1. Build the authorization URL (replace YOUR_CLIENT_ID with your actual client ID):
```
https://accounts.google.com/o/oauth2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&response_type=code&scope=https://www.googleapis.com/auth/adwords&access_type=offline
```

2. Open that URL in your browser, log in, and approve access
3. You'll be redirected to `http://localhost/?code=XXXX` — copy the `code` parameter value
4. Exchange it for tokens using curl:

```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d "code=YOUR_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=http://localhost" \
  -d "grant_type=authorization_code"
```

5. Copy the `refresh_token` from the response

---

## Step 6: Find Your Google Ads Account ID

1. Go to [ads.google.com](https://ads.google.com/)
2. Click the **gear icon** → **Account Settings**
3. Your **Customer ID** is shown as `123-456-7890` — remove the hyphens (so `1234567890`)
4. This is the `customer_id` you'll use when asking Claude about your ads

---

## Step 7: Save Your Credentials

Run:
```
python scripts/setup_google_ads.py
```

Or create `credentials/google-ads-credentials.json` directly:

```json
{
  "developer_token": "your-developer-token",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "refresh_token": "your-refresh-token",
  "account_id": "1234567890"
}
```

---

## That's It!

Once you've saved the credentials, restart the MCP server and Claude will be able to answer questions like:

- "How much did I spend on ads last month?"
- "Which campaigns have the best ROAS?"
- "What are my top-performing keywords?"
- "Show me my ad group performance for the last 30 days"

---

## Troubleshooting

**"Error 401: Invalid credentials"**
- Your refresh token may be invalid or expired — re-run the auth flow
- Make sure the developer_token is correct (no spaces at start/end)

**"Developer token not approved"**
- Google Ads API access requires approval for some account types
- Check [this page](https://developers.google.com/google-ads/api/docs/getting-started/authentication) for details

**"Can't find my Customer ID"**
- In Google Ads, click the **gear icon** → **Account Settings**
- It's the number shown as `123-456-7890`

**Need help with the OAuth flow?**
- See Step 5 above for the manual refresh token process
- Your refresh token is permanent — you only need to do this once