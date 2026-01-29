"""
Google Calendar to CSV Export - Streamlit App
A single-file application to export Google Calendar events to CSV with filtering and type mapping.

Includes SSL verification bypass option for Windows compatibility issues.
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

# Allow http://localhost for OAuth redirect (safe for desktop app flow)
# This is needed for manual OAuth flow on cloud platforms
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

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
               'Peacock', 'Graphite', 'Blueberry', 'Basil', 'Tomato', 'Default']

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
    'Tomato': '#D50000',
    'Default': '#A4BDFC'  # Light blue - calendar default color
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


def setup_credentials_from_secrets():
    """
    Create credentials.json from Streamlit secrets if running on Streamlit Cloud.
    This allows the app to work in the cloud without committing credentials to git.
    """
    try:
        # Check if running on Streamlit Cloud (secrets available)
        if hasattr(st, 'secrets') and 'google_credentials' in st.secrets:
            # Get redirect_uris - handle both string and list formats
            redirect_uris_raw = st.secrets["google_credentials"]["redirect_uris"]

            # If it's a string, convert to list; if already a list, use as-is
            if isinstance(redirect_uris_raw, str):
                redirect_uris = [redirect_uris_raw]
            else:
                redirect_uris = list(redirect_uris_raw)

            # Determine client type: 'web' or 'installed' (desktop)
            # Default to 'installed' for backward compatibility
            client_type = st.secrets["google_credentials"].get("client_type", "installed")

            # Create credentials.json from secrets
            credentials_data = {
                client_type: {
                    "client_id": st.secrets["google_credentials"]["client_id"],
                    "project_id": st.secrets["google_credentials"]["project_id"],
                    "auth_uri": st.secrets["google_credentials"]["auth_uri"],
                    "token_uri": st.secrets["google_credentials"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["google_credentials"]["auth_provider_x509_cert_url"],
                    "client_secret": st.secrets["google_credentials"]["client_secret"],
                    "redirect_uris": redirect_uris
                }
            }

            # Write to credentials.json
            with open('credentials.json', 'w') as f:
                json.dump(credentials_data, f)

            st.success(f"✅ Loaded {client_type} credentials from Streamlit secrets")
            return True
    except Exception as e:
        st.error(f"Error loading credentials from secrets: {e}")
        st.info("Secrets structure detected: " + str(list(st.secrets.keys()) if hasattr(st, 'secrets') else "No secrets"))

    return False


def enable_ssl_bypass():
    """
    Globally disable SSL certificate verification for Windows compatibility.
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


def is_running_on_cloud():
    """Check if running on Streamlit Cloud or similar environment."""
    # Check for common cloud environment indicators
    return (
        os.environ.get('STREAMLIT_SHARING_MODE') is not None or
        os.environ.get('HOSTNAME', '').startswith('streamlit') or
        not os.path.exists('/usr/bin/xdg-open')  # No display available
    )


def get_oauth_client_type():
    """
    Determine OAuth client type from credentials.json.
    Returns: 'web' or 'installed'
    """
    try:
        if os.path.exists('credentials.json'):
            with open('credentials.json', 'r') as f:
                creds_data = json.load(f)
            if 'web' in creds_data:
                return 'web'
            elif 'installed' in creds_data:
                return 'installed'
    except:
        pass
    return 'installed'  # Default


def get_streamlit_app_url():
    """
    Get the current Streamlit app URL for OAuth redirects.
    Returns the full URL including protocol and domain.
    """
    try:
        # Try to get from Streamlit's session info
        from streamlit.web.server import Server
        from streamlit.runtime import get_instance

        runtime = get_instance()
        if runtime and hasattr(runtime, '_session_mgr'):
            # Get the first session's client
            sessions = list(runtime._session_mgr._sessions.values())
            if sessions:
                session = sessions[0]
                if hasattr(session, '_client') and session._client:
                    return session._client.request.host_url.rstrip('/')
    except:
        pass

    # Fallback: construct from environment or use placeholder
    if os.environ.get('STREAMLIT_SHARING_MODE'):
        # On Streamlit Cloud, construct from repo info if available
        return "https://your-app.streamlit.app"  # User will need to update this

    return "http://localhost:8501"


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
                # Determine OAuth client type
                client_type = get_oauth_client_type()

                # Check if running on cloud (no browser available)
                if is_running_on_cloud():
                    # Load credentials to determine flow type
                    with open('credentials.json', 'r') as f:
                        creds_data = json.load(f)

                    # Check for OAuth callback in query parameters (for web clients)
                    query_params = st.query_params

                    # Debug info (temporary)
                    with st.expander("🔍 OAuth Debug Info"):
                        st.write(f"Client type detected: {client_type}")
                        st.write(f"Query params present: {dict(query_params)}")
                        st.write(f"Has 'code' param: {'code' in query_params}")
                        if 'code' in query_params:
                            st.write(f"Code type: {type(query_params['code'])}")
                            st.write(f"Code value (first 30 chars): {str(query_params['code'])[:30]}")
                        st.write(f"OAuth flow in session: {'oauth_flow' in st.session_state}")
                        st.write(f"Session state keys: {list(st.session_state.keys())}")

                    if 'code' in query_params and client_type == 'web':
                        # Web OAuth callback - process automatically
                        st.info("🔄 OAuth callback detected! Processing...")

                        try:
                            # Recreate flow if not in session (session might be lost on redirect)
                            if 'oauth_flow' in st.session_state:
                                flow = st.session_state.oauth_flow
                                st.write("✓ Using flow from session state")
                            else:
                                # Recreate flow from credentials
                                st.warning("⚠️ OAuth flow not in session, recreating...")
                                from google_auth_oauthlib.flow import Flow

                                # CRITICAL: Must use same redirect_uri that was used for auth URL
                                redirect_uri = creds_data['web']['redirect_uris'][0]
                                st.write(f"✓ Using redirect_uri: {redirect_uri}")

                                flow = Flow.from_client_secrets_file(
                                    'credentials.json',
                                    scopes=SCOPES,
                                    redirect_uri=redirect_uri
                                )
                                # Set the state from the callback for CSRF validation
                                if 'state' in query_params:
                                    state_param = query_params['state']
                                    if isinstance(state_param, (list, tuple)):
                                        state_value = state_param[0]
                                    else:
                                        state_value = str(state_param)
                                    flow._state = state_value
                                    st.write(f"✓ Set state from callback: {state_value[:10]}...")

                            # Fetch token using the authorization code
                            # Streamlit query_params can return values directly or as lists depending on version
                            code_param = query_params['code']
                            if isinstance(code_param, (list, tuple)):
                                code_value = code_param[0]
                            else:
                                code_value = str(code_param)

                            st.info(f"Fetching token...")
                            st.write(f"✓ Code type: {type(code_param)}")
                            st.write(f"✓ Code value (first 30 chars): {code_value[:30]}...")
                            st.write(f"✓ Code length: {len(code_value)}")

                            flow.fetch_token(code=code_value)
                            creds = flow.credentials

                            st.success("✅ Token received! Saving credentials...")

                            # Clear OAuth flow and query params
                            if 'oauth_flow' in st.session_state:
                                del st.session_state.oauth_flow
                            st.query_params.clear()

                            st.success("✅ Authentication successful! Redirecting...")
                            # Don't show the auth UI again - we have creds now, skip to saving them
                        except Exception as e:
                            st.error(f"OAuth callback failed: {e}")
                            st.error(f"Full error: {repr(e)}")
                            import traceback
                            st.code(traceback.format_exc())
                            if 'oauth_flow' in st.session_state:
                                del st.session_state.oauth_flow
                            st.query_params.clear()
                            return None, f"auth_error: {str(e)}"

                    # Only show auth UI if we haven't just processed a callback
                    # If creds is set from callback above, skip this entire section
                    if not creds and 'oauth_flow' not in st.session_state:
                        if client_type == 'web':
                            # Web application OAuth flow
                            from google_auth_oauthlib.flow import Flow

                            # IMPORTANT: Always use the first redirect URI consistently
                            # Session state doesn't persist across external redirects, so we can't
                            # store which URI we used. Must use same URI for auth URL generation
                            # and token exchange.
                            redirect_uri = creds_data['web']['redirect_uris'][0]

                            flow = Flow.from_client_secrets_file(
                                'credentials.json',
                                scopes=SCOPES,
                                redirect_uri=redirect_uri
                            )
                            st.info(f"🌐 **Using Web OAuth flow** (redirect: {redirect_uri})")
                        else:
                            # Desktop (installed) application OAuth flow
                            redirect_uri = creds_data['installed']['redirect_uris'][0]
                            flow = InstalledAppFlow.from_client_secrets_file(
                                'credentials.json', SCOPES)
                            flow.redirect_uri = redirect_uri
                            st.info("🌐 **Using Desktop OAuth flow (manual)**")

                        # Generate authorization URL and store flow
                        auth_url, state = flow.authorization_url(
                            prompt='consent',
                            access_type='offline'
                        )
                        st.session_state.oauth_flow = flow
                        st.session_state.auth_url = auth_url
                        st.session_state.redirect_uri = redirect_uri
                    elif not creds:
                        # Retrieve existing flow from session (only if we don't have creds from callback)
                        flow = st.session_state.oauth_flow
                        auth_url = st.session_state.auth_url
                        redirect_uri = st.session_state.redirect_uri

                    # Display instructions based on client type (only if we don't have creds yet)
                    if not creds and client_type == 'web':
                        st.markdown(f"""
                        ### 🔐 Google Authentication

                        Click the button below to authorize the app. You'll be redirected back automatically.

                        [**🔓 Authorize with Google**]({auth_url})

                        After authorizing, you'll be redirected back to this page.
                        """)
                    else:
                        # Desktop client - manual copy/paste flow
                        st.markdown(f"""
                        ### Manual Authentication Steps:

                        1. Click this link to authorize: [**Open Google Authorization**]({auth_url})
                        2. Log in and authorize the app
                        3. You'll see "This site can't be reached" - **this is normal!**
                        4. Copy the **entire URL** from your browser's address bar
                        5. Paste it in the box below **exactly as copied** (keep http://, don't change to https://)

                        **Example URL to copy (keep http:// not https://):**
                        ```
                        http://localhost/?code=4/0AY0e...&scope=https://...
                        ```

                        ⚠️ **Important:** The URL must start with `http://localhost` (not `https://`)
                        """)

                    # Debug info (only show if we're in the auth flow, not after successful callback)
                    if not creds:
                        with st.expander("🔍 Debug Info"):
                            st.write(f"Client type: {client_type}")
                            if 'redirect_uri' in locals():
                                st.write(f"Using redirect_uri: `{redirect_uri}`")
                            st.write("If you see an error about redirect_uri, make sure this URL is added to your Google OAuth credentials.")

                    # For desktop clients, show text input for manual URL paste (only if we don't have creds yet)
                    if not creds and client_type == 'installed':
                        # Text input for the redirect URL
                        redirect_url = st.text_input(
                            "Paste the full redirect URL here:",
                            key="oauth_redirect_input",
                            placeholder="http://localhost/?code=..."
                        )

                        if redirect_url:
                            try:
                                # Show what we're processing
                                st.info(f"Processing URL: {redirect_url[:50]}...")

                                # Extract the authorization response from the URL
                                flow.fetch_token(authorization_response=redirect_url)
                                creds = flow.credentials

                                # Clear OAuth flow from session state
                                if 'oauth_flow' in st.session_state:
                                    del st.session_state.oauth_flow
                                if 'auth_url' in st.session_state:
                                    del st.session_state.auth_url

                                st.success("✅ Authentication successful!")
                            except Exception as e:
                                st.error(f"❌ Failed to process authorization URL")
                                st.error(f"**Error details:** {str(e)}")

                                # Provide helpful tips based on common errors
                                if "redirect_uri_mismatch" in str(e):
                                    st.warning("**Redirect URI mismatch!** Make sure you're using Desktop app credentials (not Web app) in your Streamlit secrets.")
                                elif "http" in str(e).lower() and "https" in str(e).lower():
                                    st.warning("**Protocol mismatch!** The URL should start with http:// (not https://)")

                                st.info("💡 **Troubleshooting:**")
                                st.markdown("""
                                1. Make sure you copied the **complete URL** from the browser (including http://)
                                2. The URL should start with `http://localhost` (not https)
                                3. Make sure you're using **Desktop app** credentials in Streamlit secrets
                                4. Try clicking the button below to restart
                                """)

                                if st.button("🔄 Clear and Restart Authentication"):
                                    if 'oauth_flow' in st.session_state:
                                        del st.session_state.oauth_flow
                                    if 'auth_url' in st.session_state:
                                        del st.session_state.auth_url
                                    st.rerun()
                                return None, f"auth_error: {str(e)}"
                        else:
                            # User hasn't pasted the URL yet
                            return None, "awaiting_auth"
                    elif not creds:
                        # Web client - just wait for OAuth callback (only if we don't have creds yet)
                        st.info("⏳ Waiting for you to authorize via the link above...")
                        return None, "awaiting_auth"
                else:
                    # Local environment - use browser-based flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)

            except Exception as e:
                return None, f"auth_error: {str(e)}"

        # Save credentials for next run
        if creds:
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

    # Convert datetime to RFC3339 format (treating as UTC)
    # Note: 'Z' suffix indicates UTC timezone
    time_min = start_datetime.isoformat() + 'Z'
    time_max = end_datetime.isoformat() + 'Z'

    for calendar_id in calendar_ids:
        try:
            # Fetch events with maxResults to ensure we get all events
            # showDeleted=False to exclude deleted events
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=2500,  # Google Calendar API max per request
                singleEvents=True,
                orderBy='startTime',
                showDeleted=False
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

    # Show global SSL bypass status
    if _ssl_bypass_enabled:
        st.info("ℹ️ SSL verification disabled (Windows compatibility mode)")

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

    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'service' not in st.session_state:
        st.session_state.service = None

    # IMPORTANT: Check for OAuth callback before checking authenticated status
    # If we detect an OAuth callback, clear authentication to force reprocessing
    query_params = st.query_params
    if 'code' in query_params and 'state' in query_params:
        st.info("🔄 OAuth callback detected - clearing old session...")
        st.session_state.authenticated = False
        st.session_state.service = None
        if 'user_email' in st.session_state:
            st.session_state.user_email = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'disable_ssl_verify' not in st.session_state:
        st.session_state.disable_ssl_verify = False

    # Setup credentials from Streamlit secrets if running on cloud
    setup_credentials_from_secrets()

    # Check for credentials.json
    if not os.path.exists('credentials.json'):
        st.error("⚠️ **credentials.json not found!** Please follow the setup instructions above to create and download your credentials.")
        st.stop()

    # Auto-enable SSL bypass on cloud (Linux servers have same httplib2 SSL issues)
    if is_running_on_cloud() and not st.session_state.disable_ssl_verify:
        st.session_state.disable_ssl_verify = True
        enable_ssl_bypass()

    # SSL Options
    with st.expander("🔧 SSL Options (for Windows compatibility)", expanded=not st.session_state.authenticated):
        st.info("""
        **Windows SSL Compatibility**

        If you're experiencing SSL connection errors (common on Windows), enable SSL bypass below.
        This works around Windows + Python SSL interception issues.

        **Note:** Only use on trusted networks (home/office). Safe for personal calendar data.
        """)

        disable_ssl = st.checkbox(
            "Disable SSL Verification (Windows compatibility)",
            value=st.session_state.disable_ssl_verify,
            help="Bypasses SSL certificate verification to work around Windows compatibility issues."
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
            st.info("ℹ️ SSL verification is disabled (Windows compatibility mode)")

    # Authentication button
    if not st.session_state.authenticated:
        # Try to authenticate (for cloud, this will show the manual OAuth UI)
        # Auto-enable SSL bypass on cloud (SSL issues with httplib2 on cloud servers)
        ssl_bypass_needed = is_running_on_cloud() or st.session_state.disable_ssl_verify
        service, status = authenticate_google(disable_ssl_verify=ssl_bypass_needed)

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
        elif status == "awaiting_auth":
            # User is in the middle of OAuth flow, instructions are shown above
            st.stop()
        elif status == "credentials_missing":
            st.error("⚠️ Credentials not properly configured!")
            st.stop()
        else:
            # Show error only for actual failures, not during OAuth flow
            st.error(f"Authentication failed: {status}")
            st.error("**Troubleshooting tips:**")
            st.markdown("""
            1. Make sure you pasted the complete URL including 'code='
            2. Try the authentication link again
            3. Check that your Google credentials are correctly configured in secrets
            """)
            st.stop()
    else:
        st.success(f"✅ Connected as: {st.session_state.user_email}")

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

    # Debug section to help identify date/cache issues
    with st.expander("🔍 Debug Info & Cache Control"):
        st.markdown("**Date Range Being Sent to Google Calendar API:**")
        st.code(f"""
Start: {start_datetime.isoformat()}Z (UTC)
End:   {end_datetime.isoformat()}Z (UTC)
        """)

        st.markdown("**Current System Time:**")
        st.write(f"Local time: {datetime.now()}")
        st.write(f"UTC time: {datetime.utcnow()}")

        st.markdown("**Cache Control:**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Clear Auth Token"):
                if os.path.exists('token.json'):
                    os.remove('token.json')
                    st.session_state.authenticated = False
                    st.session_state.service = None
                    st.success("Token cleared! Please reconnect.")
                    st.rerun()
        with col2:
            if st.button("🗑️ Reset All Settings"):
                if os.path.exists(SETTINGS_FILE):
                    os.remove(SETTINGS_FILE)
                    st.success("Settings reset! Page will reload.")
                    st.rerun()

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

            # Debug: Show date range of fetched events
            if events:
                event_dates = []
                for event in events:
                    start = event.get('start', {})
                    event_date_str = start.get('dateTime', start.get('date', ''))
                    if event_date_str:
                        event_dates.append(event_date_str)

                if event_dates:
                    st.write(f"- Earliest event: {event_dates[0]}")
                    st.write(f"- Latest event: {event_dates[-1]}")

    # Save settings to file if changed
    if st.session_state.settings_changed:
        save_settings(st.session_state.settings)
        st.session_state.settings_changed = False


if __name__ == "__main__":
    main()
