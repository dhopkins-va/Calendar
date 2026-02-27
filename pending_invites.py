"""Detect and report events where you haven't explicitly accepted or declined."""

from datetime import datetime, timezone


def find_pending_invites(events):
    """Return events where the user's response status is 'needsAction' or 'tentative'.

    These are invites where other attendees may expect you to show up
    but you haven't explicitly committed or declined.
    """
    pending = []
    for event in events:
        if event["status"] == "cancelled":
            continue
        if event["my_response"] in ("needsAction", "tentative"):
            pending.append(event)
    return pending


def find_past_unresponded(events):
    """Return events that already happened but were never accepted/declined.

    These are the most problematic — someone expected you and you never
    responded either way.
    """
    now = datetime.now(timezone.utc)
    return [
        e for e in find_pending_invites(events)
        if e["end"].tzinfo and e["end"] < now
        or not e["end"].tzinfo  # naive datetimes from all-day events
    ]


def find_upcoming_unresponded(events):
    """Return future events that still need a response."""
    now = datetime.now(timezone.utc)
    results = []
    for e in find_pending_invites(events):
        # Handle timezone-aware and naive datetimes
        if e["start"].tzinfo:
            if e["start"] > now:
                results.append(e)
        else:
            results.append(e)
    return results


def format_pending_report(events):
    """Return a human-readable report of pending invites."""
    all_pending = find_pending_invites(events)
    past = find_past_unresponded(events)
    upcoming = find_upcoming_unresponded(events)

    lines = []
    lines.append("=" * 60)
    lines.append("  PENDING INVITES — ACTION NEEDED")
    lines.append("=" * 60)
    lines.append("")
    lines.append(
        f"You have {len(all_pending)} event(s) without an explicit accept/decline."
    )
    lines.append("")

    if past:
        lines.append("-" * 60)
        lines.append(f"  PAST EVENTS — NEVER RESPONDED ({len(past)})")
        lines.append("  (These already happened without you accepting or declining)")
        lines.append("-" * 60)
        for e in past:
            lines.append(_format_event_line(e))
        lines.append("")

    if upcoming:
        lines.append("-" * 60)
        lines.append(f"  UPCOMING — NEEDS YOUR RESPONSE ({len(upcoming)})")
        lines.append("  (Others may expect you unless you explicitly decline)")
        lines.append("-" * 60)
        for e in upcoming:
            lines.append(_format_event_line(e))
        lines.append("")

    if not all_pending:
        lines.append("  All clear! Every invite has been explicitly accepted or declined.")
        lines.append("")

    return "\n".join(lines)


def _format_event_line(event):
    """Format a single event for the pending report."""
    start = event["start"]
    if event["is_all_day"]:
        date_str = start.strftime("%a %b %d (all day)")
    else:
        date_str = start.strftime("%a %b %d  %I:%M %p")

    duration = ""
    if not event["is_all_day"]:
        mins = event["duration_minutes"]
        if mins >= 60:
            duration = f" ({mins / 60:.1f}h)"
        else:
            duration = f" ({mins:.0f}m)"

    status_label = {
        "needsAction": "NO RESPONSE",
        "tentative": "TENTATIVE",
    }.get(event["my_response"], event["my_response"])

    attendee_count = ""
    if event["num_attendees"] > 0:
        attendee_count = f"  [{event['num_attendees']} attendees]"

    organizer = ""
    if event["organizer"] and not event["organizer_self"]:
        organizer = f"  from: {event['organizer']}"

    return (
        f"  [{status_label:^13}]  {date_str}{duration}\n"
        f"                  {event['summary']}{attendee_count}{organizer}\n"
        f"                  {event['html_link']}"
    )
