"""Fetch and parse events from Google Calendar."""

from datetime import datetime, timedelta, timezone


def fetch_events(service, days_back=14, days_forward=14, calendar_id="primary"):
    """Fetch events from a date range around today.

    Returns a list of event dicts with normalized fields.
    """
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days_back)).isoformat()
    time_max = (now + timedelta(days=days_forward)).isoformat()

    raw_events = []
    page_token = None

    while True:
        resp = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        )
        raw_events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return [_normalize(e) for e in raw_events]


def fetch_all_calendar_events(service, days_back=14, days_forward=14):
    """Fetch events from all visible calendars."""
    calendars = _list_calendars(service)
    all_events = []
    for cal in calendars:
        events = fetch_events(
            service,
            days_back=days_back,
            days_forward=days_forward,
            calendar_id=cal["id"],
        )
        for e in events:
            e["calendar_name"] = cal["summary"]
        all_events.extend(events)

    all_events.sort(key=lambda e: e["start"])
    return all_events, calendars


def _list_calendars(service):
    """List all calendars the user has access to."""
    result = []
    page_token = None
    while True:
        resp = (
            service.calendarList().list(pageToken=page_token).execute()
        )
        result.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return result


def _normalize(event):
    """Convert a raw API event into a simpler dict."""
    start_raw = event.get("start", {})
    end_raw = event.get("end", {})

    # All-day events use "date", timed events use "dateTime"
    is_all_day = "date" in start_raw and "dateTime" not in start_raw

    if is_all_day:
        start = datetime.fromisoformat(start_raw["date"])
        end = datetime.fromisoformat(end_raw["date"])
    else:
        start = datetime.fromisoformat(start_raw.get("dateTime", start_raw.get("date")))
        end = datetime.fromisoformat(end_raw.get("dateTime", end_raw.get("date")))

    duration_minutes = (end - start).total_seconds() / 60

    my_status = _my_response_status(event)

    return {
        "id": event.get("id", ""),
        "summary": event.get("summary", "(no title)"),
        "start": start,
        "end": end,
        "duration_minutes": duration_minutes,
        "is_all_day": is_all_day,
        "status": event.get("status", "confirmed"),
        "my_response": my_status,
        "organizer": event.get("organizer", {}).get("email", ""),
        "organizer_self": event.get("organizer", {}).get("self", False),
        "attendees": event.get("attendees", []),
        "num_attendees": len(event.get("attendees", [])),
        "recurring": event.get("recurringEventId") is not None,
        "html_link": event.get("htmlLink", ""),
        "calendar_name": "",
    }


def _my_response_status(event):
    """Determine the authenticated user's response status for an event."""
    for attendee in event.get("attendees", []):
        if attendee.get("self"):
            return attendee.get("responseStatus", "needsAction")
    # If no attendees list or user isn't in it, they're the sole
    # organizer — treat as accepted.
    return "accepted"
