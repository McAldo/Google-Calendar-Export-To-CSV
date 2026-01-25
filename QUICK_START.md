# Quick Start Guide

## For Windows Users (Recommended)

If you're experiencing SSL errors (and you likely will on Windows), use the **diagnostic version** which works reliably.

### Step 1: Run the App

Double-click: **`run_app_diagnostic.bat`**

Or from command line:
```bash
venv\Scripts\activate
streamlit run calendar_export_app_diagnostic.py
```

### Step 2: Enable SSL Bypass (Required for Windows)

1. In the app, expand **"🔧 Diagnostic Options"**
2. Check **"🚨 Disable SSL Verification"**
3. You'll see warnings - this is normal and safe on your home network

### Step 3: Connect to Google

1. Click **"Connect to Google Calendar"**
2. Browser will open for Google login
3. If you see "Google hasn't verified this app":
   - Click "Advanced"
   - Click "Go to Calendar To CSV (unsafe)"
   - Click "Allow"
4. Return to the app

### Step 4: Export Events

1. **Select Calendars** - Use "Select All" or choose specific ones
2. **Set Date Range** - Pick start and end dates/times
3. **Configure Colours** - Use "Select All" or choose specific colours
4. **Map Types** - Optionally assign type labels to colours (e.g., Flamingo = "positive")
5. **Set Filename** - Default is `calendar_export_YYYY-MM-DD.csv`
6. **Click "Export to CSV"**
7. Preview results and download

## Your Settings Are Saved!

All your choices (calendars, colours, type mappings) are automatically saved to `app_settings.json` and will be remembered next time you run the app.

## Is SSL Bypass Safe?

**Yes, for your use case:**
- ✅ You're on a home network (not public WiFi)
- ✅ You're only reading calendar data (not entering passwords)
- ✅ The connection is still encrypted, just not verified
- ✅ This is a known Windows + Python 3.13 compatibility issue

**Don't use with SSL bypass on:**
- ❌ Public WiFi (coffee shops, airports, etc.)
- ❌ Untrusted networks

## Troubleshooting

### "credentials.json not found"
- Follow the Google Cloud setup in the main README.md
- Add yourself as a test user in Google Cloud Console

### "Access blocked: has not completed verification"
- Go to Google Cloud Console
- OAuth consent screen → Test users
- Add your email address

### Still getting SSL errors with bypass enabled?
- Make sure you enabled SSL bypass **BEFORE** clicking "Connect to Google Calendar"
- If you connected first, you need to reconnect after enabling bypass

## Files

- `calendar_export_app_diagnostic.py` - **Use this one** (SSL bypass for Windows)
- `calendar_export_app.py` - Standard version (may not work on Windows)
- `app_settings.json` - Your saved preferences (auto-created)
- `credentials.json` - Your Google OAuth credentials (you create this)
- `token.json` - Auto-created after first login

---

**Need more details?** See `README.md` for full setup instructions and `DIAGNOSTIC_README.md` for SSL troubleshooting details.
