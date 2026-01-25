# Google Calendar Export - DIAGNOSTIC VERSION

## ⚠️ IMPORTANT WARNING

This is a **DIAGNOSTIC VERSION** of the app that includes SSL verification bypass options.

**This version should ONLY be used for:**
- Troubleshooting SSL/connectivity errors
- Identifying the root cause of connection issues
- Testing whether SSL interception is the problem

**DO NOT use this version in production or on untrusted networks!**

---

## What's Different in This Version?

### Added Features:

1. **SSL Verification Bypass Option**
   - Toggle to disable SSL certificate verification
   - Helps diagnose if antivirus/proxy is interfering
   - **INSECURE** - only for diagnostics!

2. **Enhanced Error Messages**
   - Detailed troubleshooting tips when authentication fails
   - Better feedback about connection issues

3. **Connection Testing**
   - Test button to try reconnecting with SSL enabled
   - Helps verify if the issue is resolved

4. **Visual Warnings**
   - Clear indicators when SSL is disabled
   - Reminders about security risks

---

## How to Use This Diagnostic Version

### Step 1: Run the Diagnostic App

```bash
streamlit run calendar_export_app_diagnostic.py
```

### Step 2: Try Normal Connection First

1. Click **"Connect to Google Calendar"** without enabling SSL bypass
2. If it works → Great! You don't have an SSL issue
3. If you get the SSL error → Proceed to Step 3

### Step 3: Enable SSL Bypass (Diagnostics Only!)

1. Expand **"🔧 Diagnostic Options"** section
2. Check the box: **"🚨 Disable SSL Verification"**
3. Click **"Connect to Google Calendar"** again

### Step 4: Diagnose the Issue

**If it works with SSL bypass disabled:**
- Your issue is SSL interception by software on your system
- Common culprits:
  - **Antivirus**: Kaspersky, Avast, Norton, etc.
  - **Corporate proxy/firewall**
  - **VPN software**
  - **Parental control software**

**If it still fails:**
- The issue is not SSL-related
- Could be:
  - Network firewall blocking Google APIs
  - DNS issues
  - General connectivity problems

---

## Fixing SSL Interception Issues

### Solution 1: Antivirus SSL Scanning

**Temporarily disable SSL scanning in your antivirus:**

- **Kaspersky**: Settings → Additional → Network → Don't scan encrypted connections
- **Avast**: Settings → Protection → Core Shields → Web Shield → Configure → Untick "Enable HTTPS scanning"
- **Norton**: Settings → Firewall → Intrusion and Browser Protection → Turn off SSL Scanning
- **Windows Defender**: Generally doesn't intercept SSL

### Solution 2: VPN

- Disconnect from VPN temporarily
- Try the app again with SSL verification enabled
- If it works, your VPN was interfering

### Solution 3: Corporate Network

- If you're on a work/school network, they may block Google API access
- Try using:
  - Mobile hotspot
  - Home network
  - Public WiFi (if trusted)

### Solution 4: System Certificates

Update your system's SSL certificates:

```bash
# In your activated venv:
pip install --upgrade certifi
```

---

## Once the Issue is Identified

### If You Fixed the Root Cause:

1. **Test with SSL enabled:**
   - In the diagnostic app, uncheck "Disable SSL Verification"
   - Click "🔒 Test With SSL Enabled"
   - If it works → You're good!

2. **Switch back to normal app:**
   ```bash
   streamlit run calendar_export_app.py
   ```

### If You Can't Fix It (Not Recommended):

If you absolutely cannot resolve the SSL issue and need to use the app:

1. **Understand the risks:**
   - Your connection is not encrypted/verified
   - Vulnerable to man-in-the-middle attacks
   - Only use on trusted networks

2. **Use the diagnostic version:**
   - Keep "Disable SSL Verification" enabled
   - Only use when necessary
   - Don't enter sensitive data in other apps while this is active

---

## Common Scenarios

### Scenario 1: Antivirus Blocking

```
❌ Error: ssl.SSLError: [SSL: WRONG_VERSION_NUMBER]
✅ Works with SSL bypass enabled
→ Solution: Disable antivirus SSL scanning or add Python to exceptions
```

### Scenario 2: Corporate Proxy

```
❌ Error: ssl.SSLError or connection timeout
❌ Fails even with SSL bypass
→ Solution: Use different network or configure proxy settings
```

### Scenario 3: VPN Interference

```
❌ Error: Various SSL or connection errors
✅ Works with VPN disconnected
→ Solution: Disconnect VPN when using app, or configure VPN to allow Google APIs
```

### Scenario 4: Outdated Certificates

```
❌ Error: certificate verify failed
✅ Works after updating certifi
→ Solution: pip install --upgrade certifi
```

---

## Security Implications

### When SSL Verification is Disabled:

**What's at Risk:**
- Someone on your network could intercept your Google credentials
- Your calendar data could be read by attackers
- Token could be stolen and used by others

**When is it "Safe Enough":**
- On your home network (assuming it's secure)
- For testing/diagnostics only
- For a few minutes to identify the issue

**When is it NEVER safe:**
- Public WiFi (coffee shops, airports, etc.)
- Untrusted networks
- Long-term usage
- When handling sensitive calendar data

---

## Files

- `calendar_export_app.py` - **Normal version** (use this when possible)
- `calendar_export_app_diagnostic.py` - **This diagnostic version** (use only for troubleshooting)

---

## Still Having Issues?

If you've tried everything and still can't connect:

1. Check Python version: `python --version` (needs 3.7+)
2. Check network connectivity: Can you open https://calendar.google.com in a browser?
3. Check firewall: Is Python allowed through Windows Firewall?
4. Try a completely different network
5. Check system date/time is correct

---

## Reporting Issues

If you need to report the error, include:

1. The full error message
2. Whether SSL bypass worked or not
3. Your antivirus software
4. VPN status
5. Network type (home/corporate/public)
6. Windows version

---

**Remember: This diagnostic version is a temporary troubleshooting tool. Switch back to the normal `calendar_export_app.py` once your issue is resolved!**
