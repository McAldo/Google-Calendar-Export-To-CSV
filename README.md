# Google Calendar to CSV Export

A Streamlit web application that exports Google Calendar events to CSV with advanced filtering and custom type mapping based on event colours.

## Features

- 📅 Export events from multiple Google Calendars
- 🎨 Filter events by colour (all 11 Google Calendar colours supported)
- 📊 Custom type mapping based on event colours
- 🕐 Date and time range filtering (UK format: DD/MM/YYYY HH:MM)
- 💾 Customizable CSV filename
- 🔐 Secure OAuth 2.0 authentication
- 📝 Full event details including descriptions, creation date, and duration

## CSV Output Fields

The exported CSV includes the following columns:

1. **Event Name** - Event title/summary
2. **Event Description** - Full description text
3. **Start DateTime** - DD/MM/YYYY HH:MM format
4. **End DateTime** - DD/MM/YYYY HH:MM format
5. **Duration** - Human-readable duration (e.g., "2 hours 30 minutes")
6. **Created DateTime** - When the event was created
7. **Colour** - Event colour name (Flamingo, Banana, etc.)
8. **Type** - Custom label based on your colour mapping

## Installation

### 1. Clone or Download

```bash
cd GoogleCalendar_toExcel
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Google Cloud Setup (One-Time, ~5-10 minutes)

**This is required to access the Google Calendar API. It's completely FREE for personal use!**

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name (e.g., "Calendar Export")
4. Click **"Create"**

### Step 2: Enable Google Calendar API

1. Make sure your new project is selected
2. Go to **"APIs & Services"** → **"Library"**
3. Search for **"Google Calendar API"**
4. Click on it and press **"Enable"**

### Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Choose **"External"** user type → Click **"Create"**
3. Fill in required fields:
   - **App name**: e.g., "Calendar Export"
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
4. Click **"Save and Continue"**
5. **Scopes**: Skip this (click "Save and Continue")
6. **Test users**: Add your email address → Click **"Save and Continue"**
7. Click **"Back to Dashboard"**

### Step 4: Create OAuth Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Choose **"Desktop app"** as Application type
4. Enter a name (e.g., "Calendar Export Desktop")
5. Click **"Create"**

### Step 5: Download Credentials

1. Click the **Download** button (⬇️) next to your newly created OAuth 2.0 Client ID
2. **IMPORTANT**: Rename the downloaded file to `credentials.json`
3. Place `credentials.json` in the **same folder** as `calendar_export_app.py`

## Usage

### 1. Run the Application

Make sure your virtual environment is activated, then:

```bash
streamlit run calendar_export_app.py
```

The app will open in your default web browser.

### 2. First-Time Authentication

1. Click **"Connect to Google Calendar"**
2. A browser window will open asking you to sign in to Google
3. Select your Google account
4. You may see a warning "Google hasn't verified this app" - this is normal for personal projects
   - Click **"Advanced"** → **"Go to [Your App Name] (unsafe)"**
5. Click **"Allow"** to grant calendar read permissions
6. The app will save your credentials in `token.json` for future use

### 3. Export Events

1. **Select Calendars**: Choose which calendars to export from
2. **Set Date Range**: Pick start and end dates/times (UK format)
3. **Configure Colours**:
   - Check which colours to include
   - Optionally assign type labels (e.g., Flamingo = "positive", Banana = "mixed")
4. **Export Settings**: Customize CSV filename if desired
5. Click **"Export to CSV"**
6. Preview the results and click **"Download CSV"**

## Example Type Mapping

You might want to categorize events by colour:

- **Flamingo** → "positive"
- **Banana** → "mixed"
- **Graphite** → "negative"
- **Blueberry** → "personal"
- **Peacock** → "work"

Leave any colour's type field empty if you don't want a specific label.

## Supported Google Calendar Colours

1. Lavender
2. Sage
3. Grape
4. Flamingo
5. Banana
6. Tangerine
7. Peacock
8. Graphite
9. Blueberry
10. Basil
11. Tomato

## Troubleshooting

### "credentials.json not found"

- Make sure you've completed the Google Cloud Setup
- Verify the file is named exactly `credentials.json` (not `credentials (1).json` or similar)
- Ensure it's in the same folder as `calendar_export_app.py`

### "Token has been expired or revoked"

- Delete `token.json` from the app folder
- Click "Reconnect" in the app
- Re-authenticate through the browser

### "This app isn't verified" warning

- This is normal for personal projects
- Click "Advanced" → "Go to [App Name] (unsafe)"
- Google shows this warning for apps not published publicly, but your app is safe since you created it

### No events found

- Check your date range includes events
- Verify you've selected the correct calendars
- Make sure at least one colour is selected
- Some events may not have explicit colours set

### Events missing colour information

- Events inherit the calendar's default colour if no specific colour is assigned
- You can assign colours to events in Google Calendar UI for better filtering

## Files Created

- `credentials.json` - Your OAuth credentials (DO NOT share or commit to git)
- `token.json` - Cached authentication token (DO NOT share or commit to git)
- `*.csv` - Your exported event files

## Privacy & Security

- All authentication happens locally on your machine
- Your credentials never leave your computer
- The app only requests **read-only** access to your calendar
- `credentials.json` and `token.json` are excluded from git via `.gitignore`

## API Quotas

Google Calendar API free tier includes:
- **1,000,000 queries/day** - Far more than you'll ever need for personal use
- No credit card or billing account required for readonly access

## Requirements

- Python 3.7+
- Internet connection for Google API access
- Google account with calendar access

## License

Free to use for personal and commercial purposes.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the in-app setup instructions (expandable section)
3. Verify your Google Cloud project is configured correctly

---

**Enjoy exporting your calendar events!** 📅✨
