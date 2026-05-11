# Google Analytics Setup Guide

This guide walks you through getting your Google Analytics credentials so Claude can read your GA4 data.

---

## Step 1: Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Click **"Select a project"** at the top → **"New Project"**
3. Name it something like `klicker-mcp` → click **Create**
4. Copy your **Project ID** (you'll need it later — it's on the dashboard)

---

## Step 2: Enable the Analytics APIs

1. With your project selected, go to **APIs & Services → Library**
2. Search for and enable these two APIs:
   - **Google Analytics Admin API**
   - **Google Analytics Data API**

---

## Step 3: Create a Service Account

1. Go to **APIs & Services → Credentials**
2. Click **"+ Create Credentials"** → choose **"Service Account"**
3. Name it `klicker-mcp` → click **Create**
4. Skip the optional "Grant this service account access to project" step — click **Done**
5. Click on your new service account from the list
6. Go to the **"Keys"** tab → **"Add Key" → "Create new key"**
7. Choose **JSON** → click **Create**
8. The file will download automatically. **Keep this file safe!**

---

## Step 4: Add the Service Account to Your GA4 Property

1. Go to [analytics.google.com](https://analytics.google.com/)
2. Select your property → click **Admin** (the gear icon)
3. Under **Property Access Management**, click **"+"**
4. Paste the service account email (it looks like: `klicker-mcp@your-project-id.iam.gserviceaccount.com`)
5. Set role to **"Viewer"** → click **Add**

### Workaround: GA4 UI rejects service account emails

Google has a known issue where the GA4 **Property Access Management** UI only accepts standard Gmail / Google Workspace addresses and refuses service account emails ending in `@*.iam.gserviceaccount.com`. If you hit this, use the Admin API directly:

1. Open the [`accessBindings.create` API Explorer](https://developers.google.com/analytics/devguides/config/admin/v1/rest/v1beta/properties.accessBindings/create)
2. On the right, expand the **Try this method** panel
3. In **parent**, enter: `properties/YOUR_GA4_PROPERTY_ID` (find it in your GA4 URL: `analytics.google.com/analytics/web/#/p<PROPERTY_ID>`)
4. In the **Request body**, paste:
   ```json
   {
     "user": "your-service-account@your-project.iam.gserviceaccount.com",
     "roles": ["predefinedRoles/viewer"]
   }
   ```
5. Click **Execute** and sign in with a Google account that has GA4 **Admin** rights on the property
6. A `200` response echoing the email and roles confirms it worked
7. Go back to GA4 → Admin → Property Access Management and the service account will now appear

---

## Step 5: Save the Credentials File

1. Find the JSON file you downloaded in Step 3
2. Copy it to the `credentials/` folder in this project
3. Rename it to: `google-analytics-credentials.json`

> The file path should look like: `klicker-mcp/credentials/google-analytics-credentials.json`

---

## Step 6: Find Your GA4 Property ID

1. In GA4, go to **Admin → Property Settings**
2. Copy the **Property ID** (a number like `123456789`)
3. You don't need to save it anywhere special — just share it with me when you ask questions about your analytics

---

## That's It!

Once you've saved the JSON file, restart the MCP server and Claude will be able to answer questions like:

- "What was my traffic last month compared to the month before?"
- "Which pages get the most visitors?"
- "What devices are my visitors using?"
- "Where are my visitors located?"

---

## Troubleshooting

**"Credentials not found" error**
- Make sure the file is named exactly `google-analytics-credentials.json` (check for extra spaces or numbers added by your browser)
- Make sure it's in the `credentials/` folder (not a subfolder)

**"Permission denied" error**
- Make sure you've added the service account email to your GA4 property (Step 4)
- The service account needs "Viewer" access at minimum

**Can't find your Property ID?**
- In GA4, click Admin → Property Settings. It's the number shown there.

---

## Need Help?

If you get stuck, just let me know. I can walk you through any step you need. The hardest part is usually Step 4 (adding the service account to GA4) — don't skip it!