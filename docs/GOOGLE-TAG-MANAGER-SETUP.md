# Google Tag Manager Setup Guide

This guide walks you through setting up service account credentials for Google Tag Manager so Claude can read your GTM container.

The MCP server uses a **service account** for GTM (same auth pattern as Google Analytics). If you already set up Google Analytics with a service account, you can reuse it — see the "Reusing your GA service account" shortcut below.

---

## Step 1: Create a Google Cloud Project

If you already have one from the Google Analytics setup, skip to Step 2 and use the same project.

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Name it `klicker-mcp` → click **Create**
4. Copy your **Project ID** (shown on the dashboard)

---

## Step 2: Enable the Tag Manager API

1. With your project selected, go to **APIs & Services → Library**
2. Search for **"Tag Manager API"**
3. Click it → click **Enable**

Or jump straight to: `https://console.cloud.google.com/apis/library/tagmanager.googleapis.com?project=YOUR_PROJECT_ID`

---

## Step 3: Create a Service Account (or reuse the GA one)

### Option A — Reuse your existing GA service account (recommended if you already set up GA)

Copy your existing GA credentials file to the GTM path:

```cmd
cd %USERPROFILE%\Documents\git\klicker-mcp
copy /Y credentials\google-analytics-credentials.json credentials\google-tag-manager-credentials.json
```

The service account email will be the same as your GA service account (something like `klicker-mcp@your-project-id.iam.gserviceaccount.com`). Use this email in Step 4.

### Option B — Create a new dedicated service account

1. Go to **APIs & Services → Credentials**
2. Click **"+ Create Credentials"** → choose **"Service Account"**
3. Name it `klicker-mcp-gtm` → click **Create**
4. Skip the optional "Grant this service account access to project" step — click **Done**
5. Click the new service account → **Keys** tab → **Add Key → Create new key**
6. Choose **JSON** → click **Create** (the file downloads automatically)
7. Move that file into the project's `credentials/` folder and rename it to:
   ```
   google-tag-manager-credentials.json
   ```

---

## Step 4: Grant the Service Account Access in GTM

1. Go to [tagmanager.google.com](https://tagmanager.google.com/)
2. Open the account that owns the container you want to read
3. Click **Admin** (top right)
4. Under **Account** (left column), click **User Management**
5. Click the **+** button → **Add users**
6. Email: paste the service account email (e.g. `klicker-mcp@your-project-id.iam.gserviceaccount.com`)
7. Account permissions: **User** (read-only is fine)
8. Container permissions: **Read** for each container you want to expose
9. Click **Invite**

> GTM may warn that it can't email the invite to a service account address — that's expected and harmless. The permission still takes effect immediately.

### Workaround: GTM UI rejects service account emails

Like GA4, the GTM **User Management** UI has a known issue rejecting `@*.iam.gserviceaccount.com` addresses with errors such as "invalid email" or "user not found". If you hit this, grant the permission via the Tag Manager API instead:

1. Open the [`accounts.user_permissions.create` API Explorer](https://developers.google.com/tag-platform/tag-manager/api/v2/reference/accounts/user_permissions/create)
2. On the right, expand the **Try this method** panel
3. In **parent**, enter: `accounts/YOUR_GTM_ACCOUNT_ID`
   - Find this in your GTM URL: `tagmanager.google.com/#/container/accounts/<ACCOUNT_ID>/containers/<CONTAINER_ID>/...`
4. In the **Request body**, paste (adjust email, container ID, and permission as needed):
   ```json
   {
     "emailAddress": "your-service-account@your-project.iam.gserviceaccount.com",
     "accountAccess": { "permission": "user" },
     "containerAccess": [
       {
         "containerId": "YOUR_CONTAINER_ID",
         "permission": "read"
       }
     ]
   }
   ```
   - `accountAccess.permission` options: `user`, `admin`
   - `containerAccess.permission` options: `read`, `edit`, `approve`, `publish`
5. In the OAuth scope picker, make sure `https://www.googleapis.com/auth/tagmanager.manage.users` is selected (the Explorer may prompt for it)
6. Click **Execute** and sign in with a Google account that has GTM **admin** rights on the target account
7. A `200` response with the new permission object confirms success
8. Verify in GTM → Admin → User Management — the service account will now appear

If you have multiple containers, you can repeat with additional entries in the `containerAccess` array, or run the call once per container.

---

## Step 5: Find Your GTM Account and Container IDs

1. Go to [tagmanager.google.com](https://tagmanager.google.com/) and open your container
2. Look at the URL: `tagmanager.google.com/#/container/accounts/<ACCOUNT_ID>/containers/<CONTAINER_ID>/...`
3. Both IDs are numeric (the public ID shown in the UI like `GTM-XXXXXXX` is different — Claude needs the **numeric container ID** from the URL, not the public one)

You don't need to save these IDs anywhere — just share them with Claude when you ask GTM questions.

---

## Step 6: Verify the Credentials File

The file at `credentials/google-tag-manager-credentials.json` must be a **service account JSON** (typically ~2 KB). It should contain fields like:

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

**If the file is only ~400 bytes**, you have the wrong file — that's an OAuth client-secret JSON (`client_secret_...apps.googleusercontent.com.json`), not a service account key. Re-download the key from **Keys → Add Key → Create new key** for the service account.

---

## That's It!

Once the file is in place, restart Claude Desktop fully (system tray → Quit, then reopen). Claude will be able to answer questions like:

- "What tracking scripts are active on my site?"
- "What triggers fire when someone submits a form?"
- "What variables are defined in my GTM workspace?"
- "Show me my GTM container version details"

---

## Troubleshooting

**"Service account info was not in the expected format, missing fields token_uri, client_email"**
- The credentials file isn't a service account JSON. Check the file size — it should be ~2 KB. If it's ~400 bytes, it's an OAuth client-secret file by mistake.

**"Not found or permission denied" (HTTP 404)**
- The service account hasn't been granted access in GTM yet. Re-check Step 4. Google returns 404 (not 403) for "permission denied" to avoid leaking whether an account exists.
- Or the Tag Manager API isn't enabled on the GCP project — see Step 2.

**Can't find Account ID?**
- It's in the URL when you're inside the GTM container, not in the in-app Admin → Account Settings page (which often shows the *public* container ID like `GTM-XXXXXXX` instead).
