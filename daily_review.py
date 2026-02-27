"""Daily review: what's on for tomorrow and what needs a response."""

from datetime import datetime, timedelta, timezone

from pending_invites import find_pending_invites


def get_tomorrow_range():
    """Return (start, end) datetimes for tomorrow in UTC."""
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_after = tomorrow + timedelta(days=1)
    return tomorrow, day_after


def filter_events_for_day(events, day_start, day_end):
    """Return events that overlap with the given day."""
    result = []
    for e in events:
        start = e["start"]
        end = e["end"]
        # For timezone-naive (all-day) events, compare dates directly
        if not start.tzinfo:
            if start.date() < day_end.date() and end.date() > day_start.date():
                result.append(e)
        else:
            if start < day_end and end > day_start:
                result.append(e)
    return result


def format_daily_review(events):
    """Generate the daily review report for tomorrow."""
    tomorrow, day_after = get_tomorrow_range()
    tomorrow_events = filter_events_for_day(events, tomorrow, day_after)

    # Separate all-day and timed events
    all_day = [e for e in tomorrow_events if e["is_all_day"]]
    timed = [e for e in tomorrow_events if not e["is_all_day"]]
    timed.sort(key=lambda e: e["start"])

    # Find pending invites among tomorrow's events
    pending = [e for e in tomorrow_events if e["my_response"] in ("needsAction", "tentative")]

    total_meeting_hours = sum(e["duration_minutes"] for e in timed) / 60

    day_label = tomorrow.strftime("%A, %B %d")

    lines = []
    lines.append("=" * 60)
    lines.append(f"  DAILY REVIEW — {day_label}")
    lines.append("=" * 60)
    lines.append("")

    lines.append(f"  {len(timed)} timed event(s)  |  {total_meeting_hours:.1f}h of meetings")
    if pending:
        lines.append(f"  {len(pending)} event(s) still need your accept/decline!")
    lines.append("")

    # All-day events
    if all_day:
        lines.append("-" * 60)
        lines.append("  ALL DAY")
        lines.append("-" * 60)
        for e in all_day:
            flag = _response_flag(e)
            lines.append(f"  {flag} {e['summary']}")
        lines.append("")

    # Timed schedule
    if timed:
        lines.append("-" * 60)
        lines.append("  SCHEDULE")
        lines.append("-" * 60)

        # Show free gaps between meetings
        prev_end = None
        for e in timed:
            if prev_end and e["start"].tzinfo and prev_end.tzinfo:
                gap_minutes = (e["start"] - prev_end).total_seconds() / 60
                if gap_minutes >= 15:
                    gap_str = _format_duration(gap_minutes)
                    lines.append(f"  {'':>13}  ~~ {gap_str} free ~~")

            time_str = e["start"].strftime("%I:%M %p")
            dur = _format_duration(e["duration_minutes"])
            flag = _response_flag(e)
            attendees = ""
            if e["num_attendees"] > 1:
                attendees = f"  [{e['num_attendees']}p]"
            lines.append(f"  {time_str:>8}  {dur:>6}  {flag} {e['summary']}{attendees}")

            prev_end = e["end"]
        lines.append("")
    else:
        lines.append("  No timed events tomorrow — clear calendar!\n")

    # Action items
    if pending:
        lines.append("-" * 60)
        lines.append("  ACTION: RESPOND TO THESE BEFORE TOMORROW")
        lines.append("-" * 60)
        for e in pending:
            time_str = e["start"].strftime("%I:%M %p") if not e["is_all_day"] else "all day"
            status = "NO RESPONSE" if e["my_response"] == "needsAction" else "TENTATIVE"
            organizer = ""
            if e["organizer"] and not e["organizer_self"]:
                organizer = f"  (from {e['organizer']})"
            lines.append(f"  [{status}] {time_str}  {e['summary']}{organizer}")
            if e["html_link"]:
                lines.append(f"             {e['html_link']}")
        lines.append("")

    return "\n".join(lines)


def _response_flag(event):
    """Return a text flag based on the user's response status."""
    flags = {
        "accepted": "[ok]",
        "declined": "[no]",
        "tentative": "[??]",
        "needsAction": "[!!]",
    }
    return flags.get(event["my_response"], "    ")


def _format_duration(minutes):
    """Format minutes as a compact duration string."""
    if minutes >= 60:
        h = int(minutes // 60)
        m = int(minutes % 60)
        return f"{h}h{m:02d}m" if m else f"{h}h"
    return f"{int(minutes)}m"
