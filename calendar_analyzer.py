#!/usr/bin/env python3
"""Google Calendar Analyzer — understand how your time is spent and catch unanswered invites.

Usage:
    python calendar_analyzer.py                # Full report (2-week window)
    python calendar_analyzer.py --weeks 4      # Analyze 4 weeks back/forward
    python calendar_analyzer.py --pending      # Only show pending invites
    python calendar_analyzer.py --time         # Only show time analysis
    python calendar_analyzer.py --all-calendars  # Include all calendars
"""

import argparse
import sys

from auth import get_calendar_service
from fetch_events import fetch_all_calendar_events, fetch_events
from analyze import analyze_time, format_time_report, load_categories
from pending_invites import format_pending_report


def main():
    parser = argparse.ArgumentParser(
        description="Analyze your Google Calendar: time breakdown and pending invites."
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=2,
        help="Number of weeks to look back and forward (default: 2)",
    )
    parser.add_argument(
        "--pending",
        action="store_true",
        help="Only show pending invites report",
    )
    parser.add_argument(
        "--time",
        action="store_true",
        help="Only show time analysis report",
    )
    parser.add_argument(
        "--all-calendars",
        action="store_true",
        help="Analyze all calendars, not just the primary one",
    )
    args = parser.parse_args()

    show_all = not args.pending and not args.time

    print("Authenticating with Google Calendar...")
    service = get_calendar_service()

    days = args.weeks * 7
    print(f"Fetching events ({args.weeks} weeks back and forward)...")

    if args.all_calendars:
        events, calendars = fetch_all_calendar_events(
            service, days_back=days, days_forward=days
        )
        print(f"Found {len(events)} events across {len(calendars)} calendars.\n")
    else:
        events = fetch_events(service, days_back=days, days_forward=days)
        print(f"Found {len(events)} events.\n")

    if show_all or args.time:
        categories = load_categories()
        analysis = analyze_time(events, categories)
        print(format_time_report(analysis, args.weeks))

    if show_all or args.pending:
        print(format_pending_report(events))

    if show_all:
        _print_tips(events)


def _print_tips(events):
    """Print actionable suggestions based on the data."""
    from pending_invites import find_upcoming_unresponded

    upcoming = find_upcoming_unresponded(events)

    lines = []
    lines.append("=" * 60)
    lines.append("  SUGGESTIONS")
    lines.append("=" * 60)
    lines.append("")

    if upcoming:
        lines.append(
            f"  -> You have {len(upcoming)} upcoming event(s) without a response."
        )
        lines.append(
            "     Go through each one and explicitly Accept or Decline."
        )
        lines.append(
            "     This prevents the ambiguity where people expect you to attend."
        )
        lines.append("")

    lines.append("  -> Customize categories.json to match your actual meeting types.")
    lines.append("     This makes the time breakdown more meaningful for your role.")
    lines.append("")
    lines.append("  -> Run this weekly to stay on top of invite hygiene:")
    lines.append("       python calendar_analyzer.py --weeks 1")
    lines.append("")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
