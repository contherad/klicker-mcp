# Ahrefs API Setup Guide

Getting your Ahrefs API key takes about 2 minutes.

---

## Step 1: Get Your API Key

1. Log in to [ahrefs.com](https://ahrefs.com/)
2. Go to **Dashboard → API → API Settings** (or click your profile → API)
3. Copy your **API key** — it's a long string of letters and numbers

> If you don't have API access, you need an Ahrefs subscription that includes API access. API access is available on paid plans.

---

## Step 2: Save It

Create a file `credentials/ahrefs-api-key.txt` in the project folder and paste your API key as the only contents. Nothing else — just the key itself.

**Alternative:** Create `credentials/ahrefs-credentials.json`:
```json
{
  "api_key": "your-api-key-here"
}
```

Both approaches work — the server checks for both formats.

---

## Step 3: Test It

Restart the MCP server, then ask Claude something like:

- "What's the domain rating of example.com?"
- "What are the top backlinks for klickerinc.com?"
- "What organic keywords is my site ranking for?"

---

## Need Help?

If you don't have Ahrefs API access, visit [ahrefs.com/api](https://ahrefs.com/api) to learn about plans. The API is available on paid subscriptions.