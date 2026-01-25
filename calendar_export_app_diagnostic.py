"""
Google Calendar to CSV Export - Streamlit App (DIAGNOSTIC VERSION)
A single-file application to export Google Calendar events to CSV with filtering and type mapping.

**WARNING**: This diagnostic version includes SSL verification bypass options for troubleshooting.
Only use this version for diagnosing connectivity issues. Do not use in production.
"""

import streamlit as st
import os
import json
import ssl
import certifi
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Google Calendar API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httplib2
from google_auth_httplib2 import AuthorizedHttp

# Global flag for SSL bypass
_ssl_bypass_enabled = False

# Google Calendar API scope (readonly)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Settings file for persistence
SETTINGS_FILE = 'app_settings.json'

# Google Calendar color mapping (colorId to name)
CALENDAR_COLORS = {
    '1': 'Lavender',
    '2': 'Sage',
    '3': 'Grape',
    '4': 'Flamingo',
    '5': 'Banana',
    '6': 'Tangerine',
    '7': 'Peacock',
    '8': 'Graphite',
    '9': 'Blueberry',
    '10': 'Basil',
    '11': 'Tomato'
}

# Color names in order for UI display
COLOR_NAMES = ['Lavender', 'Sage', 'Grape', 'Flamingo', 'Banana', 'Tangerine',
               'Peacock', 'Graphite', 'Blueberry', 'Basil', 'Tomato']

# Visual color representations (approximate hex codes)
COLOR_HEX = {
    'Lavender': '#7986CB',
    'Sage': '#33B679',
    'Grape': '#8E24AA',
    'Flamingo': '#E67C73',
    'Banana': '#F6BF26',
    'Tangerine': '#F4511E',
    'Peacock': '#039BE5',
    'Graphite': '#616161',
    'Blueberry': '#3F51B5',
    'Basil': '#0B8043',
    'Tomato': '#D50000'
}


def load_settings():
    """
    Load user settings from file. Returns default settings if file doesn't exist.
    """
    default_settings = {
        'selected_calendar_ids': [],
        'color_selections': {color: True for color in COLOR_NAMES},
        'color_type_mapping': {},
        'start_days_ago': 30,
        'csv_filename_template': 'calendar_export_{date}.csv'
    }

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved_settings = json.load(f)
                # Merge with defaults to handle new settings in updates
                default_settings.update(saved_settings)
        except Exception as e:
            st.warning(f"Could not load settings file: {e}. Using defaults.")

    return default_settings


def save_settings(settings):
    """
    Save user settings to file.
    """
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        st.error(f"Could not save settings: {e}")


def enable_ssl_bypass():
    """
    Globally disable SSL certificate verification.

    WARNING: This is EXTREMELY insecure and should ONLY be used for diagnostics!
    This modifies the global SSL context for the entire Python process.
    """
    global _ssl_bypass_enabled

    if not _ssl_bypass_enabled:
        # Store the original ssl context creation function
        if not hasattr(ssl, '_create_default_https_context_original'):
            ssl._create_default_https_context_original = ssl._create_default_https_context

        # Replace with unverified context
        ssl._create_default_https_context = ssl._create_unverified_context
        _ssl_bypass_enabled = True

        st.warning("⚠️ **GLOBAL SSL verification is DISABLED** - This is insecure! Only for diagnostics.")


def disable_ssl_bypass():
    """
    Re-enable SSL certificate verification.
    """
    global _ssl_bypass_enabled

    if _ssl_bypass_enabled and hasattr(ssl, '_create_default_https_context_original'):
        # Restore original ssl context creation function
        ssl._create_default_https_context = ssl._create_default_https_context_original
        _ssl_bypass_enabled = False

        st.success("✅ SSL verification has been re-enabled.")


def create_http_client(disable_ssl_verify=False):
    """
    Create HTTP client with optional SSL verification bypass.

    WARNING: Disabling SSL verification is insecure and should only be used for diagnostics!
    """
    if disable_ssl_verify:
        # Enable global SSL bypass
        enable_ssl_bypass()

        # Create HTTP client without SSL validation
        http = httplib2.Http(
            disable_ssl_certificate_validation=True,
            timeout=30
        )
        return http
    else:
        # Disable global SSL bypass if it was enabled
        disable_ssl_bypass()

        # Normal HTTP client with full SSL verification
        http = httplib2.Http(ca_certs=certifi.where(), timeout=30)
        return http


def authenticate_google(disable_ssl_verify=False):
    """
    Authenticate with Google Calendar API using OAuth 2.0.
    Returns the service object for API calls.

    Args:
        disable_ssl_verify: If True, bypasses SSL verification (INSECURE - diagnostics only!)
    """
    creds = None

    # Check if token.json exists (cached credentials)
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                st.warning(f"Token refresh failed: {e}. Re-authenticating...")
                # Delete invalid token and force re-auth
                if os.path.exists('token.json'):
                    os.remove('token.json')
                creds = None

        if not creds:
            if not os.path.exists('credentials.json'):
                return None, "credentials_missing"

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                return None, f"auth_error: {str(e)}"

        # Save credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Create HTTP client with optional SSL bypass
        http = create_http_client(disable_ssl_verify)

        # Create authorized HTTP client (combines credentials with HTTP client)
        authorized_http = AuthorizedHttp(creds, http=http)

        # Build service with authorized HTTP client
        service = build('calendar', 'v3', http=authorized_http)
        return service, "success"
    except Exception as e:
        return None, f"service_error: {str(e)}"


def get_calendars(service):
    """
    Fetch all accessible calendars.
    Returns list of calendar dicts with id, name, and color.
    """
    try:
        calendar_list = service.calendarList().list().execute()
        calendars = []

        for calendar in calendar_list.get('items', []):
            calendars.append({
                'id': calendar['id'],
                'name': calendar.get('summary', 'Unnamed Calendar'),
                'color': calendar.get('backgroundColor', '#FFFFFF')
            })

        return calendars, None
    except HttpError as e:
        return None, f"Error fetching calendars: {str(e)}"


def get_calendar_events(service, calendar_ids, start_datetime, end_datetime, selected_colors):
    """
    Fetch events from selected calendars within date range and matching selected colors.

    Args:
        service: Google Calendar API service object
        calendar_ids: List of calendar IDs to fetch from
        start_datetime: Start datetime object
        end_datetime: End datetime object
        selected_colors: List of color names to filter by

    Returns:
        List of event dictionaries with relevant fields
    """
    all_events = []

    # Convert selected color names to IDs
    color_ids = [k for k, v in CALENDAR_COLORS.items() if v in selected_colors]

    # Convert datetime to RFC3339 format
    time_min = start_datetime.isoformat() + 'Z'
    time_max = end_datetime.isoformat() + 'Z'

    for calendar_id in calendar_ids:
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            for event in events:
                # Get event color (could be event-specific or calendar default)
                event_color_id = event.get('colorId', None)

                # If no event-specific color, it inherits calendar color
                # For filtering purposes, we need to check if this event matches selected colors
                if event_color_id and event_color_id in color_ids:
                    all_events.append(event)
                elif not event_color_id and selected_colors:
                    # Event with no specific color - we'll include it with a note
                    # This handles the case where events inherit calendar color
                    all_events.append(event)

        except HttpError as e:
            st.warning(f"Error fetching events from calendar {calendar_id}: {str(e)}")
            continue

    return all_events


def format_uk_datetime(dt_string):
    """
    Convert ISO datetime string to UK format (DD/MM/YYYY HH:MM).
    Handles both datetime and date-only formats.
    """
    if not dt_string:
        return ""

    try:
        # Try parsing as datetime
        if 'T' in dt_string:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y %H:%M')
        else:
            # Date only (all-day event)
            dt = datetime.strptime(dt_string, '%Y-%m-%d')
            return dt.strftime('%d/%m/%Y')
    except Exception:
        return dt_string


def calculate_duration(start, end):
    """
    Calculate human-readable duration between start and end times.
    """
    if not start or not end:
        return ""

    try:
        # Handle all-day events
        start_dt_str = start.get('dateTime', start.get('date'))
        end_dt_str = end.get('dateTime', end.get('date'))

        if 'T' in start_dt_str:
            start_dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_dt_str.replace('Z', '+00:00'))
        else:
            start_dt = datetime.strptime(start_dt_str, '%Y-%m-%d')
            end_dt = datetime.strptime(end_dt_str, '%Y-%m-%d')

        duration = end_dt - start_dt

        # Format duration
        days = duration.days
        seconds = duration.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        return " ".join(parts) if parts else "0 minutes"
    except Exception:
        return ""


def get_event_color_name(event):
    """
    Get the color name for an event.
    """
    color_id = event.get('colorId', None)
    if color_id and color_id in CALENDAR_COLORS:
        return CALENDAR_COLORS[color_id]
    return "Default"


def generate_csv(events, color_type_mapping):
    """
    Generate CSV data from events list.

    Args:
        events: List of event dictionaries
        color_type_mapping: Dict mapping color names to type labels

    Returns:
        pandas DataFrame
    """
    rows = []

    for event in events:
        start = event.get('start', {})
        end = event.get('end', {})

        color_name = get_event_color_name(event)
        event_type = color_type_mapping.get(color_name, "")

        row = {
            'Event Name': event.get('summary', '(No title)'),
            'Event Description': event.get('description', ''),
            'Start DateTime': format_uk_datetime(start.get('dateTime', start.get('date'))),
            'End DateTime': format_uk_datetime(end.get('dateTime', end.get('date'))),
            'Duration': calculate_duration(start, end),
            'Created DateTime': format_uk_datetime(event.get('created', '')),
            'Colour': color_name,
            'Type': event_type
        }

        rows.append(row)

    return pd.DataFrame(rows)


def main():
    """Main Streamlit application."""

    st.set_page_config(
        page_title="Google Calendar to CSV Export",
        page_icon="📅",
        layout="wide"
    )

    st.title("📅 Google Calendar to CSV Export")
    st.markdown("Export your Google Calendar events to CSV with custom filtering and type mapping.")

    # Show global SSL bypass status prominently
    if _ssl_bypass_enabled:
        st.error("🚨 **GLOBAL SSL BYPASS ACTIVE** - All SSL verification is disabled! Use only for diagnostics.")

    # Load settings
    if 'settings' not in st.session_state:
        st.session_state.settings = load_settings()
    if 'settings_changed' not in st.session_state:
        st.session_state.settings_changed = False

    # Section A: Setup Instructions
    with st.expander("📖 First-Time Setup Instructions", expanded=False):
        st.markdown("""
        ### One-Time Google Cloud Setup (5-10 minutes)

        You need to create a Google Cloud project to access the Calendar API. Don't worry - it's **FREE** and you only do this once!

        #### Step-by-Step Guide:

        1. **Create a Google Cloud Project**
           - Go to [Google Cloud Console](https://console.cloud.google.com/)
           - Click "Select a project" → "New Project"
           - Give it a name (e.g., "Calendar Export") → Click "Create"

        2. **Enable Google Calendar API**
           - In your new project, go to "APIs & Services" → "Library"
           - Search for "Google Calendar API"
           - Click on it and press "Enable"

        3. **Create OAuth Credentials**
           - Go to "APIs & Services" → "Credentials"
           - Click "Create Credentials" → "OAuth client ID"
           - If prompted, configure OAuth consent screen:
             - Choose "External" → Click "Create"
             - Fill in App name (e.g., "Calendar Export"), User support email (your email)
             - Add your email under "Developer contact information" → Click "Save and Continue"
             - Skip scopes → Click "Save and Continue"
             - Add your email as a test user → Click "Save and Continue"
           - Back to Create OAuth client ID:
             - Choose "Desktop app" as Application type
             - Name it (e.g., "Calendar Export Desktop") → Click "Create"

        4. **Download Credentials**
           - Click "Download JSON" button
           - **Important:** Rename the downloaded file to `credentials.json`
           - Place `credentials.json` in the same folder as this app

        5. **Run the App**
           - Once `credentials.json` is in place, click "Connect to Google Calendar" below
           - A browser window will open asking you to authorize the app
           - After authorization, a `token.json` file will be created for future use

        #### Notes:
        - ✅ Completely FREE for personal use
        - ✅ No billing/credit card required for readonly calendar access
        - ✅ 1,000,000 API queries/day limit (more than enough!)
        - ✅ Your credentials are stored locally and never shared
        """)

    # Section B: Authentication
    st.header("🔐 Step 1: Authentication")

    # DIAGNOSTIC MODE WARNING
    st.error("⚠️ **DIAGNOSTIC VERSION** - This version includes SSL bypass options for troubleshooting only!")

    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'service' not in st.session_state:
        st.session_state.service = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'disable_ssl_verify' not in st.session_state:
        st.session_state.disable_ssl_verify = False

    # Check for credentials.json
    if not os.path.exists('credentials.json'):
        st.error("⚠️ **credentials.json not found!** Please follow the setup instructions above to create and download your credentials.")
        st.stop()

    # Diagnostic Mode Toggle
    with st.expander("🔧 Diagnostic Options (Troubleshooting SSL Errors)", expanded=not st.session_state.authenticated):
        st.warning("""
        **⚠️ WARNING: Security Risk!**

        If you're experiencing SSL errors, you can temporarily disable SSL verification to diagnose the issue.
        This is **INSECURE** and should only be used for testing!

        Common causes of SSL errors:
        - Antivirus software intercepting SSL connections
        - Corporate proxy/firewall
        - VPN interference
        - Outdated system certificates

        **Try this ONLY if you trust your network and are troubleshooting connectivity issues.**
        """)

        disable_ssl = st.checkbox(
            "🚨 Disable SSL Verification (INSECURE - Diagnostics Only)",
            value=st.session_state.disable_ssl_verify,
            help="Bypasses SSL certificate verification. Only use this temporarily to identify SSL issues."
        )

        # Apply or remove SSL bypass when setting changes
        if disable_ssl != st.session_state.disable_ssl_verify:
            st.session_state.disable_ssl_verify = disable_ssl
            if disable_ssl:
                enable_ssl_bypass()
            else:
                disable_ssl_bypass()

            # Force reconnection when SSL setting changes
            if st.session_state.get('authenticated', False):
                st.warning("⚠️ SSL setting changed. You need to reconnect for changes to take effect.")
                st.session_state.authenticated = False
                st.session_state.service = None
                st.session_state.user_email = None
                # Delete token to force fresh auth
                if os.path.exists('token.json'):
                    os.remove('token.json')

        if disable_ssl:
            st.error("⚠️ SSL Verification is DISABLED - Your connection is NOT secure!")
            st.info("This setting affects all network connections in this app session.")

    # Authentication button
    if not st.session_state.authenticated:
        if st.button("🔗 Connect to Google Calendar", type="primary"):
            with st.spinner("Authenticating..."):
                service, status = authenticate_google(disable_ssl_verify=st.session_state.disable_ssl_verify)

                if status == "success":
                    st.session_state.service = service
                    st.session_state.authenticated = True

                    # Get user email from primary calendar
                    try:
                        calendar = service.calendars().get(calendarId='primary').execute()
                        st.session_state.user_email = calendar.get('id', 'Connected')
                    except:
                        st.session_state.user_email = 'Connected'

                    st.rerun()
                else:
                    st.error(f"Authentication failed: {status}")
                    st.error("**Troubleshooting tips:**")
                    st.markdown("""
                    1. Try enabling 'Disable SSL Verification' in Diagnostic Options above
                    2. Disconnect from VPN if using one
                    3. Temporarily disable antivirus SSL scanning
                    4. Check if you're behind a corporate proxy
                    5. Delete `token.json` file and try again
                    """)
                    st.stop()
    else:
        st.success(f"✅ Connected as: {st.session_state.user_email}")
        if st.session_state.disable_ssl_verify:
            st.error("⚠️ You are connected with SSL verification DISABLED")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Reconnect"):
                # Clear token and reconnect
                if os.path.exists('token.json'):
                    os.remove('token.json')
                st.session_state.authenticated = False
                st.session_state.service = None
                st.session_state.user_email = None
                st.rerun()
        with col2:
            if st.button("🔒 Test With SSL Enabled"):
                st.session_state.disable_ssl_verify = False
                if os.path.exists('token.json'):
                    os.remove('token.json')
                st.session_state.authenticated = False
                st.session_state.service = None
                st.session_state.user_email = None
                st.info("Now reconnect with SSL verification enabled to test your connection.")
                st.rerun()

    if not st.session_state.authenticated:
        st.stop()

    # Section C: Calendar Selection
    st.header("📋 Step 2: Select Calendars")

    with st.spinner("Loading calendars..."):
        calendars, error = get_calendars(st.session_state.service)

    if error:
        st.error(error)
        st.stop()

    if not calendars:
        st.warning("No calendars found in your account.")
        st.stop()

    # Select/Deselect All buttons for calendars
    st.markdown("Select which calendars to export from:")
    cal_col1, cal_col2, cal_col3 = st.columns([1, 1, 4])

    with cal_col1:
        if st.button("✓ Select All Calendars"):
            for calendar in calendars:
                st.session_state[f"cal_{calendar['id']}"] = True
            st.session_state.settings['selected_calendar_ids'] = [cal['id'] for cal in calendars]
            st.session_state.settings_changed = True
            st.rerun()

    with cal_col2:
        if st.button("✗ Deselect All Calendars"):
            for calendar in calendars:
                st.session_state[f"cal_{calendar['id']}"] = False
            st.session_state.settings['selected_calendar_ids'] = []
            st.session_state.settings_changed = True
            st.rerun()

    # Initialize calendar checkboxes with saved settings
    saved_calendar_ids = st.session_state.settings.get('selected_calendar_ids', [])

    # Display calendars with checkboxes
    selected_calendar_ids = []
    cols = st.columns(2)
    for idx, calendar in enumerate(calendars):
        col = cols[idx % 2]
        with col:
            # Use saved setting if available, otherwise default to True
            default_value = calendar['id'] in saved_calendar_ids if saved_calendar_ids else True

            if st.checkbox(
                calendar['name'],
                value=default_value,
                key=f"cal_{calendar['id']}"
            ):
                selected_calendar_ids.append(calendar['id'])

    # Save calendar selections
    if set(selected_calendar_ids) != set(st.session_state.settings.get('selected_calendar_ids', [])):
        st.session_state.settings['selected_calendar_ids'] = selected_calendar_ids
        st.session_state.settings_changed = True

    if not selected_calendar_ids:
        st.warning("Please select at least one calendar.")
        st.stop()

    # Section D: Date & Time Range Filter
    st.header("📅 Step 3: Date & Time Range")

    col1, col2 = st.columns(2)

    # Use saved start_days_ago setting
    saved_days_ago = st.session_state.settings.get('start_days_ago', 30)

    with col1:
        st.subheader("Start")
        start_date = st.date_input(
            "Date",
            value=datetime.now().date() - timedelta(days=saved_days_ago),
            key="start_date"
        )
        start_time = st.time_input(
            "Time",
            value=datetime.min.time(),
            key="start_time"
        )

    with col2:
        st.subheader("End")
        end_date = st.date_input(
            "Date",
            value=datetime.now().date(),
            key="end_date"
        )
        end_time = st.time_input(
            "Time",
            value=datetime.max.time().replace(microsecond=0),
            key="end_time"
        )

    # Combine date and time
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    if end_datetime <= start_datetime:
        st.error("End date/time must be after start date/time!")
        st.stop()

    # Section E: Colour Filter & Type Mapping
    st.header("🎨 Step 4: Colour Filter & Type Mapping")
    st.markdown("Select which colours to export and optionally assign type labels:")

    # Select/Deselect All buttons for colours
    color_btn_col1, color_btn_col2, color_btn_col3 = st.columns([1, 1, 4])

    with color_btn_col1:
        if st.button("✓ Select All Colours"):
            new_selections = {color: True for color in COLOR_NAMES}
            st.session_state.settings['color_selections'] = new_selections
            st.session_state.settings_changed = True
            # Update session state for immediate UI feedback
            for color in COLOR_NAMES:
                st.session_state[f"color_checkbox_{color}"] = True
            st.rerun()

    with color_btn_col2:
        if st.button("✗ Deselect All Colours"):
            new_selections = {color: False for color in COLOR_NAMES}
            st.session_state.settings['color_selections'] = new_selections
            st.session_state.settings_changed = True
            # Update session state for immediate UI feedback
            for color in COLOR_NAMES:
                st.session_state[f"color_checkbox_{color}"] = False
            st.rerun()

    # Initialize color selections and type mappings from saved settings
    saved_color_selections = st.session_state.settings.get('color_selections', {color: True for color in COLOR_NAMES})
    saved_color_type_mapping = st.session_state.settings.get('color_type_mapping', {})

    # Track current selections and mappings
    current_color_selections = {}
    current_color_type_mapping = {}

    # Display all 11 colors in a grid
    for i in range(0, len(COLOR_NAMES), 2):
        col1, col2 = st.columns(2)

        for j, col in enumerate([col1, col2]):
            if i + j < len(COLOR_NAMES):
                color_name = COLOR_NAMES[i + j]
                with col:
                    with st.container():
                        subcol1, subcol2, subcol3 = st.columns([0.3, 0.3, 0.4])

                        with subcol1:
                            # Color indicator
                            st.markdown(
                                f"<div style='background-color: {COLOR_HEX[color_name]}; "
                                f"width: 30px; height: 30px; border-radius: 5px; margin-top: 5px;'></div>",
                                unsafe_allow_html=True
                            )

                        with subcol2:
                            # Checkbox to include color
                            include = st.checkbox(
                                color_name,
                                value=saved_color_selections.get(color_name, True),
                                key=f"color_checkbox_{color_name}"
                            )
                            current_color_selections[color_name] = include

                        with subcol3:
                            # Type label input
                            type_label = st.text_input(
                                "Type",
                                value=saved_color_type_mapping.get(color_name, ""),
                                key=f"type_{color_name}",
                                label_visibility="collapsed",
                                placeholder="e.g., positive"
                            )
                            current_color_type_mapping[color_name] = type_label

    # Save color selections and type mappings if changed
    if current_color_selections != st.session_state.settings.get('color_selections', {}):
        st.session_state.settings['color_selections'] = current_color_selections
        st.session_state.settings_changed = True

    if current_color_type_mapping != st.session_state.settings.get('color_type_mapping', {}):
        st.session_state.settings['color_type_mapping'] = current_color_type_mapping
        st.session_state.settings_changed = True

    selected_colors = [color for color, selected in current_color_selections.items() if selected]

    if not selected_colors:
        st.warning("Please select at least one colour to export.")
        st.stop()

    # Section F: Export Settings
    st.header("💾 Step 5: Export Settings")

    # Use saved filename template
    saved_template = st.session_state.settings.get('csv_filename_template', 'calendar_export_{date}.csv')
    default_filename = saved_template.replace('{date}', datetime.now().strftime('%Y-%m-%d'))

    csv_filename = st.text_input(
        "CSV Filename",
        value=default_filename,
        help="Enter the desired filename for the CSV export"
    )

    # Ensure .csv extension
    if not csv_filename.endswith('.csv'):
        csv_filename += '.csv'

    # Export button
    if st.button("📥 Export to CSV", type="primary"):
        with st.spinner("Fetching events..."):
            events = get_calendar_events(
                st.session_state.service,
                selected_calendar_ids,
                start_datetime,
                end_datetime,
                selected_colors
            )

        if not events:
            st.warning("No events found matching your criteria.")
        else:
            # Generate CSV
            df = generate_csv(events, current_color_type_mapping)

            # Section G: Results/Download
            st.success(f"✅ Found {len(events)} event(s)")

            # Preview
            st.subheader("Preview (first 10 rows)")
            st.dataframe(df.head(10), use_container_width=True)

            # Download button
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=csv_filename,
                mime="text/csv",
                type="primary"
            )

            # Show full statistics
            st.subheader("Export Statistics")
            st.write(f"- Total events: {len(events)}")
            st.write(f"- Date range: {start_datetime.strftime('%d/%m/%Y %H:%M')} to {end_datetime.strftime('%d/%m/%Y %H:%M')}")
            st.write(f"- Selected calendars: {len(selected_calendar_ids)}")
            st.write(f"- Selected colours: {', '.join(selected_colors)}")

    # Save settings to file if changed
    if st.session_state.settings_changed:
        save_settings(st.session_state.settings)
        st.session_state.settings_changed = False


if __name__ == "__main__":
    main()
