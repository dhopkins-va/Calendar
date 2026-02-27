"""Google Calendar API authentication.

Handles OAuth2 flow and token management. Requires a credentials.json file
downloaded from the Google Cloud Console (OAuth 2.0 Client ID for a
Desktop application with the Google Calendar API enabled).
"""

import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


def get_calendar_service():
    """Return an authenticated Google Calendar API service object."""
    creds = _load_credentials()

    if not creds or not creds.valid:
        creds = _refresh_or_authorize(creds)
        _save_credentials(creds)

    return build("calendar", "v3", credentials=creds)


def _load_credentials():
    """Load saved credentials from disk, if they exist."""
    if os.path.exists(TOKEN_PATH):
        return Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    return None


def _refresh_or_authorize(creds):
    """Refresh expired credentials or run the full OAuth flow."""
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        return creds

    if not os.path.exists(CREDENTIALS_PATH):
        print(
            "ERROR: credentials.json not found.\n"
            "Download it from the Google Cloud Console:\n"
            "  1. Go to https://console.cloud.google.com/apis/credentials\n"
            "  2. Create an OAuth 2.0 Client ID (Desktop application)\n"
            "  3. Enable the Google Calendar API\n"
            "  4. Download the JSON and save it as credentials.json in this directory",
            file=sys.stderr,
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    return flow.run_local_server(port=0)


def _save_credentials(creds):
    """Persist credentials to disk for future runs."""
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
