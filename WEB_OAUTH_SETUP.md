# Web OAuth Client Setup Guide

This guide explains how to switch from Desktop OAuth client to Web OAuth client for seamless mobile authentication.

## Why Switch to Web OAuth?

**Desktop OAuth** (current setup):
- ❌ Requires copy/pasting the localhost URL
- ❌ Cumbersome on mobile devices
- ✅ Works anywhere (local or cloud)

**Web OAuth** (new setup):
- ✅ Automatic redirect back to your app
- ✅ Seamless mobile experience
- ✅ Just click → authorize → done!
- ⚠️ Requires configuring redirect URI in Google Cloud Console

---

## Part 1: Create Web OAuth Client in Google Cloud Console

### Step 1: Open Google Cloud Console

1. Go to https://console.cloud.google.com
2. Select your project: **calendartocsv**
3. Navigate to **APIs & Services** → **Credentials**

### Step 2: Create Web Application OAuth Client

1. Click **"+ CREATE CREDENTIALS"** at the top
2. Select **"OAuth client ID"**
3. For **"Application type"**, choose **"Web application"**
4. Give it a name: `Calendar Export Web Client`

### Step 3: Configure Redirect URIs

Under **"Authorized redirect URIs"**, click **"+ ADD URI"** and add your Streamlit Cloud URL:

```
https://YOUR-APP-NAME.streamlit.app
```

Replace `YOUR-APP-NAME` with your actual Streamlit Cloud app name.

**Example:**
```
https://mcaldo-google-calendar-export-to-csv.streamlit.app
```

**Important notes:**
- ✅ Use `https://` (not `http://`)
- ✅ NO trailing slash at the end
- ✅ Must match your Streamlit Cloud URL exactly

### Step 4: Save and Download Credentials

1. Click **"CREATE"**
2. You'll see your new **Client ID** and **Client Secret**
3. Click **"DOWNLOAD JSON"** or copy the credentials

You'll get a JSON file that looks like:
```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "calendartocsv",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["https://YOUR-APP-NAME.streamlit.app"]
  }
}
```

Note the **"web"** key instead of **"installed"**!

---

## Part 2: Update Streamlit Cloud Secrets

### Step 5: Convert JSON to TOML for Streamlit Secrets

1. Go to your Streamlit Cloud app
2. Click **Settings** (gear icon) → **Secrets**
3. Replace the existing secrets with the new format:

```toml
[google_credentials]
client_type = "web"
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
project_id = "calendartocsv"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_secret = "YOUR_CLIENT_SECRET"
redirect_uris = ["https://YOUR-APP-NAME.streamlit.app"]
```

**Key changes from old format:**
- ✅ Added `client_type = "web"` (new line!)
- ✅ `redirect_uris` now points to your Streamlit app (not localhost)
- ✅ Make sure to update `client_id`, `client_secret`, and `redirect_uris`

### Step 6: Save and Reboot

1. Click **"Save"**
2. Click **"Reboot app"** or wait for automatic reboot
3. Wait 1-2 minutes for the app to restart

---

## Part 3: Test the New Flow

### Step 7: Test Authentication

1. Open your Streamlit Cloud app on any device (phone, tablet, computer)
2. You should see: **"Using Web OAuth flow"**
3. Click the **"🔓 Authorize with Google"** button
4. Log in and grant permissions
5. You'll be **automatically redirected back** to your app - no copy/paste needed!
6. Done! ✅

---

## Troubleshooting

### "redirect_uri_mismatch" Error

**Problem:** The redirect URI doesn't match what's configured in Google Cloud Console.

**Solution:**
1. Check that the redirect URI in Streamlit secrets **exactly matches** the one in Google Cloud Console
2. Make sure there's no trailing slash: ✅ `https://app.streamlit.app` ❌ `https://app.streamlit.app/`
3. Use `https://` not `http://`

### Still Shows "Desktop OAuth flow (manual)"

**Problem:** The app hasn't detected the web client type.

**Solution:**
1. Make sure you added `client_type = "web"` to Streamlit secrets
2. Reboot the app after saving secrets
3. Check debug panel to verify client type is "web"

### OAuth Callback Not Processing

**Problem:** After authorizing, nothing happens or you see an error.

**Solution:**
1. Clear your browser cache and cookies
2. Try in an incognito/private window
3. Check Streamlit Cloud logs for error messages
4. Make sure the app is on the `web-oauth-client` branch

### Want to Revert to Desktop OAuth?

Simply change in Streamlit secrets:
```toml
client_type = "installed"
redirect_uris = ["http://localhost"]
```

And use your old desktop client credentials.

---

## Comparison: Before and After

### Before (Desktop OAuth)
1. Click auth link
2. Authorize in Google
3. See "This site can't be reached"
4. Copy localhost URL from browser
5. Paste URL back into app
6. Authenticated ✅

### After (Web OAuth)
1. Click auth link
2. Authorize in Google
3. **Automatically redirected back**
4. Authenticated ✅

Much simpler! 🎉

---

## Security Notes

**Is Web OAuth safe?**
- ✅ Yes! It's the standard OAuth flow used by most web apps
- ✅ Your credentials are still private in Streamlit secrets
- ✅ Google handles all the authentication securely
- ✅ Only your specific Streamlit URL can receive the OAuth callback

**Can others use my app?**
- Anyone with the URL can access the app
- But they authenticate with **their own** Google account
- They only see **their own** calendar data
- Your calendar data remains private to you

---

## Need Help?

1. Check the debug panel in the app (🔍 Debug Info)
2. Verify client type shows "web"
3. Verify redirect_uri matches your Streamlit URL
4. Check Streamlit Cloud logs for error messages

---

Good luck! 🚀
