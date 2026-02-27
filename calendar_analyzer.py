#!/usr/bin/env python3
"""Google Calendar Analyzer — understand how your time is spent and catch unanswered invites.

Usage:
    python calendar_analyzer.py                    # Full report (2-week window)
    python calendar_analyzer.py daily              # What's on for tomorrow?
    python calendar_analyzer.py weekly             # Last week vs goals + week ahead
    python calendar_analyzer.py --weeks 4          # Analyze 4 weeks back/forward
    python calendar_analyzer.py --pending          # Only show pending invites
    python calendar_analyzer.py --time             # Only show time analysis
    python calendar_analyzer.py --all-calendars    # Include all calendars
    python calendar_analyzer.py --save             # Save a snapshot for later diffing
    python calendar_analyzer.py --save weekly       # Save with a label
    python calendar_analyzer.py --diff             # Diff current vs most recent snapshot
    python calendar_analyzer.py --diff snap1 snap2 # Diff two specific snapshots
    python calendar_analyzer.py --list-snapshots   # List all saved snapshots
"""

import argparse
import sys

from auth import get_calendar_service
from fetch_events import fetch_all_calendar_events, fetch_events
from analyze import analyze_time, format_time_report, load_categories
from pending_invites import format_pending_report
from snapshots_store import (
    build_pending_summary,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)
from diff_snapshots import diff_analyses, format_diff_report


def main():
    parser = argparse.ArgumentParser(
        description="Analyze your Google Calendar: time breakdown, pending invites, and change tracking."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default=None,
        choices=["daily", "weekly"],
        help="Review cadence: 'daily' for tomorrow's prep, 'weekly' for retrospective + planning",
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
    parser.add_argument(
        "--save",
        nargs="?",
        const="",
        default=None,
        metavar="LABEL",
        help="Save a snapshot of the current analysis (optional label)",
    )
    parser.add_argument(
        "--diff",
        nargs="*",
        default=None,
        metavar="SNAPSHOT",
        help=(
            "Compare snapshots. No args: current calendar vs latest snapshot. "
            "One arg: current vs that snapshot. "
            "Two args: diff between the two specified snapshots."
        ),
    )
    parser.add_argument(
        "--list-snapshots",
        action="store_true",
        help="List all saved snapshots",
    )
    args = parser.parse_args()

    # --- List snapshots (no API call needed) ---
    if args.list_snapshots:
        _cmd_list_snapshots()
        return

    # --- Diff between two existing snapshots (no API call needed) ---
    if args.diff is not None and len(args.diff) == 2:
        _cmd_diff_two(args.diff[0], args.diff[1])
        return

    # --- Daily review ---
    if args.command == "daily":
        _cmd_daily(args)
        return

    # --- Weekly review ---
    if args.command == "weekly":
        _cmd_weekly(args)
        return

    # --- Everything else: full ad-hoc analysis ---
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

    categories = load_categories()
    analysis = analyze_time(events, categories)
    pending_summary = build_pending_summary(events)

    # --- Save snapshot ---
    if args.save is not None:
        path = save_snapshot(analysis, pending_summary, label=args.save or None)
        print(f"Snapshot saved to {path}\n")

    # --- Diff: current vs snapshot ---
    if args.diff is not None:
        _cmd_diff_live(args.diff, analysis, pending_summary)
        return

    # --- Normal reports ---
    if show_all or args.time:
        print(format_time_report(analysis, args.weeks))

    if show_all or args.pending:
        print(format_pending_report(events))

    if show_all:
        _print_tips(events)


# ── Subcommand implementations ──────────────────────────────


def _cmd_daily(args):
    """Daily review: what's on for tomorrow + pending invites to respond to."""
    from daily_review import format_daily_review

    print("Authenticating with Google Calendar...")
    service = get_calendar_service()

    # Fetch 2 days forward (today + tomorrow), 0 back
    print("Fetching tomorrow's events...")
    if args.all_calendars:
        events, _ = fetch_all_calendar_events(service, days_back=0, days_forward=2)
    else:
        events = fetch_events(service, days_back=0, days_forward=2)

    print(format_daily_review(events))


def _cmd_weekly(args):
    """Weekly review: last week vs goals, this week preview."""
    from weekly_review import format_weekly_review

    print("Authenticating with Google Calendar...")
    service = get_calendar_service()

    # Need last week + this week: ~14 days back, ~7 forward
    print("Fetching events for last week and this week...")
    if args.all_calendars:
        events, _ = fetch_all_calendar_events(service, days_back=14, days_forward=7)
    else:
        events = fetch_events(service, days_back=14, days_forward=7)

    print(format_weekly_review(events))


def _cmd_list_snapshots():
    """List all saved snapshots."""
    snaps = list_snapshots()
    if not snaps:
        print("No snapshots saved yet. Run with --save to create one.")
        return

    print(f"{'#':<4} {'Saved at':<28} {'Label':<20} {'Path'}")
    print(f"{'─' * 3} {'─' * 27} {'─' * 19} {'─' * 30}")
    for i, (path, saved_at, label) in enumerate(snaps, 1):
        print(f"{i:<4} {saved_at:<28} {label or '(none)':<20} {path}")


def _cmd_diff_two(path_a, path_b):
    """Diff two snapshot files directly."""
    try:
        old_snap = load_snapshot(path_a)
        new_snap = load_snapshot(path_b)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    diff = diff_analyses(old_snap, new_snap)
    print(format_diff_report(diff, old_snap, new_snap))


def _cmd_diff_live(diff_args, analysis, pending_summary):
    """Diff the live analysis against a snapshot."""
    if len(diff_args) == 1:
        # User specified a snapshot path
        old_path = diff_args[0]
    else:
        # No args: use the most recent snapshot
        snaps = list_snapshots()
        if not snaps:
            print(
                "No snapshots found. Run with --save first to create a baseline.",
                file=sys.stderr,
            )
            sys.exit(1)
        old_path = snaps[0][0]
        print(f"Comparing against most recent snapshot: {old_path}\n")

    try:
        old_snap = load_snapshot(old_path)
    except FileNotFoundError:
        print(f"Error: snapshot not found: {old_path}", file=sys.stderr)
        sys.exit(1)

    # Build a synthetic "new" snapshot from the live analysis
    serializable_cats = {}
    for cat_name, cat_data in analysis["by_category"].items():
        serializable_cats[cat_name] = {
            "hours": cat_data["hours"],
            "count": cat_data["count"],
        }

    new_snap = {
        "saved_at": "(live)",
        "label": "current calendar",
        "analysis": {
            "by_category": serializable_cats,
            "by_day": analysis["by_day"],
            "total_meeting_hours": analysis["total_meeting_hours"],
            "total_events": analysis["total_events"],
            "busiest_day": analysis["busiest_day"],
            "avg_daily_meeting_hours": analysis["avg_daily_meeting_hours"],
            "num_days_analyzed": analysis["num_days_analyzed"],
        },
        "pending": pending_summary,
    }

    diff = diff_analyses(old_snap, new_snap)
    print(format_diff_report(diff, old_snap, new_snap))


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
    lines.append("  -> Use the review cadences to build a habit:")
    lines.append("       python calendar_analyzer.py daily    # end of each day")
    lines.append("       python calendar_analyzer.py weekly   # Monday morning")
    lines.append("")
    lines.append("  -> Save snapshots and diff to track trends over time:")
    lines.append("       python calendar_analyzer.py --save weekly")
    lines.append("       python calendar_analyzer.py --diff")
    lines.append("")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
