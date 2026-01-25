"""
Google Calendar to CSV Export - Streamlit App
A single-file application to export Google Calendar events to CSV with filtering and type mapping.
"""

import streamlit as st
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Google Calendar API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Calendar API scope (readonly)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

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


def authenticate_google():
    """
    Authenticate with Google Calendar API using OAuth 2.0.
    Returns the service object for API calls.
    """
    creds = None

    # Check if token.json exists (cached credentials)
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
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
        service = build('calendar', 'v3', credentials=creds)
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

    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'service' not in st.session_state:
        st.session_state.service = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None

    # Check for credentials.json
    if not os.path.exists('credentials.json'):
        st.error("⚠️ **credentials.json not found!** Please follow the setup instructions above to create and download your credentials.")
        st.stop()

    # Authentication button
    if not st.session_state.authenticated:
        if st.button("🔗 Connect to Google Calendar", type="primary"):
            with st.spinner("Authenticating..."):
                service, status = authenticate_google()

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
                    st.stop()
    else:
        st.success(f"✅ Connected as: {st.session_state.user_email}")
        if st.button("🔄 Reconnect"):
            # Clear token and reconnect
            if os.path.exists('token.json'):
                os.remove('token.json')
            st.session_state.authenticated = False
            st.session_state.service = None
            st.session_state.user_email = None
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

    # Display calendars with checkboxes
    st.markdown("Select which calendars to export from:")
    selected_calendar_ids = []

    cols = st.columns(2)
    for idx, calendar in enumerate(calendars):
        col = cols[idx % 2]
        with col:
            if st.checkbox(
                calendar['name'],
                value=True,
                key=f"cal_{calendar['id']}"
            ):
                selected_calendar_ids.append(calendar['id'])

    if not selected_calendar_ids:
        st.warning("Please select at least one calendar.")
        st.stop()

    # Section D: Date & Time Range Filter
    st.header("📅 Step 3: Date & Time Range")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Start")
        start_date = st.date_input(
            "Date",
            value=datetime.now().date() - timedelta(days=30),
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

    # Initialize session state for color selections and type mappings
    if 'color_selections' not in st.session_state:
        st.session_state.color_selections = {color: True for color in COLOR_NAMES}
    if 'color_type_mapping' not in st.session_state:
        st.session_state.color_type_mapping = {}

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
                                value=st.session_state.color_selections.get(color_name, True),
                                key=f"color_checkbox_{color_name}"
                            )
                            st.session_state.color_selections[color_name] = include

                        with subcol3:
                            # Type label input
                            type_label = st.text_input(
                                "Type",
                                value=st.session_state.color_type_mapping.get(color_name, ""),
                                key=f"type_{color_name}",
                                label_visibility="collapsed",
                                placeholder="e.g., positive"
                            )
                            st.session_state.color_type_mapping[color_name] = type_label

    selected_colors = [color for color, selected in st.session_state.color_selections.items() if selected]

    if not selected_colors:
        st.warning("Please select at least one colour to export.")
        st.stop()

    # Section F: Export Settings
    st.header("💾 Step 5: Export Settings")

    default_filename = f"calendar_export_{datetime.now().strftime('%Y-%m-%d')}.csv"
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
            df = generate_csv(events, st.session_state.color_type_mapping)

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


if __name__ == "__main__":
    main()
