# Klicker MCP Server

Connect Claude Desktop to Google Analytics, Google Ads, Google Tag Manager, and Ahrefs — all in one unified MCP server.

**For Kade at Klicker** — setup for Windows, designed for marketers who aren't developers.

---

## What Is This?

This is a **local MCP server** that lets Claude read and analyze your marketing data:

- **Google Analytics 4** — traffic, conversions, user behavior, custom reports
- **Google Ads** — campaigns, keywords, spend, ROAS, performance over time
- **Google Tag Manager** — active tags, triggers, and variables in your container
- **Ahrefs** — domain rating, backlinks, organic keywords, SEO metrics

Instead of opening four different dashboards, you can ask Claude directly:

> "What's my organic traffic trend for the last 90 days?"
> "Which Google Ads campaigns have the best ROAS this month?"
> "What tracking scripts are deployed on my site?"
> "What keywords is example.com ranking for in the top 10?"

---

## Prerequisites

- **Python 3.10 or higher** — [Download from python.org](https://www.python.org/downloads/)
  - On Windows, make sure to check *"Add Python to PATH"* during install
- **A Google account** with access to Google Analytics, Google Ads, and/or Google Tag Manager
- **Ahrefs API access** (paid subscription) — [check plans](https://ahrefs.com/pricing)

---

## Quick Setup (Windows)

### Step 1: Download the Project

Click the green **Code** button on [the GitHub repo](https://github.com/contherad/klicker-mcp) → **Download ZIP**

Extract the ZIP to your Desktop (or anywhere you prefer).

### Step 2: Install Python Dependencies

Open **Command Prompt** (`Win + R` → type `cmd` → Enter) and run:

```
cd %USERPROFILE%\Desktop\klicker-mcp
pip install -r requirements.txt
```

> If you extracted to a different location, adjust the path above.

### Step 3: Set Up Your Credentials

#### Google Analytics

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) → Create a project
2. Enable **Google Analytics Admin API** and **Google Analytics Data API**
3. Go to **Credentials** → **Service Accounts** → create one
4. Download the JSON key file → save as `credentials/google-analytics-credentials.json`
5. In GA4, go to **Admin → Property Access Management** → add the service account email with "Viewer" access

See: [docs/GOOGLE-ANALYTICS-SETUP.md](docs/GOOGLE-ANALYTICS-SETUP.md)

#### Google Ads

1. Enable **Google Ads API** in your Google Cloud project
2. Create **OAuth2 credentials** (Desktop app type) → get Client ID + Client Secret
3. Get your **Developer Token** from ads.google.com → Tools → Settings → API Center
4. Run: `python scripts/setup_google_ads.py` — or create `credentials/google-ads-credentials.json` manually

See: [docs/GOOGLE-ADS-SETUP.md](docs/GOOGLE-ADS-SETUP.md)

#### Google Tag Manager

1. Enable **Google Tag Manager API** in your Google Cloud project
2. Create **OAuth2 credentials** (Desktop app type) → get Client ID + Client Secret
3. Run: `python scripts/setup_gtm.py` — or create `credentials/google-tag-manager-credentials.json` manually

See: [docs/GOOGLE-TAG-MANAGER-SETUP.md](docs/GOOGLE-TAG-MANAGER-SETUP.md)

#### Ahrefs

1. Get your API key from [ahrefs.com](https://ahrefs.com/) → Dashboard → API
2. Run: `python scripts/setup_ahrefs.py` — or create `credentials/ahrefs-api-key.txt` manually

See: [docs/AHREFS-SETUP.md](docs/AHREFS-SETUP.md)

---

## Step 4: Connect to Claude Desktop

1. Open **Claude Desktop** (click the **Wrench icon** or go to **Settings → MCP Servers**)
2. Click **Add MCP Server**
3. Name it: `marketing-mcp`
4. For the **Command**, enter: `python`
5. For the **Arguments**, enter: `-m marketing_mcp.server`
6. For the **Working Directory**, enter the path to the `klicker-mcp` folder:
   - If on Desktop: `C:\Users\YourName\Desktop\klicker-mcp`

> **Tip:** The exact path to the klicker-mcp folder is shown at the top of File Explorer when you're inside the folder.

### Example Configuration

```
Command: python
Arguments: -m marketing_mcp.server
Working Directory: C:\Users\YourName\Desktop\klicker-mcp
```

If Claude Desktop doesn't have a Working Directory field, set it via command line:

```cmd
set MCPPATH=C:\Users\YourName\Desktop\klicker-mcp
```

---

## Step 5: Test It

Restart Claude Desktop. Then ask:

```
What's my Google Analytics traffic summary for the last 30 days?
Show me my Google Ads campaign performance this month.
What's the domain rating of klickerinc.com according to Ahrefs?
```

If you get an error, check the **Troubleshooting** section below.

---

## Available Tools

### Google Analytics (GA4)
| Tool | What it does |
|------|-------------|
| `ga_get_account_summaries` | List all GA4 accounts and properties you have access to |
| `ga_get_property_details` | Get details about a specific GA4 property |
| `ga_run_report` | Run a custom GA4 report with dimensions and metrics you specify |
| `ga_run_realtime_report` | Get current active users, page views in last 30 minutes |
| `ga_get_custom_dimensions` | List available custom dimensions in your property |

### Google Ads
| Tool | What it does |
|------|-------------|
| `ads_get_campaigns` | List all campaigns with spend, clicks, impressions |
| `ads_get_campaign_performance` | Performance metrics for a specific campaign over a date range |
| `ads_get_keywords_performance` | Keyword-level performance: clicks, cost, conversions, CTR |
| `ads_get_ad_groups` | List ad groups within a campaign |
| `ads_get_account_summary` | High-level spend, clicks, conversions for entire account |

### Google Tag Manager
| Tool | What it does |
|------|-------------|
| `gtm_list_containers` | List all GTM containers in your account |
| `gtm_get_workspace_tags` | Show all tags (tracking scripts) in the active workspace |
| `gtm_list_triggers` | List all triggers (events that fire tags) |
| `gtm_list_variables` | List all variables (data sources) in the workspace |
| `gtm_get_container_version` | Get details about a specific container version |

### Ahrefs
| Tool | What it does |
|------|-------------|
| `ahrefs_get_domain_rating` | Domain Rating (DR) score for any website |
| `ahrefs_get_backlinks` | Top backlinks pointing to a domain |
| `ahrefs_get_organic_keywords` | Organic keyword rankings with positions, traffic, CPC |
| `ahrefs_get_linking_domains` | Number of unique domains linking to a site |
| `ahrefs_compare_domains` | Compare DR and link metrics across multiple domains |

---

## Troubleshooting

### "Module not found" error
Make sure you ran `pip install -r requirements.txt` in the correct folder:
```cmd
cd %USERPROFILE%\Desktop\klicker-mcp
pip install -r requirements.txt
```

### "Credentials not found" error
Check that your credential files are in the `credentials/` folder (inside klicker-mcp):
```
klicker-mcp/
└── credentials/
    ├── google-analytics-credentials.json   ← must exist if using GA
    ├── google-ads-credentials.json          ← must exist if using Ads
    ├── google-tag-manager-credentials.json ← must exist if using GTM
    └── ahrefs-api-key.txt                   ← must exist if using Ahrefs
```

### "Permission denied" in Google Analytics
Make sure you've added the service account email to your GA4 property:
1. In GA4 → Admin → Property Access Management
2. Click "+" → paste the service account email (looks like `something@project-id.iam.gserviceaccount.com`)
3. Set role to "Viewer"

### "Invalid credentials" in Google Ads
- Re-check your developer token (no extra spaces)
- Make sure the OAuth2 Client ID and Secret are for a **Desktop app** credential type
- Your refresh token may have expired — re-run `python scripts/setup_google_ads.py`

### Claude Desktop doesn't connect to the MCP server
1. Make sure the working directory path is correct
2. Try restarting Claude Desktop
3. Check the command: `python -m marketing_mcp.server` — does it run without errors in a terminal?

To test manually, open Command Prompt and run:
```cmd
cd %USERPROFILE%\Desktop\klicker-mcp
python -m marketing_mcp.server
```
If you see "Starting Marketing MCP Server..." it's running correctly. Press `Ctrl + C` to stop it.

---

## Updating the Server

To update to the latest version, re-download the ZIP from GitHub and replace the folder, then re-run:
```cmd
pip install -r requirements.txt --upgrade
```

---

## Uninstall

1. Remove the `klicker-mcp` folder from your Desktop
2. Remove the MCP server entry from Claude Desktop settings
3. Optionally delete the `credentials/` folder if you want to completely remove your stored credentials